import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load env variables from a .env file if present
load_dotenv()

@dataclass(frozen=True)
class Settings:
    qdrant_url: str = os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "repository_context")
    qdrant_timeout_seconds: float = float(os.getenv("QDRANT_TIMEOUT_SECONDS", "10.0"))
    qdrant_retries: int = int(os.getenv("QDRANT_RETRIES", "3"))

    redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

    embedding_model: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))

    # Directory where repositories are cloned and status db is stored (if needed)
    data_dir: str = os.getenv("DATA_DIR", "./data")

    # Base chunk size in words/tokens
    chunk_size_tokens: int = int(os.getenv("CHUNK_SIZE_TOKENS", "450"))
    chunk_overlap_tokens: int = int(os.getenv("CHUNK_OVERLAP_TOKENS", "100"))

def get_settings() -> Settings:
    return Settings()
