from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

import requests

from llm.factory import get_provider
from llm.prompt_builder import build_prompt

logger = logging.getLogger("infra-risk-llm")


class LLMReasoner:
    """Wraps LLM provider execution and normalizes provider results."""

    def __init__(self, provider: Any | None = None, cache_ttl_seconds: int = 300):
        self.provider = provider or get_provider()
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def reason_about_change(self, payload: dict[str, Any], deterministic_result: dict[str, Any]) -> dict[str, Any]:
        prompt = build_prompt(
            score=int(deterministic_result.get("score", 0)),
            severity=str(deterministic_result.get("severity", "low")),
            confidence=float(deterministic_result.get("confidence", 0.0)),
            reasons=list(deterministic_result.get("reasons", [])) or [],
            recommendations=list(deterministic_result.get("recommendations", [])) or [],
            changed_files=_extract_changed_files(payload),
            metadata=deterministic_result.get("metadata", {}),
        )

        cache_key = self._cache_key(payload, deterministic_result)
        cached = self._cache.get(cache_key)
        if cached and time.time() - cached[0] < self.cache_ttl_seconds:
            logger.info("LLM cache hit for payload")
            return cached[1]

        logger.info("LLM prompt generated")
        response = self._generate_with_retries(prompt)
        self._cache[cache_key] = (time.time(), response)
        return response

    def _generate_with_retries(self, prompt: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                logger.info("LLM request started using provider %s", getattr(self.provider, "name", "unknown"))
                response = self.provider.analyze(prompt)
                logger.info("LLM response received from provider %s", getattr(self.provider, "name", "unknown"))
                return _normalize_response(response, provider_name=getattr(self.provider, "name", "unknown"))
            except (requests.Timeout, requests.HTTPError, requests.ConnectionError, ValueError, json.JSONDecodeError, ImportError) as exc:
                last_error = exc
                logger.warning("LLM request failed (attempt %s/3): %s", attempt + 1, exc)
            except Exception as exc:
                last_error = exc
                logger.warning("Unexpected LLM error (attempt %s/3): %s", attempt + 1, exc)

            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))

        logger.warning("LLM reasoning unavailable after retries: %s", last_error)
        return _default_response(provider_name=getattr(self.provider, "name", "unavailable"))

    def _cache_key(self, payload: dict[str, Any], deterministic_result: dict[str, Any]) -> str:
        stable_payload = {
            "payload": payload,
            "deterministic": deterministic_result,
        }
        encoded = json.dumps(stable_payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _extract_changed_files(payload: dict[str, Any]) -> list[dict[str, Any]]:
    changed_files = payload.get("files")
    if isinstance(changed_files, list):
        return [file_entry for file_entry in changed_files if isinstance(file_entry, dict)]
    return []


def _normalize_response(response: dict[str, Any], provider_name: str) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ValueError("LLM response was not a JSON object")

    normalized = {
        "summary": str(response.get("summary") or "Deterministic analysis reviewed with conservative AI context."),
        "risk_reasoning": [str(item) for item in response.get("risk_reasoning", []) if str(item).strip()],
        "recommendations": [str(item) for item in response.get("recommendations", []) if str(item).strip()],
        "confidence": float(response.get("confidence", 0.0) or 0.0),
        "provider": provider_name,
        "available": bool(response.get("available", True)),
    }

    normalized["confidence"] = max(0.0, min(1.0, normalized["confidence"]))
    return normalized


def _default_response(provider_name: str = "unavailable") -> dict[str, Any]:
    return {
        "summary": "",
        "risk_reasoning": [],
        "recommendations": [],
        "confidence": 0.0,
        "provider": provider_name,
        "available": False,
    }
