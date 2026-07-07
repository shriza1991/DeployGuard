from incident_history.embeddings import HashEmbeddingProvider


def get_embedding_provider():
    """Backward-compatible deterministic provider for older imports."""
    provider = HashEmbeddingProvider()
    provider.embed_text = provider.embed  # type: ignore[attr-defined]
    return provider

