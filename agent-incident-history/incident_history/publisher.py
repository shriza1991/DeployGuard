from __future__ import annotations

import json
import logging
from typing import Any

from kafka import KafkaProducer

logger = logging.getLogger("incident-history-agent")


class RiskResultPublisher:
    def __init__(self, broker: str, topic: str):
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=[broker],
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )

    def publish(self, result: dict[str, Any]) -> None:
        self.producer.send(self.topic, result)
        self.producer.flush()
        logger.info("Kafka publish completed correlation_id=%s", result.get("correlation_id"))

''