import json
from kafka import KafkaConsumer
from config import Settings
from aggregation_engine import AggregationEngine
from logger import logger

class RiskResultConsumer:
    def __init__(self, settings: Settings, engine: AggregationEngine):
        self.settings = settings
        self.engine = engine
        self.consumer = KafkaConsumer(
            self.settings.input_topic,
            bootstrap_servers=[self.settings.kafka_broker],
            group_id=self.settings.group_id,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: self._deserialize(m)
        )
        logger.info(f"Initialized Kafka consumer for topic: {self.settings.input_topic}")

    def _deserialize(self, message_bytes: bytes) -> dict:
        try:
            return json.loads(message_bytes.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to deserialize JSON message: {e}")
            return {}

    def run_forever(self) -> None:
        logger.info("Kafka consumer loop started, reading events...")
        try:
            for message in self.consumer:
                payload = message.value
                if not payload:
                    continue

                correlation_id = payload.get("correlation_id")
                agent_name = payload.get("agent")
                
                if not correlation_id:
                    logger.warning(f"Skipping event with missing correlation_id: {payload}")
                    continue

                if not agent_name:
                    logger.warning(f"Skipping event with missing agent field: {payload}")
                    continue

                logger.info(f"Received agent result from '{agent_name}' for correlation_id: {correlation_id}")
                
                try:
                    self.engine.handle_agent_result(correlation_id, agent_name, payload)
                except Exception as ex:
                    logger.error(f"Error handling agent result: {ex}", exc_info=True)
        except Exception as e:
            logger.critical(f"Critical error in Kafka consumer loop: {e}", exc_info=True)
