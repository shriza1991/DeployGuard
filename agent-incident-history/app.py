import hashlib
import json
import os
import re
import time

import requests
from kafka import KafkaConsumer, KafkaProducer

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
INPUT_TOPIC = "deployment-events"
OUTPUT_TOPIC = "risk-results"
GROUP_ID = "agent-incident-history-group"

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
)

consumer = KafkaConsumer(
    INPUT_TOPIC,
    bootstrap_servers=[KAFKA_BROKER],
    group_id=GROUP_ID,
    auto_offset_reset="earliest",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
)


def clamp(value: float, minimum: float = 0, maximum: float = 100) -> int:
    return int(max(minimum, min(maximum, value)))


def text_embedding(text: str, dimension: int = 64) -> list[float]:
    normalized = re.findall(r"\w+", text.lower())
    if not normalized:
        return [0.0] * dimension

    vector = [0.0] * dimension
    for token in normalized:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for idx in range(dimension):
            vector[idx] += digest[idx] / 255.0

    length = sum(v * v for v in vector) ** 0.5
    if length > 0:
        vector = [v / length for v in vector]
    return vector


def query_qdrant(query_vector: list[float]) -> dict:
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


def score_incident_history(payload: dict) -> dict:
    pull_request = payload.get("pull_request") or {}
    description = payload.get("description") or pull_request.get("body") or ""
    if not isinstance(description, str):
        description = str(description)

    vector = text_embedding(description)
    search_result = query_qdrant(vector)
    hits = search_result.get("result") or []
    hit_count = len(hits)
    top_score = max((hit.get("score", 0) for hit in hits), default=0)

    if hit_count >= 2 and top_score > 0.75:
        score = 80
    elif hit_count >= 1 and top_score > 0.5:
        score = 55
    else:
        score = 35

    if "incident" in description.lower() or "outage" in description.lower():
        score += 10

    return {
        "score": clamp(score),
        "details": {
            "description_snippet": description[:120],
            "matched_incidents": hit_count,
            "top_similarity": round(top_score, 3),
            "qdrant_available": bool(search_result),
        },
    }


print("agent-incident-history started, waiting for events...")
for msg in consumer:
    event = msg.value
    payload = event.get("payload", {})
    correlation_id = event.get("correlation_id")
    print("[incident-history] received event", event)

    score_data = score_incident_history(payload)
    output = {
        "agent": "incident-history",
        "score": score_data["score"],
        "correlation_id": correlation_id,
        "details": score_data["details"],
    }
    producer.send(OUTPUT_TOPIC, output)
    producer.flush()
    print("[incident-history] published result", output)
    time.sleep(1)
