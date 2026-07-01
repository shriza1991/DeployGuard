import json
import logging
import os
import time

from kafka import KafkaConsumer, KafkaProducer

from llm_reasoner import LLMReasoner
from risk_analyzers import analyze_code_risk

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
INPUT_TOPIC = "deployment-events"
OUTPUT_TOPIC = "risk-results"
GROUP_ID = "agent-code-risk-group"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("code-risk-agent")

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

reasoner = LLMReasoner()

logger.info("agent-code-risk started, waiting for events...")
for msg in consumer:
    event = msg.value
    payload = event.get("payload", {})
    correlation_id = event.get("correlation_id")
    logger.info("[code-risk] received event %s", correlation_id)

    try:
        analysis = analyze_code_risk(payload)
        llm_result = reasoner.reason_about_change(payload, analysis)

        adjusted_score = max(0, min(100, analysis["score"] + llm_result.get("risk_adjustment", 0)))
        adjusted_confidence = max(0.0, min(1.0, analysis["confidence"] / 100.0 + llm_result.get("confidence_adjustment", 0.0)))

        output = {
            "agent": "code-risk",
            "correlation_id": correlation_id,
            "score": adjusted_score,
            "severity": analysis["severity"],
            "confidence": adjusted_confidence,
            "reasons": analysis["reasons"],
            "recommendations": analysis["recommendations"],
            "metadata": analysis["metadata"],
            "llm": {
                "summary": llm_result.get("summary"),
                "additional_risks": llm_result.get("additional_risks", []),
                "deployment_recommendation": llm_result.get("deployment_recommendation"),
                "reasoning": llm_result.get("reasoning"),
                "provider": llm_result.get("provider"),
                "available": llm_result.get("available", False),
            },
        }
        producer.send(OUTPUT_TOPIC, output)
        producer.flush()
        logger.info("[code-risk] published result %s", output)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("[code-risk] failed to analyze event: %s", exc)
        output = {
            "agent": "code-risk",
            "correlation_id": correlation_id,
            "score": 0,
            "severity": "low",
            "confidence": 0.0,
            "reasons": ["Unexpected failure while analyzing the deployment change."],
            "recommendations": ["Inspect the service logs and retry the analysis."],
            "metadata": {"error": str(exc)},
            "llm": {
                "summary": "Deterministic analysis was not completed due to an unexpected error.",
                "additional_risks": [],
                "deployment_recommendation": "Do not rely on the automated result until the service is healthy.",
                "reasoning": "The agent encountered an unexpected processing error.",
                "provider": "unavailable",
                "available": False,
            },
        }
        producer.send(OUTPUT_TOPIC, output)
        producer.flush()

    time.sleep(1)
