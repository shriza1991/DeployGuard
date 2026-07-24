import os
from dataclasses import dataclass, field
from typing import Set

@dataclass(frozen=True)
class Settings:
    kafka_broker: str = os.getenv("KAFKA_BROKER", "kafka:9092")
    input_topic: str = os.getenv("INPUT_TOPIC", "risk-results")
    output_topic: str = os.getenv("OUTPUT_TOPIC", "deployment-decisions")
    group_id: str = os.getenv("GROUP_ID", "aggregator-group")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    # Timeout defaults to AGGREGATION_TIMEOUT_SECONDS or TIMEOUT_SECONDS, with sensible default of 90 seconds
    timeout_seconds: int = int(os.getenv("AGGREGATION_TIMEOUT_SECONDS", os.getenv("TIMEOUT_SECONDS", "90")))
    expected_agents_str: str = os.getenv("EXPECTED_AGENTS", "code-risk,infra-risk,incident-history")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8002"))

    @property
    def expected_agents(self) -> Set[str]:
        return {a.strip() for a in self.expected_agents_str.split(",") if a.strip()}

def get_settings() -> Settings:
    return Settings()

