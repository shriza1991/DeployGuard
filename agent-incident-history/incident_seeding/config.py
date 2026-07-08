from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv_file(env_path: Path) -> None:
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def _load_dotenv(path: Path | None = None) -> None:
    if path is not None:
        _load_dotenv_file(path)
        return

    package_root = Path(__file__).resolve().parent.parent
    repo_root = package_root.parent
    candidates = [
        Path.cwd() / ".env",
        repo_root / ".env",
        package_root / ".env",
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        _load_dotenv_file(resolved)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class SeedSettings:
    qdrant_url: str
    qdrant_collection: str
    embedding_model: str
    embedding_provider: str
    embedding_dimension: int
    reset_collection: bool
    qdrant_timeout_seconds: float
    qdrant_retries: int
    embedding_cache_size: int
    incident_count_min: int
    incident_count_max: int
    verification_samples: int
    verification_top_k: int


def get_seed_settings() -> SeedSettings:
    _load_dotenv()
    return SeedSettings(
        qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        qdrant_collection=os.getenv("QDRANT_COLLECTION", "incident_history"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "sentence-transformer"),
        embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "384")),
        reset_collection=_env_bool("RESET_COLLECTION", False),
        qdrant_timeout_seconds=float(os.getenv("QDRANT_TIMEOUT_SECONDS", "10")),
        qdrant_retries=int(os.getenv("QDRANT_RETRIES", "3")),
        embedding_cache_size=int(os.getenv("EMBEDDING_CACHE_SIZE", "512")),
        incident_count_min=int(os.getenv("INCIDENT_COUNT_MIN", "50")),
        incident_count_max=int(os.getenv("INCIDENT_COUNT_MAX", "100")),
        verification_samples=int(os.getenv("VERIFICATION_SAMPLES", "3")),
        verification_top_k=int(os.getenv("VERIFICATION_TOP_K", "5")),
    )
