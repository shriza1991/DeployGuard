from __future__ import annotations

import hashlib
import logging
import math
import re
import time
from collections import OrderedDict

from .provider import EmbeddingProvider

logger = logging.getLogger("incident-history-agent")


class SentenceTransformerEmbeddingProvider:
    name = "sentence-transformer"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dimension: int = 384, cache_size: int = 256):
        self.model_name = model_name
        self.dimension = dimension
        self.cache_size = cache_size
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._model = self._load_model()

    def embed(self, text: str) -> list[float]:
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            return cached

        started = time.perf_counter()
        vector = self._model.encode(text or "", normalize_embeddings=True)
        result = [float(value) for value in vector.tolist()]
        self.dimension = len(result)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info("Embedding generated in %s ms (dimension=%s)", latency_ms, self.dimension)
        self._remember(key, result)
        return result

    def _load_model(self):
        from sentence_transformers import SentenceTransformer

        logger.info("Loading SentenceTransformer embedding model %s ...", self.model_name)
        started = time.perf_counter()
        model = SentenceTransformer(self.model_name)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info("Loaded embedding model %s in %s ms", self.model_name, latency_ms)
        return model

    def _remember(self, key: str, vector: list[float]) -> None:
        self._cache[key] = vector
        self._cache.move_to_end(key)
        if len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)


class HashEmbeddingProvider:
    name = "hash"

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        tokens = re.findall(r"\w+", (text or "").lower())
        if not tokens:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for idx in range(self.dimension):
                vector[idx] += digest[idx % len(digest)] / 255.0

        length = math.sqrt(sum(value * value for value in vector))
        return [value / length for value in vector] if length else vector


def get_embedding_provider(provider_name: str, model_name: str, dimension: int, cache_size: int) -> EmbeddingProvider:
    normalized = provider_name.strip().lower()
    if normalized in {"hash", "deterministic", "builtin"}:
        return HashEmbeddingProvider(dimension=dimension)
    return SentenceTransformerEmbeddingProvider(model_name=model_name, dimension=dimension, cache_size=cache_size)

