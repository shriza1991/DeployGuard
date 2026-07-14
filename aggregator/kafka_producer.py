import json
from typing import Any, Dict
from kafka import KafkaProducer
from config import Settings
from logger import logger

class RiskDecisionPublisher:
    def __init__(self, settings: Settings):
        self.topic = settings.output_topic
        self.producer = KafkaProducer(
    bootstrap_servers=[settings.kafka_broker],
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    retries=20,
    retry_backoff_ms=3000,
    request_timeout_ms=60000,
    api_version_auto_timeout_ms=60000,
)
        logger.info(f"Initialized Kafka producer for topic: {self.topic}")

    def publish(self, correlation_id: str, decision: Dict[str, Any]) -> None:
        try:
            self.producer.send(self.topic, decision)
            self.producer.flush()
            logger.info(f"Successfully published aggregated decision for correlation_id {correlation_id} to {self.topic}")
        except Exception as e:
            logger.error(f"Failed to publish decision to Kafka: {e}", exc_info=True)
