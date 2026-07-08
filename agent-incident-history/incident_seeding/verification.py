from __future__ import annotations

import logging
import random

from incident_seeding.embedding import embed_incident
from incident_seeding.models import SeedIncident
from incident_seeding.qdrant_client import SeedQdrantClient

logger = logging.getLogger("incident-history-seed")


def verify_semantic_search(
    client: SeedQdrantClient,
    embedding_provider,
    incidents: list[SeedIncident],
    sample_count: int = 3,
    top_k: int = 5,
) -> None:
    if not incidents:
        logger.warning("No incidents available for verification.")
        return

    samples = random.sample(incidents, k=min(sample_count, len(incidents)))
    logger.info("Running semantic search verification on %s sample(s)...", len(samples))

    for sample in samples:
        vector = embed_incident(embedding_provider, sample)
        hits = client.search(vector, top_k=top_k)
        logger.info("Query incident: %s - %s", sample.incident_id, sample.title)
        if not hits:
            logger.warning("  No neighbors returned.")
            continue
        logger.info("  Top %s nearest neighbors:", top_k)
        for rank, hit in enumerate(hits, start=1):
            payload = hit.get("payload") or {}
            incident_id = payload.get("incident_id", "unknown")
            score = float(hit.get("score", 0.0) or 0.0)
            title = payload.get("title", "")
            logger.info(
                "  #%s similarity=%.4f incident_id=%s title=%s",
                rank,
                score,
                incident_id,
                title,
            )
