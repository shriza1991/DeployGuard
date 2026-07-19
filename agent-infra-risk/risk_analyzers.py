from __future__ import annotations

import logging
import os
import sys
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


import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from technology_detector import infer_repository_capabilities
except ImportError:
    def infer_repository_capabilities(ctx):
        return {"docker", "kubernetes", "terraform", "github_actions", "secrets", "authentication"}


def analyze_infra_risk(payload: dict[str, Any]) -> dict[str, Any]:
    started_at = time.perf_counter()
    context = build_analysis_context(payload)
    files = context.get("changed_files", [])
    patch_text = str(context.get("patch_text") or "")
    
    capabilities = infer_repository_capabilities(context)
    findings = []

    logger.info("Analyzer started on %d files. Inferred capabilities: %s", len(files), capabilities)
    
    # Check if PR is documentation-only
    all_filenames = [str(f.get("filename", "")).lower() for f in files if f.get("filename")]
    is_docs_only = len(all_filenames) > 0 and all(
        fn.endswith((".md", ".txt", ".rst")) or fn.startswith("docs/") or "readme" in fn or "license" in fn
        for fn in all_filenames
    )

    if is_docs_only:
        deterministic_dicts: list[dict[str, Any]] = []
        breakdown = {
            "git_diff": 0,
            "deterministic_findings": 0,
            "repository_context": 0,
            "incident_history": 0,
            "metadata": 0,
            "synergy_bonus": 0,
            "pre_existing_penalty": 0,
        }
        return {
            "score": 0,
            "severity": "low",
            "confidence": 0.95,
            "reasons": ["Documentation-only pull request detected."],
            "recommendations": ["No infrastructure risk review required for documentation changes."],
            "deterministic_findings": deterministic_dicts,
            "score_breakdown": breakdown,
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
                "score_breakdown": breakdown,
                "inferred_capabilities": list(capabilities),
            },
        }

    analyzer_capability_map = {
        "docker": "docker",
        "kubernetes": "kubernetes",
        "terraform": "terraform",
        "github-actions": "github_actions",
        "docker-compose": "docker",
        "secrets": "secrets",
    }

    if files:
        for file_entry in files:
            filename = str(file_entry.get("filename", "") or file_entry.get("file_path", "") or "unknown")
            patch = str(file_entry.get("patch", "") or "")
            content_to_analyze = f"{filename}\n{patch}" if patch else filename
            
            for analyzer in ANALYZERS:
                analyzer_cap = analyzer_capability_map.get(getattr(analyzer, "name", ""), "secrets")
                if analyzer_cap in capabilities:
                    results = analyzer.analyze(content_to_analyze, file_path=filename)
                    findings.extend(results)
    else:
        text = str(context.get("text") or "")
        for analyzer in ANALYZERS:
            analyzer_cap = analyzer_capability_map.get(getattr(analyzer, "name", ""), "secrets")
            if analyzer_cap in capabilities:
                results = analyzer.analyze(text, file_path="infrastructure.yaml")
                findings.extend(results)

    findings = dedupe_findings(findings)

    # --- EVIDENCE ACCUMULATION SCORING MODEL ---
    file_count = int(context.get("changed_file_count") or 0)
    has_diff = bool(patch_text.strip() or len(files) > 0)

    if not has_diff and not findings:
        git_diff_score = 0
    else:
        git_diff_score = min(20, 5 + file_count * 3)

    severity_weights = {
        "CRITICAL": 35,
        "HIGH": 25,
        "MEDIUM": 12,
        "LOW": 4,
    }
    decay_multipliers = [1.0, 0.7, 0.5, 0.3]

    findings_by_severity: dict[str, list[Finding]] = {
        "CRITICAL": [],
        "HIGH": [],
        "MEDIUM": [],
        "LOW": [],
    }

    for f in findings:
        sev = f.severity.upper()
        if sev in findings_by_severity:
            findings_by_severity[sev].append(f)
        else:
            findings_by_severity["MEDIUM"].append(f)

    deterministic_findings_score = 0.0
    pre_existing_penalty = 0.0

    for sev, group in findings_by_severity.items():
        base_w = severity_weights.get(sev, 10)
        for idx, finding in enumerate(group):
            mult = decay_multipliers[min(idx, len(decay_multipliers) - 1)]
            effective_weight = base_w * mult
            
            matched_str = str((finding.evidence or {}).get("matched") or "").strip()
            is_new = bool(matched_str and matched_str in patch_text) if patch_text else True

            if is_new:
                deterministic_findings_score += effective_weight
            else:
                deterministic_findings_score += effective_weight * 0.20
                pre_existing_penalty += effective_weight * 0.80

    deterministic_findings_score = round(deterministic_findings_score)
    pre_existing_penalty = round(pre_existing_penalty)

    # Synergy Bonuses (Compound Risk)
    rule_ids = {f.rule_id for f in findings}
    synergy_bonus = 0

    if "DOCKER_ROOT_USER" in rule_ids and ("DOCKER_LATEST_TAG" in rule_ids or "DOCKER_REMOVED_NON_ROOT_USER" in rule_ids or "DOCKER_MISSING_HEALTHCHECK" in rule_ids):
        synergy_bonus += 15
    if "TERRAFORM_PUBLIC_S3" in rule_ids and ("TERRAFORM_OPEN_SSH" in rule_ids or "TERRAFORM_WILDCARD_IAM" in rule_ids or "TERRAFORM_PUBLIC_DB" in rule_ids):
        synergy_bonus += 20
    if "K8S_PRIVILEGED_POD" in rule_ids and ("K8S_HOST_NETWORK" in rule_ids or "K8S_UNSAFE_VOLUME_MOUNT" in rule_ids):
        synergy_bonus += 15
    if ("HARDCODED_AWS_CREDENTIALS" in rule_ids or "HARDCODED_SECRET" in rule_ids or "DOCKER_EXPOSED_SECRET" in rule_ids) and ("TERRAFORM_PUBLIC_S3" in rule_ids or "TERRAFORM_OPEN_SSH" in rule_ids):
        synergy_bonus += 25
    if len([f for f in findings if f.severity.upper() in {"CRITICAL", "HIGH"}]) >= 2:
        synergy_bonus += 10

    # PR Metadata Contribution
    text_content = str(context.get("text") or "").lower()
    metadata_score = 0
    if any(k in text_content for k in ("hotfix", "urgent", "bypass", "emergency")):
        metadata_score += 3

    # Total score calculation
    raw_total = git_diff_score + deterministic_findings_score + synergy_bonus + metadata_score
    score = int(max(0, min(100, raw_total)))

    # Target distribution overrides for specific high-risk scenarios
    if "HARDCODED_AWS_CREDENTIALS" in rule_ids or "HARDCODED_SECRET" in rule_ids:
        score = 100
    elif "TERRAFORM_OPEN_SSH" in rule_ids:
        score = max(score, 95)
    elif "TERRAFORM_PUBLIC_S3" in rule_ids:
        score = max(score, 92)
    elif "K8S_PRIVILEGED_POD" in rule_ids:
        score = max(score, 88)
    elif "DOCKER_ROOT_USER" in rule_ids and "DOCKER_LATEST_TAG" in rule_ids:
        score = max(score, 78)
    elif "DOCKER_ROOT_USER" in rule_ids:
        score = max(score, 65)
    elif "GITHUB_ACTIONS_EXCESSIVE_PERMISSIONS" in rule_ids or "GITHUB_ACTIONS_UNPINNED" in rule_ids:
        score = max(score, 65)

    if not findings:
        score = 0

    if score >= 85 or any(f.severity.upper() == "CRITICAL" for f in findings):
        severity = "critical"
    elif score >= 50 or any(f.severity.upper() == "HIGH" for f in findings):
        severity = "high"
    elif score >= 20 or any(f.severity.upper() == "MEDIUM" for f in findings):
        severity = "medium"
    else:
        severity = "low"

    # Confidence computation
    if has_diff and findings:
        confidence = 0.95
    elif has_diff:
        confidence = 0.88
    elif findings:
        confidence = 0.70
    else:
        confidence = 0.40

    breakdown = {
        "git_diff": int(git_diff_score),
        "deterministic_findings": int(deterministic_findings_score),
        "repository_context": 0,
        "incident_history": 0,
        "metadata": int(metadata_score),
        "synergy_bonus": int(synergy_bonus),
        "pre_existing_penalty": int(pre_existing_penalty),
    }

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
        "score_breakdown": breakdown,
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
            "score_breakdown": breakdown,
        },
    }


