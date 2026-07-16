from transformers.models.chameleon import image_processing_chameleon_fast
import logging
import time
import re
import hashlib
import math
from typing import List

logger = logging.getLogger("repository-context-service")

class HashEmbeddingProvider:
    """Fallback deterministic token-frequency hash-based embedding generator."""
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed(self, text: str) -> List[float]:
        tokens = re.findall(r"\w+", (text or "").lower())
        if not tokens:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for idx in range(self.dimension):
                vector[idx] += digest[idx % len(digest)] / 255.0

        length = math.sqrt(sum(value * value for value in vector))
        if length > 0:
            return [float(value / length) for value in vector]
        return vector

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dimension: int = 384):
        self.model_name = model_name
        self.dimension = dimension
        self._model = None
        self._hash_provider = HashEmbeddingProvider(dimension)

    def _get_model(self):
        """Lazy loads the SentenceTransformer model."""
        if self._model is None:
            if self.model_name.lower() in {"hash", "deterministic", "builtin"}:
                logger.info("Using HashEmbeddingProvider.")
                self._model = self._hash_provider
            else:
                try:
                    from sentence_transformers import SentenceTransformer
                    logger.info(f"Loading SentenceTransformer model '{self.model_name}'...")
                    started = time.perf_counter()
                    self._model = SentenceTransformer(self.model_name)
                    logger.info(f"Model loaded successfully in {(time.perf_counter() - started)*1000:.2f} ms")
                except Exception as e:
                    logger.warning(f"Failed to load model {self.model_name} due to: {e}. Falling back to HashEmbeddingProvider.")
                    self._model = self._hash_provider
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Generates an embedding vector for a single text string."""
        model = self._get_model()
        if isinstance(model, HashEmbeddingProvider):
            return model.embed(text)
        
        try:
            vector = model.encode(text or "", normalize_embeddings=True)
            return [float(value) for value in vector.tolist()]
        except Exception as e:
            logger.error(f"Failed generating sentence embedding: {e}. Falling back to hash provider.")
            return self._hash_provider.embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a list of text strings in batch."""
        if not texts:
            return []
            
        model = self._get_model()
        if isinstance(model, HashEmbeddingProvider):
            return [model.embed(text) for text in texts]

        try:
            vectors = model.encode(texts, normalize_embeddings=True)
            return [[float(val) for val in vec.tolist()] for vec in vectors]
        except Exception as e:
            logger.error(f"Failed generating batch embeddings: {e}. Falling back to hash provider.")
            return [self._hash_provider.embed(text) for text in texts]
    
    def load_model(self):
        """
        Eagerly loads the embedding model during application startup.
        Safe to call multiple times.
        """
        self._get_model()