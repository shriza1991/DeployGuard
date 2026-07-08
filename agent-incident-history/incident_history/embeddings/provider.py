from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    name: str
    dimension: int

    def embed(self, text: str) -> list[float]:
        ...

