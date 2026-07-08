from __future__ import annotations

import json
import logging
import time
from typing import Any

from kafka import KafkaConsumer

from incident_history.config import Settings
from incident_history.publisher import RiskResultPublisher
from incident_history.service import IncidentHistoryService

logger = logging.getLogger("incident-history-agent")


class DeploymentEventConsumer:
    def __init__(self, settings: Settings, service: IncidentHistoryService, publisher: RiskResultPublisher):
        self.settings = settings
        self.service = service
        self.publisher = publisher
        self.consumer = KafkaConsumer(
            settings.input_topic,
            bootstrap_servers=[settings.kafka_broker],
            group_id=settings.group_id,
            auto_offset_reset="earliest",
            value_deserializer=lambda message: json.loads(message.decode("utf-8")),
        )

    def run_forever(self) -> None:
        logger.info("agent-incident-history started, waiting for events...")
        for msg in self.consumer:
            event = msg.value if isinstance(msg.value, dict) else {}
            correlation_id = event.get("correlation_id")
            payload = event.get("payload", {}) if isinstance(event.get("payload", {}), dict) else {}
            logger.info("Kafka receive completed correlation_id=%s", correlation_id)
            try:
                result = self.service.analyze_event(payload, correlation_id=correlation_id)
            except Exception as exc:
                logger.exception("Unexpected incident-history failure: %s", exc)
                result = _unexpected_failure(correlation_id, exc, event)
            self.publisher.publish(result)
            time.sleep(1)


def _unexpected_failure(correlation_id: str | None, exc: Exception, event: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent": "incident-history",
        "correlation_id": correlation_id,
        "score": 10,
        "severity": "low",
        "confidence": 0.0,
        "reasons": ["Unexpected failure while analyzing historical incident context."],
        "recommendations": ["Inspect the incident-history service logs and retry the analysis."],
        "metadata": {"error": str(exc), "payload_type": type(event).__name__},
        "similar_incidents": [],
        "llm": {
            "provider": "unavailable",
            "available": False,
            "summary": "Incident history analysis failed before retrieval completed.",
            "risk_reasoning": [],
            "recommendations": [],
            "confidence": 0.0,
        },
    }

