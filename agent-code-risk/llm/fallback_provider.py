from __future__ import annotations

from .base import LLMProvider


class FallbackProvider(LLMProvider):
    name = "fallback"

    def analyze(self, prompt: str) -> dict[str, object]:
        return {
            "provider": self.name,
            "available": False,
            "summary": "",
            "risk_reasoning": [],
            "recommendations": [],
            "confidence": 0.0,
        }
