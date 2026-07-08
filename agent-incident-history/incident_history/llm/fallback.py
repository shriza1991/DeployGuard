from __future__ import annotations

from typing import Any

from .provider import LLMProvider


class FallbackLLMProvider(LLMProvider):
    name = "fallback"

    def analyze(self, prompt: str) -> dict[str, Any]:
        return {
            "available": False,
            "summary": "",
            "risk_reasoning": [],
            "recommendations": [],
            "confidence": 0.0,
        }

