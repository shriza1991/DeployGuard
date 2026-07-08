from __future__ import annotations

import logging
import time
from typing import Any

from infra_risk.analyzers import ANALYZERS, dedupe_findings


logger = logging.getLogger("infra-risk-agent.analyzers")


def build_analysis_context(payload: dict[str, Any]) -> dict[str, Any]:
    pr = payload.get("pull_request") or {}
    head_commit = payload.get("head_commit") or {}
    files: list[dict[str, Any]] = []

    if isinstance(payload.get("files"), list):
        files.extend(payload.get("files", []))
    if isinstance(payload.get("diffs"), list):
        files.extend(payload.get("diffs", []))

    if isinstance(payload.get("diff"), str) and payload.get("diff"):
        files.append({"filename": payload.get("filename", "<diff>"), "patch": payload.get("diff")})

    payload_changed_files = int(
        payload.get("changed_files")
        or pr.get("changed_files")
        or payload.get("pull_request", {}).get("changed_files")
        or 0
    )

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
    text = str(context.get("text") or "")
    findings = []

    logger.info("Analyzer started")
    for analyzer in ANALYZERS:
        analyzer_started_at = time.perf_counter()
        results = analyzer.analyze(text)
        findings.extend(results)
        contribution = sum(finding.weight for finding in results)
        logger.info(
            "Analyzer findings",
            extra={
                "analyzer": analyzer.name,
                "findings": len(results),
                "score_contribution": contribution,
                "execution_time_ms": round((time.perf_counter() - analyzer_started_at) * 1000, 2),
            },
        )
        logger.info("Score contribution: %s=%s", analyzer.name, contribution)

    findings = dedupe_findings(findings)
    score = int(max(0, min(100, sum(finding.weight for finding in findings))))

    if score <= 20:
        severity = "low"
    elif score <= 50:
        severity = "medium"
    elif score <= 80:
        severity = "high"
    else:
        severity = "critical"

    confidence = 60
    if findings:
        confidence = int(sum(finding.confidence for finding in findings) / len(findings))
    if context.get("patch_text"):
        confidence = min(100, confidence + 15)
    if context.get("text"):
        confidence = min(100, confidence + 5)

    reasons = [finding.reason for finding in findings]
    recommendations = [finding.recommendation for finding in findings]
    execution_time_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info("Final score: %s severity=%s execution_time_ms=%s", score, severity, execution_time_ms)

    return {
        "score": score,
        "severity": severity,
        "confidence": confidence,
        "reasons": reasons,
        "recommendations": recommendations,
        "metadata": {
            "changed_files": context.get("changed_file_count"),
            "changed_lines": context.get("changed_line_count"),
            "pull_request_title": (context.get("pull_request") or {}).get("title"),
            "pull_request_body": (context.get("pull_request") or {}).get("body"),
            "commit_message": (context.get("head_commit") or {}).get("message"),
            "repository": (context.get("repository") or {}).get("name"),
            "source": "pull_request" if context.get("pull_request") else "commit",
        },
    }
