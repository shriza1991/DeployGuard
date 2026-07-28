from __future__ import annotations

from typing import Any

from .provider import LLMProvider


class FallbackLLMProvider(LLMProvider):
    name = "fallback"

    def analyze(self, prompt: str) -> dict[str, Any]:
        return {
            "available": False,
            "summary": "Historical retrieval completed without LLM enrichment.",
            "risk_reasoning": ["LLM reasoning provider unavailable."],
            "recommendations": ["Review retrieved similar incidents manually."],
            "confidence": 0.50,
            "executive_summary": "Historical retrieval completed without LLM enrichment.",
            "common_failure_pattern": "",
            "risk_comparison": "",
            "historical_recommendations": ["Review retrieved similar incidents manually."],
        }
