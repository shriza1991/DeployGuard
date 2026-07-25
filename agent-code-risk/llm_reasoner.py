"""
llm_reasoner.py — Backward-compatibility shim.

The two-phase pipeline (pipeline.py) replaces this module as the primary
analysis entry point in app.py.  This shim exists only to preserve imports
in existing unit tests (test_llm_reasoner.py).

DO NOT use this module for new code — use pipeline.run_analysis_pipeline() instead.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from llm.factory import get_provider

logger = logging.getLogger("code-risk-llm")


class LLMReasoner:
    """
    Backward-compatible shim.

    In the new two-phase architecture this class is no longer called from app.py.
    It is kept here so existing tests that import LLMReasoner continue to pass.

    Internally it now delegates to the Phase 2 reviewer when a full payload is
    available, or falls back to a structured default response.
    """

    def __init__(self, provider: Any | None = None, cache_ttl_seconds: int = 300):
        self.provider = provider or get_provider()
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def reason_about_change(
        self,
        payload: dict[str, Any],
        deterministic_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Legacy interface.  Runs a lightweight Phase 2 review from raw payload.

        Prefer pipeline.run_analysis_pipeline(payload) for new call sites.
        """
        from pipeline import _run_phase1, _run_phase2

        cache_key = self._cache_key(payload, deterministic_result)
        cached = self._cache.get(cache_key)
        if cached and time.time() - cached[0] < self.cache_ttl_seconds:
            logger.info("LLM cache hit (shim path)")
            return cached[1]

        try:
            report = _run_phase1(payload)
            result = _run_phase2(report)
            # Extract LLM sub-dict for backward compat
            llm_block = result.get("llm") or {}
            response = {
                "summary": llm_block.get("summary", ""),
                "risk_reasoning": llm_block.get("risk_reasoning", []),
                "recommendations": llm_block.get("recommendations", []),
                "confidence": llm_block.get("confidence", 0.0),
                "provider": llm_block.get("provider", "unavailable"),
                "available": llm_block.get("available", False),
            }
        except Exception as exc:
            logger.warning("LLMReasoner shim failed: %s", exc)
            response = _default_response(provider_name=getattr(self.provider, "name", "unavailable"))

        self._cache[cache_key] = (time.time(), response)
        return response

    def _cache_key(
        self,
        payload: dict[str, Any],
        deterministic_result: dict[str, Any],
    ) -> str:
        stable = {"payload": payload, "deterministic": deterministic_result}
        encoded = json.dumps(stable, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _default_response(provider_name: str = "unavailable") -> dict[str, Any]:
    return {
        "summary": "",
        "risk_reasoning": [],
        "recommendations": [],
        "confidence": 0.0,
        "provider": provider_name,
        "available": False,
    }


def _normalize_response(raw: dict[str, Any], provider_name: str = "unknown") -> dict[str, Any]:
    """
    Backward-compat normalizer for existing unit tests.

    Accepts a raw dict (as the old LLMReasoner would have received from the LLM)
    and returns a stable output shape with all expected keys populated.
    """
    return {
        "summary": str(raw.get("summary") or ""),
        "risk_reasoning": list(raw.get("risk_reasoning") or []),
        "recommendations": list(raw.get("recommendations") or []),
        "confidence": float(raw.get("confidence") or 0.0),
        "provider": str(provider_name),
        "available": bool(raw.get("available", False)),
    }
