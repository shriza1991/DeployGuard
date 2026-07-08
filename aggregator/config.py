import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    kafka_broker: str = os.getenv("KAFKA_BROKER", "kafka:9092")
    input_topic: str = os.getenv("INPUT_TOPIC", "risk-results")
    output_topic: str = os.getenv("OUTPUT_TOPIC", "deployment-decisions")
    group_id: str = os.getenv("GROUP_ID", "aggregator-group")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    timeout_seconds: int = int(os.getenv("TIMEOUT_SECONDS", "10"))
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8002"))

def get_settings() -> Settings:
    return Settings()
