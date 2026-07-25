"""
pipeline.py — Two-phase analysis pipeline orchestrator.

Phase 1: Deterministic security analysis (no LLM).
Phase 2: LLM security review (Gemini only, no raw webhook data).

Entry point: run_analysis_pipeline(payload) -> dict
The returned dict is aggregator-compatible (same key shape as before).

Root cause of "changed_lines = 0" bug (fixed here):
    GitHub pull_request webhook payloads do NOT include file patch text.
    Patches must be fetched separately via GET /repos/{owner}/{repo}/pulls/{n}/files.
    risk_analyzers.build_analysis_context() already does this.
    Phase 1 must therefore call build_analysis_context() FIRST, then feed its
    enriched file list (with patches) into diff_parser.parse_files().
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger("code-risk-agent")


def run_analysis_pipeline(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runs Phase 1 then Phase 2 and returns an aggregator-compatible result dict.

    Phase 1 — deterministic, no LLM:
        1. build_analysis_context() — fetches full PR file list with patches from GitHub API
        2. diff_parser.parse_files() — parses patch text into structured DiffFile objects
        3. language_classifier — classifies each file's language
        4. detectors — run per-language security rule engines
        5. repository_correlator — fetches semantic context chunks
        6. Assembles AnalysisReport

    Phase 2 — LLM only, receives AnalysisReport (never the raw payload):
        Builds a structured prompt, calls Gemini, returns aggregator dict.
    """
    report = _run_phase1(payload)
    result = _run_phase2(report)
    return result


# ---------------------------------------------------------------------------
# Phase 1
# ---------------------------------------------------------------------------

def _run_phase1(payload: Dict[str, Any]):
    """
    Deterministic analysis pipeline.  Returns an AnalysisReport.
    No LLM calls permitted in this function or anything it calls.
    """
    from analysis.models import AnalysisReport, SecurityFinding
    from analysis import diff_parser, language_classifier
    from analysis.detectors import run_all_detectors
    from analysis import repository_correlator
    from risk_analyzers import analyze_code_risk, build_analysis_context, extract_github_pr_identifiers

    # =========================================================================
    # STEP 1 — Extract PR Identifiers & Build Enriched Analysis Context
    # =========================================================================
    owner, repo_name, pr_number, pr_url = extract_github_pr_identifiers(payload)
    context = build_analysis_context(payload)

    enriched_files: List[Dict[str, Any]] = context.get("changed_files") or []
    pull_request = context.get("pull_request") or {}
    head_commit = context.get("head_commit") or {}
    repo_obj = payload.get("repository") or {}

    repository = (
        repo_obj.get("full_name")
        or (f"{owner}/{repo_name}" if owner and repo_name else repo_obj.get("name") or "unknown")
    )
    branch = (
        (pull_request.get("head") or {}).get("ref")
        or repo_obj.get("default_branch")
        or "main"
    )
    commit = head_commit.get("id") or head_commit.get("sha") or ""

    files_with_patch = [f for f in enriched_files if f.get("patch")]
    files_without_patch = [f for f in enriched_files if not f.get("patch")]

    total_additions = sum(int(f.get("additions") or 0) for f in enriched_files)
    total_deletions = sum(int(f.get("deletions") or 0) for f in enriched_files)

    # Count added/removed lines from patch text if metadata missing
    if total_additions == 0 and total_deletions == 0:
        for f in enriched_files:
            patch = str(f.get("patch") or "")
            for line in patch.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    total_additions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    total_deletions += 1

    # =========================================================================
    # STEP 2 — Parse enriched file list into structured DiffFile objects
    # =========================================================================
    diff_files = diff_parser.parse_files(enriched_files)

    # =========================================================================
    # STEP 3 — Classify languages
    # =========================================================================
    language_classifier.classify_all(diff_files)

    lang_counts: Dict[str, int] = {}
    for df in diff_files:
        lang_counts[df.language] = lang_counts.get(df.language, 0) + 1

    # =========================================================================
    # STEP 4 — Run language-specific detectors
    # =========================================================================
    new_findings: list[SecurityFinding] = []
    detector_log: Dict[str, int] = {}

    for df in diff_files:
        findings_for_file = run_all_detectors(df)
        new_findings.extend(findings_for_file)
        count = len(findings_for_file)
        detector_log[df.filename] = count

    detectors_executed = sorted(list(set(df.language for df in diff_files)))

    # =========================================================================
    # STRUCTURED DEBUG LOGGING — Phase 1 Intake & Execution
    # =========================================================================
    logger.info("=" * 70)
    logger.info("[phase1] DEBUG LOGGING:")
    logger.info("  Repository               : %s", repository)
    logger.info("  PR Number                : %s", pr_number if pr_number is not None else "(none)")
    logger.info("  Files returned by GitHub : %d", len(enriched_files))
    logger.info("  Files containing patches : %d", len(files_with_patch))
    logger.info("  Files parsed             : %d", len(diff_files))
    logger.info("  Total additions          : %d", total_additions)
    logger.info("  Total deletions          : %d", total_deletions)
    logger.info("  Detectors executed       : %s", detectors_executed)
    logger.info("  Findings produced        : %d", len(new_findings))
    logger.info("=" * 70)

    if len(enriched_files) > 0 and len(files_with_patch) == 0:
        logger.warning(
            "[phase1] EXPLICIT WARNING: Deterministic security analysis cannot proceed to inspect source code diffs because patch data is missing! "
            "GitHub returned %d file(s) for repository '%s' PR #%s, but 0 files contained a unified diff patch string. "
            "Possible reasons: (1) GitHub API rate limit or authentication required (check GITHUB_TOKEN), "
            "(2) Changed files are all binary or empty, (3) The PR contains no line changes. "
            "Detectors require patch content to analyze code changes rather than repository metadata.",
            len(enriched_files), repository, pr_number
        )
    elif len(enriched_files) == 0:
        logger.warning(
            "[phase1] EXPLICIT WARNING: Deterministic security analysis cannot proceed because no changed files were returned for repository '%s' PR #%s.",
            repository, pr_number
        )

    # =========================================================================
    # STEP 5 — Run legacy risk_analyzers for score/severity/confidence
    # =========================================================================
    # analyze_code_risk() calls build_analysis_context() internally again.
    # This is acceptable — it preserves the existing score/confidence model
    # which the aggregator depends on.
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

    # Merge new detector findings into the legacy findings list
    legacy_findings_raw = list(legacy.get("deterministic_findings") or [])
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
            "recommendation": "",   # Phase 2 will provide remediation
            "reason": finding.matched_text,
            "weight": _severity_weight(finding.severity),
            "metadata": {"file": finding.file, "line_number": finding.line_number},
        })

    # =========================================================================
    # STEP 6 — Fetch repository semantic context
    # =========================================================================
    repo_chunks, ctx_metrics = repository_correlator.fetch(payload)

    index_status = ctx_metrics.get("index_status", "unknown")
    chunk_count = len(repo_chunks)
    ctx_available = chunk_count > 0

    logger.info("[phase1] REPOSITORY CONTEXT:")
    logger.info("  index_status     : %s", index_status)
    logger.info("  chunks_retrieved : %d", chunk_count)
    logger.info("  context_available: %s", ctx_available)
    if not ctx_available:
        if index_status == "unknown":
            logger.warning(
                "[phase1] Repository context unavailable — index_status=unknown. "
                "The Repository Context Service may be unreachable or the repository "
                "has never been indexed. Phase 2 will proceed without semantic context."
            )
        elif index_status == "indexing_in_progress":
            logger.info(
                "[phase1] Repository indexing is in progress — context will be "
                "available on the next analysis run."
            )
    else:
        for chunk in repo_chunks[:3]:   # log first 3 chunks only
            logger.info(
                "[phase1]   chunk: %s  lines=%s  similarity=%.2f  reason=%s",
                chunk.file, chunk.lines, chunk.similarity, chunk.reason,
            )

    # =========================================================================
    # STEP 7 — Assemble AnalysisReport
    # =========================================================================
    files_added = [df.filename for df in diff_files if df.status == "added"]
    files_modified = [df.filename for df in diff_files if df.status == "modified"]
    files_deleted = [df.filename for df in diff_files if df.status == "deleted"]

    meta = legacy.get("metadata") or {}

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
            "index_status": index_status,
        },
        summary={
            "file_count": len(diff_files),
            "files_added": len(files_added),
            "files_modified": len(files_modified),
            "files_deleted": len(files_deleted),
            "total_additions": total_additions,
            "total_deletions": total_deletions,
            "language_breakdown": lang_counts,
            "new_finding_count": len(new_findings),
            "legacy_finding_count": len(legacy.get("deterministic_findings") or []),
            "repository_context_available": ctx_available,
            "repository_context_chunks": chunk_count,
            "index_status": index_status,
        },
        pr_title=pull_request.get("title") or "",
        pr_description=pull_request.get("body") or "",
        commit_message=head_commit.get("message") or "",
    )

    logger.info("=" * 70)
    logger.info("[phase1] ANALYSIS REPORT ASSEMBLED")
    logger.info("  Repository          : %s", report.repository)
    logger.info("  Branch              : %s", report.branch)
    logger.info("  Commit              : %s", report.commit[:12] if report.commit else "?")
    logger.info("  Files parsed        : %d", len(diff_files))
    logger.info("  Total added lines   : %d", total_additions)
    logger.info("  Total removed lines : %d", total_deletions)
    logger.info("  Language breakdown  : %s", lang_counts)
    logger.info("  Detectors run       : %d files", len(diff_files))
    logger.info("  New findings        : %d", len(new_findings))
    logger.info("  Score (legacy)      : %d  severity=%s", report.score, report.severity)
    logger.info("  Context available   : %s  chunks=%d  status=%s",
                ctx_available, chunk_count, index_status)
    logger.info("=" * 70)

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
