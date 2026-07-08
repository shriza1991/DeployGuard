from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    kafka_broker: str = os.getenv("KAFKA_BROKER", "kafka:9092")
    input_topic: str = os.getenv("INPUT_TOPIC", "deployment-events")
    output_topic: str = os.getenv("OUTPUT_TOPIC", "risk-results")
    group_id: str = os.getenv("GROUP_ID", "agent-incident-history-group")

    qdrant_url: str = os.getenv("QDRANT_URL", "http://qdrant:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "incident_history")
    qdrant_timeout_seconds: float = float(os.getenv("QDRANT_TIMEOUT_SECONDS", "3"))
    qdrant_retries: int = int(os.getenv("QDRANT_RETRIES", "2"))

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "sentence-transformer")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))

    top_k_results: int = int(os.getenv("TOP_K_RESULTS", "5"))
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.50"))
    embedding_cache_size: int = int(os.getenv("EMBEDDING_CACHE_SIZE", "256"))

    llm_provider: str = os.getenv("LLM_PROVIDER", "gemini")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    health_host: str = os.getenv("HEALTH_HOST", "0.0.0.0")
    health_port: int = int(os.getenv("HEALTH_PORT", "8080"))


def get_settings() -> Settings:
    return Settings()

