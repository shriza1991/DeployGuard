from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract interface for an LLM provider implementation."""

    name: str = "base"

    @abstractmethod
    def analyze(self, prompt: str) -> dict[str, Any]:
        """Analyze a prompt and return a structured response."""
        raise NotImplementedError
