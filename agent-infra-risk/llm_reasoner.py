"""
llm_reasoner
~~~~~~~~~~~~~
Orchestrates LLM provider calls and normalizes the synthesis response.

The LLM is called AFTER deterministic analysis to produce a security review
narrative (not to repeat individual findings).  All structured fields from
the new synthesis prompt are surfaced in the normalized response.
"""
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
    """Wraps LLM provider execution and normalizes synthesis results."""

    def __init__(self, provider: Any | None = None, cache_ttl_seconds: int = 300):
        self.provider = provider or get_provider()
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def reason_about_change(
        self,
        payload: dict[str, Any],
        deterministic_result: dict[str, Any],
    ) -> dict[str, Any]:
        prompt = build_prompt(
            score=int(deterministic_result.get("score", 0)),
            severity=str(deterministic_result.get("severity", "low")),
            confidence=float(deterministic_result.get("confidence", 0.0)),
            reasons=list(deterministic_result.get("reasons", []) or []),
            recommendations=list(deterministic_result.get("recommendations", []) or []),
            changed_files=_extract_changed_files(payload),
            metadata=deterministic_result.get("metadata", {}),
        )

        cache_key = self._cache_key(payload, deterministic_result)
        cached = self._cache.get(cache_key)
        if cached and time.time() - cached[0] < self.cache_ttl_seconds:
            logger.info("LLM cache hit for payload")
            return cached[1]

        logger.info("LLM synthesis prompt built — sending to provider")
        response = self._generate_with_retries(prompt)
        self._cache[cache_key] = (time.time(), response)
        return response

    def _generate_with_retries(self, prompt: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                logger.info(
                    "LLM request started (attempt %d/3) using provider %s",
                    attempt + 1,
                    getattr(self.provider, "name", "unknown"),
                )
                response = self.provider.analyze(prompt)
                normalized = _normalize_response(
                    response,
                    provider_name=getattr(self.provider, "name", "unknown"),
                )
                logger.info(
                    "LLM synthesis received from %s",
                    getattr(self.provider, "name", "unknown"),
                )
                return normalized
            except (
                requests.Timeout,
                requests.HTTPError,
                requests.ConnectionError,
                ValueError,
                json.JSONDecodeError,
                ImportError,
            ) as exc:
                last_error = exc
                logger.warning("LLM request failed (attempt %d/3): %s", attempt + 1, exc)
            except Exception as exc:
                last_error = exc
                logger.warning("Unexpected LLM error (attempt %d/3): %s", attempt + 1, exc)

            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))

        logger.warning("LLM synthesis unavailable after retries: %s", last_error)
        return _default_response(provider_name=getattr(self.provider, "name", "unavailable"))

    def _cache_key(
        self,
        payload: dict[str, Any],
        deterministic_result: dict[str, Any],
    ) -> str:
        stable = {"payload": payload, "deterministic": deterministic_result}
        encoded = json.dumps(stable, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_changed_files(payload: dict[str, Any]) -> list[dict[str, Any]]:
    changed_files = payload.get("files")
    if isinstance(changed_files, list):
        return [f for f in changed_files if isinstance(f, dict)]
    return []


def _normalize_response(response: dict[str, Any], provider_name: str) -> dict[str, Any]:
    if not isinstance(response, dict):
        raise ValueError("LLM response was not a JSON object")

    executive_summary = str(response.get("executive_summary") or "")
    risk_narrative = str(response.get("risk_narrative") or "")
    deployment_recommendation = str(
        response.get("deployment_recommendation") or "PROCEED_WITH_CONDITIONS"
    ).strip().upper()
    primary_attack_scenario = str(response.get("primary_attack_scenario") or "")
    reviewer_priorities = [
        str(item) for item in response.get("reviewer_priorities", []) if str(item).strip()
    ]
    confidence_explanation = str(response.get("confidence_explanation") or "")
    confidence_val = float(response.get("confidence", 0.0) or 0.0)
    confidence_val = max(0.0, min(1.0, confidence_val))

    # Validate deployment_recommendation
    valid_recommendations = {"PROCEED", "PROCEED_WITH_CONDITIONS", "DO_NOT_DEPLOY"}
    if deployment_recommendation not in valid_recommendations:
        deployment_recommendation = "PROCEED_WITH_CONDITIONS"

    # Build legacy-compatible fields so aggregator reading summary/risk_reasoning
    # / recommendations continues to work without modification.
    summary = executive_summary or "Deterministic analysis reviewed."
    risk_reasoning = []
    if risk_narrative:
        risk_reasoning.append(risk_narrative)
    if primary_attack_scenario:
        risk_reasoning.append(f"Primary attack scenario: {primary_attack_scenario}")

    return {
        # ── Legacy fields (aggregator reads these) ────────────────────────
        "summary": summary,
        "risk_reasoning": risk_reasoning,
        "recommendations": reviewer_priorities,
        "confidence": confidence_val,
        "provider": provider_name,
        "available": True,

        # ── New structured synthesis fields (additive — aggregator ignores) ─
        "executive_summary": executive_summary,
        "risk_narrative": risk_narrative,
        "deployment_recommendation": deployment_recommendation,
        "primary_attack_scenario": primary_attack_scenario,
        "reviewer_priorities": reviewer_priorities,
        "confidence_explanation": confidence_explanation,
    }


def _default_response(provider_name: str = "unavailable") -> dict[str, Any]:
    return {
        # Legacy fields
        "summary": "",
        "risk_reasoning": [],
        "recommendations": [],
        "confidence": 0.0,
        "provider": provider_name,
        "available": False,

        # Synthesis fields (empty when unavailable)
        "executive_summary": "",
        "risk_narrative": "",
        "deployment_recommendation": "PROCEED_WITH_CONDITIONS",
        "primary_attack_scenario": "",
        "reviewer_priorities": [],
        "confidence_explanation": "",
    }
