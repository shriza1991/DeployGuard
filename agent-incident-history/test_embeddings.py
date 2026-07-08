import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from incident_history.embeddings import HashEmbeddingProvider


def test_hash_embedding_is_deterministic_and_normalized():
    provider = HashEmbeddingProvider(dimension=16)

    first = provider.embed("public s3 bucket")
    second = provider.embed("public s3 bucket")

    assert first == second
    assert len(first) == 16
    assert abs(sum(value * value for value in first) - 1.0) < 0.0001

