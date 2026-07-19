from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from incident_history.models import LLMResult, SimilarIncident
from incident_history.utils import normalized_json

logger = logging.getLogger("incident-history-agent")


class IncidentLLMReasoner:
    def __init__(self, provider, cache_ttl_seconds: int = 300):
        self.provider = provider
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[float, LLMResult]] = {}

    def analyze(
        self,
        deployment_document: str,
        deterministic_result: dict[str, Any],
        incidents: list[SimilarIncident],
    ) -> LLMResult:
        if not incidents:
            return LLMResult(
                provider=getattr(self.provider, "name", "unavailable"),
                available=False,
                summary="No historical incidents available.",
                risk_reasoning=[],
                recommendations=[],
                confidence=0.0,
            )

        prompt = _build_prompt(deployment_document, deterministic_result, incidents)
        cache_key = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        cached = self._cache.get(cache_key)
        if cached and time.time() - cached[0] < self.cache_ttl_seconds:
            return cached[1]

        result = self._generate_with_retries(prompt)
        self._cache[cache_key] = (time.time(), result)
        return result

    def _generate_with_retries(self, prompt: str) -> LLMResult:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                logger.info("LLM request started using provider %s", getattr(self.provider, "name", "unknown"))
                response = self.provider.analyze(prompt)
                logger.info("LLM response received from provider %s", getattr(self.provider, "name", "unknown"))
                result = _normalize_response(response, getattr(self.provider, "name", "unknown"))
                if not result.available:
                    return result
                return result
            except Exception as exc:
                last_error = exc
                logger.warning("LLM request failed (attempt %s/3): %s", attempt + 1, exc)
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
        logger.warning("LLM fallback activated: %s", last_error)
        return LLMResult(
            provider=getattr(self.provider, "name", "unavailable"),
            available=False,
            summary="Historical retrieval completed without LLM enrichment.",
            risk_reasoning=[],
            recommendations=[],
            confidence=0.0,
        )


def _build_prompt(deployment_document: str, deterministic_result: dict[str, Any], incidents: list[SimilarIncident]) -> str:
    incident_payload = [
        {
            "incident_id": item.incident_id,
            "similarity": item.similarity,
            "severity": item.severity,
            "outcome": item.outcome,
            "title": item.title,
            "description": item.description,
            "service": item.service,
            "environment": item.environment,
            "rollback": item.rollback,
            "root_cause": item.root_cause,
            "timestamp": item.timestamp,
            "tags": item.tags,
        }
        for item in incidents
    ]
    incident_text = json.dumps(incident_payload, indent=2, sort_keys=True)
    deterministic_text = normalized_json(deterministic_result)

    return (
        "You are a Staff DevSecOps Engineer analyzing historical incident patterns for DeployGuard.\n"
        "Your job is to reason about whether this deployment resembles previous production failures,\n"
        "identify recurring failure patterns, and produce actionable recommendations.\n"
        "You reason from the evidence provided — not from generic assumptions.\n\n"
        "-------------------------------------------------\n"
        "Deployment Being Evaluated\n"
        f"{deployment_document[:4000]}\n\n"
        "-------------------------------------------------\n"
        "Deterministic Risk Assessment\n"
        f"{deterministic_text}\n\n"
        "-------------------------------------------------\n"
        "Matched Historical Incidents (ordered by similarity)\n"
        f"{incident_text}\n\n"
        "-------------------------------------------------\n"
        "Task\n"
        "Analyze whether this deployment shares characteristics with the matched historical incidents.\n"
        "Think like a Staff DevSecOps Engineer:\n"
        "  - WHICH specific incidents (by incident_id) are most relevant, and WHY?\n"
        "  - WHAT root cause pattern do they share with this deployment?\n"
        "  - DID the matched incidents result in rollbacks or production failures?\n"
        "  - HOW severe was the blast radius of those historical incidents?\n"
        "  - WHAT concrete action should the team take before merging this change?\n\n"
        "Rules:\n"
        "  - Only cite incidents that are genuinely similar (similarity >= 0.70).\n"
        "  - Do NOT fabricate incident details not present in the provided data.\n"
        "  - If no incidents are highly similar, say so and recommend proceeding with caution.\n"
        "  - Confidence calibration:\n"
        "      >= 0.85 → multiple high-similarity incidents (>= 0.80) with matching root cause\n"
        "      0.65-0.84 → one or more moderate-similarity incidents (>= 0.70)\n"
        "      0.40-0.64 → low-similarity matches, pattern is weak\n"
        "      < 0.40 → no meaningful historical match found\n\n"
        "IMPORTANT: Return ONLY a valid JSON object. No Markdown. No code fences.\n"
        "Required JSON shape:\n"
        "{\n"
        '  "summary": "...",\n'
        '  "risk_reasoning": ["...", "..."],\n'
        '  "recommendations": ["...", "..."],\n'
        '  "confidence": 0.75,\n'
        '  "available": true\n'
        "}\n"
    )



def _normalize_response(response: dict[str, Any], provider_name: str) -> LLMResult:
    if not isinstance(response, dict):
        raise ValueError("LLM response was not a JSON object")
    return LLMResult(
        provider=provider_name,
        available=bool(response.get("available", True)),
        summary=str(response.get("summary") or ""),
        risk_reasoning=[str(item) for item in response.get("risk_reasoning", []) if str(item).strip()],
        recommendations=[str(item) for item in response.get("recommendations", []) if str(item).strip()],
        confidence=max(0.0, min(1.0, float(response.get("confidence", 0.0) or 0.0))),
    )

