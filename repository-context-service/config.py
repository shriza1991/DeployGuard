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

    # Context retrieval and similarity settings
    top_k_default: int = int(os.getenv("TOP_K_DEFAULT", "5"))
    top_k_max: int = int(os.getenv("TOP_K_MAX", "10"))
    min_similarity: float = float(os.getenv("MIN_SIMILARITY", "0.45"))
    max_context_characters: int = int(os.getenv("MAX_CONTEXT_CHARACTERS", "4000"))
    enable_fallback: bool = os.getenv("ENABLE_FALLBACK", "True").lower() in ("true", "1", "yes")
    enable_ranking: bool = os.getenv("ENABLE_RANKING", "True").lower() in ("true", "1", "yes")
    enable_deduplication: bool = os.getenv("ENABLE_DEDUPLICATION", "True").lower() in ("true", "1", "yes")

    # Heuristic scoring weights and penalties
    weight_semantic: float = float(os.getenv("WEIGHT_SEMANTIC", "0.75"))
    bonus_exact_file: float = float(os.getenv("BONUS_EXACT_FILE", "0.10"))
    bonus_same_dir: float = float(os.getenv("BONUS_SAME_DIR", "0.05"))
    bonus_same_module: float = float(os.getenv("BONUS_SAME_MODULE", "0.05"))
    bonus_config_file: float = float(os.getenv("BONUS_CONFIG_FILE", "0.05"))
    penalty_test_file: float = float(os.getenv("PENALTY_TEST_FILE", "0.10"))
    penalty_mock_generated: float = float(os.getenv("PENALTY_MOCK_GENERATED", "0.15"))
    penalty_tiny_chunk: float = float(os.getenv("PENALTY_TINY_CHUNK", "0.10"))

    # Configurable Qdrant batching and indexing settings
    qdrant_batch_size: int = int(os.getenv("QDRANT_BATCH_SIZE", "100"))
    enable_incremental_indexing: bool = os.getenv("ENABLE_INCREMENTAL_INDEXING", "True").lower() in ("true", "1", "yes")

    # Ignore rules
    repository_ignore_rules: str = os.getenv(
        "REPOSITORY_IGNORE_RULES",
        "coverage/,.cache/,dist/,build/,storybook-static/,node_modules/,venv/,__pycache__/,package-lock.json,pnpm-lock.yaml,poetry.lock,yarn.lock,generated docs"
    )

def get_settings() -> Settings:
    return Settings()
