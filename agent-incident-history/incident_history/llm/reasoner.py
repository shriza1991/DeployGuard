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
                summary="No similar historical incidents found in corpus.",
                risk_reasoning=["No matching historical failure patterns identified."],
                recommendations=["Standard code review and pre-deployment automated checks."],
                confidence=0.50,
                executive_summary="No similar historical incidents were found for this pull request.",
                common_failure_pattern="No recurring historical failure pattern identified.",
                risk_comparison="This deployment presents standard baseline risk as no matching past production incidents were retrieved.",
                historical_recommendations=["Enforce standard pre-deployment CI/CD unit and security testing."],
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
            risk_reasoning=["LLM reasoning provider unavailable."],
            recommendations=["Review retrieved similar incidents manually."],
            confidence=0.50,
        )


def _build_prompt(deployment_document: str, deterministic_result: dict[str, Any], incidents: list[SimilarIncident]) -> str:
    incident_payload = [
        {
            "incident_id": item.incident_id,
            "similarity": round(item.similarity, 3),
            "severity": item.severity,
            "outcome": item.outcome,
            "title": item.title,
            "summary": item.summary or item.description,
            "root_cause": item.root_cause,
            "impact": item.impact,
            "resolution": item.resolution,
            "lessons_learned": item.lessons_learned,
            "preventive_controls": item.preventive_controls,
            "tags": item.tags,
        }
        for item in incidents
    ]
    incident_text = json.dumps(incident_payload, indent=2, sort_keys=True)
    deterministic_text = normalized_json(deterministic_result)

    return (
        "You are an expert Staff DevSecOps Historical Reasoning Analyst for DeployGuard.\n"
        "Your task is to analyze an incoming pull request against retrieved historical production incidents.\n"
        "Compare the current pull request directly against the retrieved incidents rather than merely listing them.\n"
        "You must answer four core questions:\n"
        "  1. What happened before? (Summarize retrieved incidents, root causes, and resolutions)\n"
        "  2. How similar is this PR? (Compare specific diff patterns with past incidents)\n"
        "  3. What is different? (Identify attack surface differences that make this PR lower, similar, or higher risk)\n"
        "  4. What can we learn? (Derive actionable recommendations strictly from what resolved past incidents)\n\n"
        "-------------------------------------------------\n"
        "Pull Request Being Evaluated\n"
        f"{deployment_document[:4000]}\n\n"
        "-------------------------------------------------\n"
        "Deterministic Risk Summary\n"
        f"{deterministic_text}\n\n"
        "-------------------------------------------------\n"
        "Retrieved Historical Incidents (Ordered by Relevance)\n"
        f"{incident_text}\n\n"
        "-------------------------------------------------\n"
        "Instructions & Required Output JSON Format\n"
        "Return ONLY a valid JSON object with the following fields:\n"
        "{\n"
        '  "executive_summary": "High-level analytical summary comparing this PR to historical incidents.",\n'
        '  "common_failure_pattern": "Explanation of the underlying systemic weakness connecting the retrieved incidents (e.g. excessive container privileges combined with missing boundary controls).",\n'
        '  "risk_comparison": "Explicit risk comparison stating whether this PR is lower risk, similar risk, or higher risk than the retrieved incidents and why.",\n'
        '  "historical_recommendations": ["Recommendation 1 derived from past resolutions", "Recommendation 2..."],\n'
        '  "confidence": 0.85,\n'
        '  "available": true\n'
        "}\n"
    )


def _normalize_response(response: dict[str, Any], provider_name: str) -> LLMResult:
    if not isinstance(response, dict):
        raise ValueError("LLM response was not a JSON object")

    summary = str(response.get("summary") or response.get("executive_summary") or "")
    exec_summary = str(response.get("executive_summary") or summary)
    common_pattern = str(response.get("common_failure_pattern") or "")
    risk_comp = str(response.get("risk_comparison") or "")

    recs_raw = response.get("historical_recommendations") or response.get("recommendations") or []
    recs = [str(item) for item in recs_raw if str(item).strip()]

    reasoning_raw = response.get("risk_reasoning") or []
    reasoning = [str(item) for item in reasoning_raw if str(item).strip()]

    if not reasoning:
        reasoning = [r for r in [exec_summary, common_pattern, risk_comp] if r]

    return LLMResult(
        provider=provider_name,
        available=bool(response.get("available", True)),
        summary=summary or exec_summary,
        risk_reasoning=reasoning,
        recommendations=recs,
        confidence=max(0.0, min(1.0, float(response.get("confidence", 0.0) or 0.80))),
        executive_summary=exec_summary,
        common_failure_pattern=common_pattern,
        risk_comparison=risk_comp,
        historical_recommendations=recs,
    )
