from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    name = "base"

    @abstractmethod
    def analyze(self, prompt: str) -> dict[str, Any]:
        raise NotImplementedError

