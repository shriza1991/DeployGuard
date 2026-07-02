import json
import os
import time
from typing import Any, Dict, List

import requests
from kafka import KafkaConsumer, KafkaProducer

from embeddings import get_embedding_provider

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
INPUT_TOPIC = "deployment-events"
OUTPUT_TOPIC = "risk-results"
GROUP_ID = "agent-incident-history-group"

producer = None
consumer = None

embedding_provider = get_embedding_provider()


def get_producer():
    global producer
    if producer is None:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER],
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )
    return producer


def get_consumer():
    global consumer
    if consumer is None:
        consumer = KafkaConsumer(
            INPUT_TOPIC,
            bootstrap_servers=[KAFKA_BROKER],
            group_id=GROUP_ID,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
    return consumer


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> int:
    return int(max(minimum, min(maximum, value)))


def extract_description(payload: dict) -> str:
    pull_request = payload.get("pull_request") or {}
    description = payload.get("description") or pull_request.get("body") or payload.get("title") or ""
    if not isinstance(description, str):
        description = str(description)
    return description.strip()


def query_qdrant(query_vector: List[float]) -> dict:
    search_url = f"{QDRANT_URL}/collections/incidents/points/search"
    payload = {
        "vector": query_vector,
        "top": 3,
        "with_scores": True,
    }
    try:
        response = requests.post(search_url, json=payload, timeout=10)
        if response.status_code != 200:
            return {}
        return response.json()
    except requests.RequestException:
        return {}


def analyze_incident_history(payload: dict) -> dict:
    description = extract_description(payload)
    vector = embedding_provider.embed_text(description)
    search_result = query_qdrant(vector)
    hits = search_result.get("result") or []
    hit_count = len(hits)
    top_hit = hits[0] if hits else {}
    top_score = float(top_hit.get("score", 0) or 0)
    payload_data = top_hit.get("payload") or {}

    history_signals = {
        "previous_incidents": int(payload_data.get("previous_incidents", 0) or 0),
        "rollbacks": int(payload_data.get("rollbacks", 0) or 0),
        "outages": int(payload_data.get("outages", 0) or 0),
        "failed_deployments": int(payload_data.get("failed_deployments", 0) or 0),
    }

    score = 25
    if top_score > 0.85:
        score += 35
    elif top_score > 0.65:
        score += 20
    elif top_score > 0.4:
        score += 10

    if hit_count >= 2:
        score += 10
    if history_signals["previous_incidents"] > 0:
        score += 10
    if history_signals["rollbacks"] > 0:
        score += 10
    if history_signals["outages"] > 0:
        score += 10
    if history_signals["failed_deployments"] > 0:
        score += 10

    text_lower = description.lower()
    if any(term in text_lower for term in ["incident", "outage", "rollback", "failure", "downtime"]):
        score += 10

    score = clamp(score)

    severity = "low"
    if score >= 80:
        severity = "critical"
    elif score >= 60:
        severity = "high"
    elif score >= 40:
        severity = "medium"

    confidence = 0.35
    if hit_count > 0:
        confidence += 0.2
    if top_score > 0.6:
        confidence += 0.2
    if history_signals["previous_incidents"] + history_signals["rollbacks"] + history_signals["outages"] + history_signals["failed_deployments"] > 0:
        confidence += 0.15
    confidence = max(0.0, min(1.0, confidence))

    reasons = []
    if hit_count > 0:
        reasons.append(f"Historical match found with similarity {top_score:.2f}.")
    else:
        reasons.append("No strong historical match was found in Qdrant.")

    if history_signals["previous_incidents"] > 0:
        reasons.append("The closest historical deployment had prior incidents.")
    if history_signals["rollbacks"] > 0:
        reasons.append("The close history includes rollbacks.")
    if history_signals["outages"] > 0:
        reasons.append("The close history includes outages.")
    if history_signals["failed_deployments"] > 0:
        reasons.append("The close history includes failed deployments.")

    recommendations = [
        "Review the historical deployment context before shipping this change.",
    ]
    if score >= 60:
        recommendations.append("Prepare a rollback plan and increase monitoring before rollout.")
    if history_signals["rollbacks"] > 0 or history_signals["outages"] > 0:
        recommendations.append("Coordinate with on-call responders and rehearse rollback criteria.")

    return {
        "score": score,
        "severity": severity,
        "confidence": confidence,
        "reasons": reasons,
        "recommendations": recommendations,
        "metadata": {
            "embedding_provider": embedding_provider.name,
            "description_snippet": description[:160],
            "matched_incidents": hit_count,
            "top_similarity": round(top_score, 3),
            "qdrant_available": bool(search_result),
            "history_signals": history_signals,
            "query_text": description,
        },
    }


def main():
    print("agent-incident-history started, waiting for events...")
    kafka_consumer = get_consumer()
    kafka_producer = get_producer()

    for msg in kafka_consumer:
        event = msg.value
        payload = event.get("payload", {})
        correlation_id = event.get("correlation_id")
        print("[incident-history] received event", event)

        try:
            analysis = analyze_incident_history(payload)
            output = {
                "agent": "incident-history",
                "correlation_id": correlation_id,
                "score": analysis["score"],
                "severity": analysis["severity"],
                "confidence": analysis["confidence"],
                "reasons": analysis["reasons"],
                "recommendations": analysis["recommendations"],
                "metadata": analysis["metadata"],
            }
            kafka_producer.send(OUTPUT_TOPIC, output)
            kafka_producer.flush()
            print("[incident-history] published result", output)
        except Exception as exc:  # pragma: no cover - defensive logging
            output = {
                "agent": "incident-history",
                "correlation_id": correlation_id,
                "score": 0,
                "severity": "low",
                "confidence": 0.0,
                "reasons": ["Unexpected failure while analyzing historical incident context."],
                "recommendations": ["Inspect the service logs and retry the analysis."],
                "metadata": {"error": str(exc)},
            }
            kafka_producer.send(OUTPUT_TOPIC, output)
            kafka_producer.flush()

        time.sleep(1)


if __name__ == "__main__":
    main()
