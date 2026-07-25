"""
llm/reviewer.py — Phase 2: LLM Security Review.

Accepts a fully typed AnalysisReport (Phase 1 output) and returns a ReviewResult.
NEVER receives the raw webhook payload.
NEVER asks the LLM to detect vulnerabilities — only to reason about pre-verified findings.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Dict

from analysis.models import AnalysisReport, FindingAnalysis, ReviewResult
from llm.factory import get_provider
from llm.prompt_builder import build_security_review_prompt

logger = logging.getLogger("code-risk-llm")

_CACHE_TTL_SECONDS = 300


class SecurityReviewer:
    """
    Phase 2 entry point.

    Responsibilities:
    - Build a structured prompt from AnalysisReport (no raw payload data)
    - Call the configured LLM provider with retries
    - Parse and validate the structured JSON response
    - Return a ReviewResult mapping to the existing aggregator output shape
    """

    def __init__(self, provider=None, cache_ttl_seconds: int = _CACHE_TTL_SECONDS):
        self.provider = provider or get_provider()
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, tuple[float, ReviewResult]] = {}

    def review(self, report: AnalysisReport) -> ReviewResult:
        """
        Perform an LLM security review of *report* and return a ReviewResult.
        Falls back to a safe default on any LLM failure.
        """
        cache_key = self._cache_key(report)
        cached = self._cache.get(cache_key)
        if cached and time.time() - cached[0] < self.cache_ttl_seconds:
            logger.info("LLM review cache hit")
            return cached[1]

        prompt = build_security_review_prompt(report)
        raw_response = self._generate_with_retries(prompt)
        result = _parse_review_result(raw_response, provider_name=getattr(self.provider, "name", "unknown"))

        self._cache[cache_key] = (time.time(), result)
        return result

    def _generate_with_retries(self, prompt: str) -> Dict[str, Any]:
        last_error = None
        for attempt in range(3):
            try:
                logger.info(
                    "LLM security review request (attempt %d/3) via provider %s",
                    attempt + 1,
                    getattr(self.provider, "name", "unknown"),
                )
                response = self.provider.analyze(prompt)
                logger.info("LLM security review response received")
                return response
            except Exception as exc:
                last_error = exc
                logger.warning("LLM review failed (attempt %d/3): %s", attempt + 1, exc)
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))

        logger.warning("LLM security review unavailable after retries: %s", last_error)
        return {}

    def _cache_key(self, report: AnalysisReport) -> str:
        # Key on findings + repository identity — deterministic for the same input
        data = {
            "repository": report.repository,
            "commit": report.commit,
            "findings": [f.rule_id for f in report.findings],
            "score": report.score,
        }
        encoded = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _parse_review_result(raw: Dict[str, Any], provider_name: str) -> ReviewResult:
    """
    Parse and validate the LLM JSON response into a ReviewResult.
    Handles missing or malformed fields gracefully.
    """
    if not isinstance(raw, dict):
        logger.warning("LLM returned non-dict response: %r", raw)
        return _default_review(provider_name)

    # ── finding_analyses ──────────────────────────────────────────────────
    finding_analyses: list[FindingAnalysis] = []
    for item in raw.get("finding_analyses") or []:
        if not isinstance(item, dict):
            continue
        try:
            finding_analyses.append(FindingAnalysis(
                rule_id=str(item.get("rule_id") or "UNKNOWN"),
                severity=str(item.get("severity") or "MEDIUM"),
                why_dangerous=str(item.get("why_dangerous") or ""),
                exploitability=str(item.get("exploitability") or ""),
                blast_radius=str(item.get("blast_radius") or ""),
                false_positive_likelihood=str(item.get("false_positive_likelihood") or ""),
                block_recommendation=bool(item.get("block_recommendation", False)),
                remediation=str(item.get("remediation") or ""),
            ))
        except Exception as exc:
            logger.warning("Could not parse FindingAnalysis entry: %s — %s", item, exc)

    # ── deployment_decision ───────────────────────────────────────────────
    raw_decision = str(raw.get("deployment_decision") or "REVIEW").upper().strip()
    if raw_decision not in ("SAFE", "REVIEW", "BLOCK"):
        raw_decision = "REVIEW"

    # ── confidence ────────────────────────────────────────────────────────
    try:
        confidence = float(raw.get("confidence") or 0.0)
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.0

    return ReviewResult(
        executive_summary=str(raw.get("executive_summary") or ""),
        deployment_decision=raw_decision,
        finding_analyses=finding_analyses,
        ai_observations=[str(o) for o in (raw.get("ai_observations") or []) if str(o).strip()],
        prioritized_risks=[str(r) for r in (raw.get("prioritized_risks") or []) if str(r).strip()],
        remediation_plan=[str(r) for r in (raw.get("remediation_plan") or []) if str(r).strip()],
        confidence=confidence,
        confidence_rationale=str(raw.get("confidence_rationale") or ""),
        provider=provider_name,
        available=True,
    )


def _default_review(provider_name: str = "unavailable") -> ReviewResult:
    """Returned when the LLM is unreachable or returns an unparseable response."""
    return ReviewResult(
        executive_summary="",
        deployment_decision="REVIEW",
        finding_analyses=[],
        ai_observations=[],
        prioritized_risks=[],
        remediation_plan=[],
        confidence=0.0,
        confidence_rationale="LLM review was unavailable; confidence cannot be assessed.",
        provider=provider_name,
        available=False,
    )


def to_aggregator_payload(review: ReviewResult, report: AnalysisReport) -> Dict[str, Any]:
    """
    Map a ReviewResult + AnalysisReport to the existing aggregator-compatible dict shape.

    The following keys are UNCHANGED from the previous implementation and must
    remain stable for the aggregator and any downstream consumers:
        agent, correlation_id, score, severity, confidence, reasons,
        recommendations, metadata, llm

    New additive keys (ignored by current aggregator, available for future use):
        deployment_decision, finding_analyses, ai_observations,
        confidence_rationale, deterministic_findings
    """
    provider_name = getattr(review, "provider", "unavailable")

    return {
        # ── Unchanged aggregator contract ──────────────────────────────────
        "score": report.score,
        "severity": report.severity,
        "confidence": report.confidence,
        "reasons": report.legacy_reasons,
        "recommendations": report.legacy_recommendations,
        "deterministic_findings": report.legacy_deterministic_findings,
        "score_breakdown": report.metrics.get("score_breakdown", {}),
        "metadata": {
            **report.metrics.get("metadata", {}),
            "repository": report.repository,
            "branch": report.branch,
            "commit": report.commit,
            "repository_evidence_metrics": report.metrics.get("repository_evidence_metrics", {}),
            "inferred_capabilities": report.metrics.get("inferred_capabilities", []),
            "index_status": report.metrics.get("index_status", "unknown"),
        },
        "llm": {
            "provider": provider_name,
            "available": review.available,
            "summary": review.executive_summary,
            "risk_reasoning": review.prioritized_risks,
            "recommendations": review.remediation_plan,
            "confidence": review.confidence,
        },
        # ── New additive keys ──────────────────────────────────────────────
        "deployment_decision": review.deployment_decision,
        "finding_analyses": [fa.model_dump() for fa in review.finding_analyses],
        "ai_observations": review.ai_observations,
        "confidence_rationale": review.confidence_rationale,
    }
