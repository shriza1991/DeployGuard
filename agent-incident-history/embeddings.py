import hashlib
import math
import os
import re
from typing import List, Protocol


class EmbeddingProvider(Protocol):
    name: str

    def embed_text(self, text: str) -> List[float]:
        ...


class HashEmbeddingProvider:
    def __init__(self, dimension: int = 64):
        self.name = "hash"
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        normalized = re.findall(r"\w+", text.lower())
        if not normalized:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension
        for token in normalized:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for idx in range(self.dimension):
                vector[idx] += digest[idx % len(digest)] / 255.0

        length = math.sqrt(sum(v * v for v in vector))
        if length > 0:
            vector = [v / length for v in vector]
        return vector


def get_embedding_provider() -> EmbeddingProvider:
    provider_name = os.getenv("EMBEDDING_PROVIDER", os.getenv("EMBEDDING_MODEL", "hash")).lower()
    dimension = int(os.getenv("EMBEDDING_DIMENSION", "64"))

    if provider_name in {"hash", "deterministic", "builtin"}:
        return HashEmbeddingProvider(dimension=dimension)

    # Future providers can be implemented here. The agent only depends on the
    # provider interface, so swapping implementations is a local change.
    return HashEmbeddingProvider(dimension=dimension)
