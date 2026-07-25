"""
pipeline.py — Two-phase analysis pipeline orchestrator.

Phase 1: Deterministic security analysis (no LLM).
Phase 2: LLM security review (Gemini only, no raw webhook data).

Entry point: run_analysis_pipeline(payload) -> dict
The returned dict is aggregator-compatible (same key shape as before).
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("code-risk-agent")


def run_analysis_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs Phase 1 then Phase 2 and returns an aggregator-compatible result dict.

    Phase 1 — deterministic, no LLM:
        Parses the diff, classifies files, runs language-specific detectors,
        fetches repository context, and assembles an AnalysisReport.

    Phase 2 — LLM only, receives AnalysisReport (never the raw payload):
        Builds a structured prompt from verified findings,
        calls Gemini to reason and prioritize,
        returns a ReviewResult mapped to the aggregator shape.
    """
    report = _run_phase1(payload)
    result = _run_phase2(report)
    return result


# ---------------------------------------------------------------------------
# Phase 1
# ---------------------------------------------------------------------------

def _run_phase1(payload: Dict[str, Any]):
    """
    Deterministic analysis.  Returns an AnalysisReport.
    No LLM calls permitted here.
    """
    from analysis.models import AnalysisReport, SecurityFinding
    from analysis import diff_parser, language_classifier
    from analysis.detectors import run_all_detectors
    from analysis import repository_correlator
    from risk_analyzers import analyze_code_risk, build_analysis_context

    # ── 1. Parse diff into DiffFile objects ──────────────────────────────
    diff_files = diff_parser.parse(payload)

    # ── 2. Classify languages ─────────────────────────────────────────────
    language_classifier.classify_all(diff_files)

    # ── 3. Run language-specific detectors ────────────────────────────────
    new_findings: list[SecurityFinding] = []
    for df in diff_files:
        new_findings.extend(run_all_detectors(df))

    logger.info(
        "[phase1] Detectors produced %d findings across %d files",
        len(new_findings), len(diff_files),
    )

    # ── 4. Run existing risk_analyzers for score/severity/confidence ──────
    # The existing analyzer produces the legacy score model and backward-compat
    # fields that the aggregator depends on. We keep it to preserve the scoring.
    try:
        legacy = analyze_code_risk(payload)
    except Exception as exc:
        logger.warning("[phase1] risk_analyzers.analyze_code_risk failed: %s", exc)
        legacy = {
            "score": 0, "severity": "low", "confidence": 0.0,
            "reasons": [], "recommendations": [],
            "deterministic_findings": [], "score_breakdown": {},
            "metadata": {},
        }

    # Merge new detector findings into legacy so score reflects them
    legacy_findings_raw = legacy.get("deterministic_findings") or []

    # Convert new SecurityFinding objects to legacy dict format for aggregator compat
    for finding in new_findings:
        legacy_findings_raw.append({
            "category": finding.category,
            "subcategory": finding.detector,
            "rule_id": finding.rule_id,
            "severity": finding.severity,
            "confidence": finding.confidence,
            "evidence": {
                "file": finding.file,
                "line": finding.line_number,
                "matched": finding.matched_text,
            },
            "description": finding.rule_id,
            "recommendation": "",   # Phase 2 will provide this
            "reason": finding.matched_text,
            "weight": _severity_weight(finding.severity),
            "metadata": {"file": finding.file, "line_number": finding.line_number},
        })

    # ── 5. Fetch repository context ───────────────────────────────────────
    repo_chunks, ctx_metrics = repository_correlator.fetch(payload)
    logger.info("[phase1] Repository context: %d chunks, index_status=%s",
                len(repo_chunks), ctx_metrics.get("index_status", "unknown"))

    # ── 6. Build diff summary ─────────────────────────────────────────────
    files_added = [df.filename for df in diff_files if df.status == "added"]
    files_modified = [df.filename for df in diff_files if df.status == "modified"]
    files_deleted = [df.filename for df in diff_files if df.status == "deleted"]

    # ── 7. Extract PR / commit metadata ───────────────────────────────────
    pull_request = payload.get("pull_request") or {}
    head_commit = payload.get("head_commit") or {}
    repo_obj = payload.get("repository") or {}

    repository = (
        repo_obj.get("full_name") or repo_obj.get("name") or ""
    )
    branch = (
        (pull_request.get("head") or {}).get("ref")
        or repo_obj.get("default_branch")
        or "main"
    )
    commit = head_commit.get("id") or head_commit.get("sha") or ""

    meta = legacy.get("metadata") or {}

    # ── 8. Assemble AnalysisReport ─────────────────────────────────────────
    report = AnalysisReport(
        repository=repository,
        branch=branch,
        commit=commit,
        clone_url=repo_obj.get("clone_url") or "",
        files_added=files_added,
        files_modified=files_modified,
        files_deleted=files_deleted,
        diff_files=diff_files,
        findings=new_findings,
        repository_context=repo_chunks,
        score=legacy.get("score", 0),
        severity=legacy.get("severity", "low"),
        confidence=legacy.get("confidence", 0.0),
        legacy_reasons=list(legacy.get("reasons") or []),
        legacy_recommendations=list(legacy.get("recommendations") or []),
        legacy_deterministic_findings=legacy_findings_raw,
        metrics={
            "score_breakdown": legacy.get("score_breakdown", {}),
            "metadata": meta,
            "inferred_capabilities": list(meta.get("inferred_capabilities") or []),
            "repository_evidence_metrics": ctx_metrics,
            "index_status": ctx_metrics.get("index_status", "unknown"),
        },
        summary={
            "file_count": len(diff_files),
            "files_added": len(files_added),
            "files_modified": len(files_modified),
            "files_deleted": len(files_deleted),
            "new_finding_count": len(new_findings),
            "legacy_finding_count": len(legacy.get("deterministic_findings") or []),
        },
        pr_title=pull_request.get("title") or "",
        pr_description=pull_request.get("body") or "",
        commit_message=head_commit.get("message") or "",
    )

    logger.info(
        "[phase1] Report assembled: repo=%s branch=%s commit=%s "
        "findings=%d score=%d severity=%s",
        report.repository, report.branch, report.commit[:8] or "?",
        len(report.findings), report.score, report.severity,
    )
    return report


# ---------------------------------------------------------------------------
# Phase 2
# ---------------------------------------------------------------------------

def _run_phase2(report) -> Dict[str, Any]:
    """
    LLM security review.  Accepts AnalysisReport, returns aggregator dict.
    Only this function is allowed to call the LLM.
    """
    from llm.reviewer import SecurityReviewer, to_aggregator_payload

    reviewer = SecurityReviewer()
    review = reviewer.review(report)

    logger.info(
        "[phase2] Review complete: decision=%s confidence=%.2f "
        "findings_analysed=%d ai_observations=%d",
        review.deployment_decision,
        review.confidence,
        len(review.finding_analyses),
        len(review.ai_observations),
    )

    return to_aggregator_payload(review, report)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _severity_weight(severity: str) -> int:
    return {"CRITICAL": 35, "HIGH": 25, "MEDIUM": 12, "LOW": 4, "INFO": 1}.get(
        severity.upper(), 10
    )
