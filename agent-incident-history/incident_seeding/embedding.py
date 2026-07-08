from __future__ import annotations

import logging

from incident_history.embeddings import get_embedding_provider

from incident_seeding.models import SeedIncident

logger = logging.getLogger("incident-history-seed")


def load_embedding_provider(
    provider_name: str,
    model_name: str,
    dimension: int,
    cache_size: int,
):
    logger.info("Loading embedding model...")
    return get_embedding_provider(provider_name, model_name, dimension, cache_size)


def embed_incident(embedding_provider, incident: SeedIncident) -> list[float]:
    return embedding_provider.embed(incident.search_text())


def embed_incidents(embedding_provider, incidents: list[SeedIncident]) -> dict[str, list[float]]:
    vectors: dict[str, list[float]] = {}
    for incident in incidents:
        vectors[incident.incident_id] = embed_incident(embedding_provider, incident)
    return vectors
