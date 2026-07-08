from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from incident_seeding.config import get_seed_settings
from incident_seeding.dataset import build_curated_dataset
from incident_seeding.embedding import embed_incidents, load_embedding_provider
from incident_seeding.qdrant_client import SeedQdrantClient
from incident_seeding.verification import verify_semantic_search

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("incident-history-seed")


def run() -> int:
    started = time.perf_counter()
    settings = get_seed_settings()

    logger.info("Connecting to Qdrant at %s...", settings.qdrant_url)
    client = SeedQdrantClient(
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        vector_size=settings.embedding_dimension,
        timeout_seconds=settings.qdrant_timeout_seconds,
        retries=settings.qdrant_retries,
    )

    embedding_provider = load_embedding_provider(
        settings.embedding_provider,
        settings.embedding_model,
        settings.embedding_dimension,
        settings.embedding_cache_size,
    )

    client.ensure_collection(reset=settings.reset_collection)

    incidents = build_curated_dataset(
        minimum=settings.incident_count_min,
        maximum=settings.incident_count_max,
    )
    logger.info("Generating embeddings for %s incidents...", len(incidents))
    vectors = embed_incidents(embedding_provider, incidents)

    inserted, skipped = client.upload_incidents(
        incidents=incidents,
        vectors=vectors,
        skip_existing=not settings.reset_collection,
    )

    verify_semantic_search(
        client=client,
        embedding_provider=embedding_provider,
        incidents=incidents,
        sample_count=settings.verification_samples,
        top_k=settings.verification_top_k,
    )

    elapsed = time.perf_counter() - started
    logger.info("Completed successfully.")
    logger.info("Total incidents inserted: %s", inserted)
    if skipped:
        logger.info("Total incidents skipped (duplicates): %s", skipped)
    logger.info("Elapsed time: %.2f seconds", elapsed)
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
