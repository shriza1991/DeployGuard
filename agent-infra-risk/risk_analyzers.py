from __future__ import annotations

import logging
import time
from typing import Any

from infra_risk.analyzers import ANALYZERS, dedupe_findings


logger = logging.getLogger("infra-risk-agent.analyzers")

SEVERITY_WEIGHTS = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def build_analysis_context(payload: dict[str, Any]) -> dict[str, Any]:
    pr = payload.get("pull_request") or {}
    head_commit = payload.get("head_commit") or {}
    files: list[dict[str, Any]] = []
    if isinstance(payload.get("changed_files"), list):
        files.extend(payload.get("changed_files", []))

    if isinstance(payload.get("files"), list):
        files.extend(payload.get("files", []))
    if isinstance(payload.get("diffs"), list):
        files.extend(payload.get("diffs", []))

    if isinstance(payload.get("diff"), str) and payload.get("diff"):
        files.append({"filename": payload.get("filename", "<diff>"), "patch": payload.get("diff")})

    raw_cf = payload.get("changed_files")
    if isinstance(raw_cf, list):
        payload_changed_files = len(raw_cf)
    elif isinstance(raw_cf, (int, str)):
        try:
            payload_changed_files = int(raw_cf)
        except (ValueError, TypeError):
            payload_changed_files = 0
    else:
        payload_changed_files = int(pr.get("changed_files") or 0)

    file_names = "\n".join(str(item.get("filename", "")) for item in files if item.get("filename"))
    patch_text = "\n".join(str(item.get("patch", "")) for item in files if item.get("patch"))
    changed_file_count = len(files) if files else payload_changed_files
    changed_line_count = sum(
        len([line for line in str(item.get("patch", "")).splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))])
        for item in files
    )

    return {
        "payload": payload,
        "pull_request": pr,
        "head_commit": head_commit,
        "changed_files": files,
        "changed_file_count": changed_file_count,
        "payload_changed_file_count": payload_changed_files,
        "changed_line_count": changed_line_count,
        "patch_text": patch_text,
        "file_names": file_names,
        "repository": payload.get("repository") or {},
        "text": "\n".join(
            [
                str(pr.get("title", "")),
                str(pr.get("body", "")),
                str(head_commit.get("message", "")),
                str(payload.get("commit_message", "")),
                file_names,
                patch_text,
            ]
        ).lower(),
    }


def analyze_infra_risk(payload: dict[str, Any]) -> dict[str, Any]:
    started_at = time.perf_counter()
    context = build_analysis_context(payload)
    files = context.get("changed_files", [])
    patch_text = str(context.get("patch_text") or "")
    
    findings = []

    logger.info("Analyzer started on %d files", len(files))
    
    # Check if PR is documentation-only
    all_filenames = [str(f.get("filename", "")).lower() for f in files if f.get("filename")]
    is_docs_only = len(all_filenames) > 0 and all(
        fn.endswith((".md", ".txt", ".rst")) or fn.startswith("docs/") or "readme" in fn or "license" in fn
        for fn in all_filenames
    )

    if is_docs_only:
        deterministic_dicts: list[dict[str, Any]] = []
        return {
            "score": 0,
            "severity": "low",
            "confidence": 0.95,
            "reasons": ["Documentation-only pull request detected."],
            "recommendations": ["No infrastructure risk review required for documentation changes."],
            "deterministic_findings": deterministic_dicts,
            "metadata": {
                "changed_files": context.get("changed_file_count"),
                "changed_lines": context.get("changed_line_count"),
                "pull_request_title": (context.get("pull_request") or {}).get("title"),
                "pull_request_body": (context.get("pull_request") or {}).get("body"),
                "commit_message": (context.get("head_commit") or {}).get("message"),
                "repository": (context.get("repository") or {}).get("name"),
                "source": "pull_request" if context.get("pull_request") else "commit",
                "findings": deterministic_dicts,
                "deterministic_findings": deterministic_dicts,
            },
        }

    if files:
        for file_entry in files:
            filename = str(file_entry.get("filename", "") or file_entry.get("file_path", "") or "unknown")
            patch = str(file_entry.get("patch", "") or "")
            content_to_analyze = f"{filename}\n{patch}" if patch else filename
            
            for analyzer in ANALYZERS:
                results = analyzer.analyze(content_to_analyze, file_path=filename)
                findings.extend(results)
    else:
        text = str(context.get("text") or "")
        for analyzer in ANALYZERS:
            results = analyzer.analyze(text, file_path="infrastructure.yaml")
            findings.extend(results)

    findings = dedupe_findings(findings)

    # --- Adaptive Scoring ---
    has_diff = bool(patch_text.strip() or len(files) > 0)
    
    if findings:
        max_severity = max(SEVERITY_WEIGHTS.get(f.severity, 0) for f in findings)
        block_rules = [f for f in findings if f.policy_action == "BLOCK" or f.severity.upper() == "CRITICAL"]
        review_rules = [f for f in findings if f.policy_action == "REVIEW_REQUIRED" or f.severity.upper() == "HIGH"]
        
        if block_rules:
            # Critical / Block rule triggered -> Deterministic findings dominate
            score = max(85, min(100, sum(f.weight for f in findings)))
        elif review_rules:
            # High / Review rule triggered
            score = max(50, min(80, sum(f.weight for f in findings)))
        else:
            score = min(40, sum(f.weight for f in findings))
    else:
        score = 0

    # Severity string for agent payload
    if score >= 85 or any(f.severity.upper() == "CRITICAL" for f in findings):
        severity = "critical"
    elif score >= 50 or any(f.severity.upper() == "HIGH" for f in findings):
        severity = "high"
    elif score >= 20 or any(f.severity.upper() == "MEDIUM" for f in findings):
        severity = "medium"
    else:
        severity = "low"

    # --- Confidence Computation ---
    if has_diff and findings:
        confidence = 0.95
    elif has_diff:
        confidence = 0.88
    elif findings:
        confidence = 0.70
    else:
        confidence = 0.40

    reasons = [finding.reason for finding in findings]
    recommendations = [finding.recommendation for finding in findings]
    deterministic_findings_dicts = [f.to_dict() for f in findings]

    execution_time_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info("Final score: %s severity=%s confidence=%.2f execution_time_ms=%s", score, severity, confidence, execution_time_ms)

    return {
        "score": int(score),
        "severity": severity,
        "confidence": float(confidence),
        "reasons": reasons,
        "recommendations": recommendations,
        "deterministic_findings": deterministic_findings_dicts,
        "metadata": {
            "changed_files": context.get("changed_file_count"),
            "changed_lines": context.get("changed_line_count"),
            "pull_request_title": (context.get("pull_request") or {}).get("title"),
            "pull_request_body": (context.get("pull_request") or {}).get("body"),
            "commit_message": (context.get("head_commit") or {}).get("message"),
            "repository": (context.get("repository") or {}).get("name"),
            "source": "pull_request" if context.get("pull_request") else "commit",
            "findings": deterministic_findings_dicts,
            "deterministic_findings": deterministic_findings_dicts,
        },
    }

