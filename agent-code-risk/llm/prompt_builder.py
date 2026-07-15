from __future__ import annotations

import json
from typing import Any
from llm.context_assembly import AssembledContext

PROMPT_TEMPLATE_ORIGINAL = """You are reviewing a deployment risk assessment for a code change.

Deterministic analysis summary:
- score: {score}
- severity: {severity}
- confidence: {confidence}

Findings:
{findings}

Recommendations:
{recommendations}

Changed files:
{changed_files}

Metadata:
{metadata}

Your job is to enrich the deterministic assessment with additional explanation, risk reasoning, and practical recommendations.
Do not replace or overwrite the deterministic score, severity, confidence, reasons, or recommendations.
Do not use any data beyond the deterministic analyzer output and changed-file context.

IMPORTANT: Return ONLY a valid JSON object. No Markdown. No code fences. No explanations before or after the JSON.
The response must start with {{ and end with }} and contain nothing else.

Required JSON shape:
{{
  "summary": "...",
  "risk_reasoning": ["...", "..."],
  "recommendations": ["...", "..."],
  "confidence": 0.91
}}

If a section is not applicable, return an empty string or empty array, but still return valid JSON.
"""

PROMPT_TEMPLATE_EXTENDED = """You are reviewing a deployment risk assessment for a code change.

-------------------------------------------------
Repository Summary
Repository: {repository}
Branch: {branch}

-------------------------------------------------
Relevant Repository Evidence
{relevant_evidence}

-------------------------------------------------
Pull Request
Title: {pr_title}
Description: {pr_body}
Commit Message: {commit_message}

Changed Files:
{changed_files}

-------------------------------------------------
Deterministic Findings
Deterministic analysis summary:
- score: {score}
- severity: {severity}
- confidence: {confidence}

Findings:
{findings}

Recommendations:
{recommendations}

Metadata:
{metadata}

-------------------------------------------------
Task
Analyze deployment risk.
Use repository context only as supporting evidence.
Do not invent information that is not present in the evidence.
If repository context is unavailable, continue normally.

Your job is to enrich the deterministic assessment with additional explanation, risk reasoning, and practical recommendations.
Do not replace or overwrite the deterministic score, severity, confidence, reasons, or recommendations.

IMPORTANT: Return ONLY a valid JSON object. No Markdown. No code fences. No explanations before or after the JSON.
The response must start with {{ and end with }} and contain nothing else.

Required JSON shape:
{{
  "summary": "...",
  "risk_reasoning": ["...", "..."],
  "recommendations": ["...", "..."],
  "confidence": 0.91
}}

If a section is not applicable, return an empty string or empty array, but still return valid JSON.
"""


def build_prompt(
    score: Any = None,
    severity: str = "low",
    confidence: int = 0,
    reasons: list[str] = None,
    recommendations: list[str] = None,
    changed_files: list[dict[str, Any]] = None,
    metadata: dict[str, Any] = None,
) -> str:
    """
    Builds the Gemini prompt. Supports direct argument invocation for backward compatibility,
    as well as parsing the newer AssembledContext object when available.
    """
    # 1. Parse arguments (checking if score is an AssembledContext)
    if hasattr(score, "evidence_list"):
        context: AssembledContext = score
        score_val = context.score
        severity_val = context.severity
        confidence_val = context.confidence
        reasons_val = context.reasons
        recommendations_val = context.recommendations
        changed_files_val = context.changed_files
        metadata_val = context.metadata
        
        repository = context.repository
        branch = context.branch
        evidence_list = context.evidence_list
        pr_title = context.pr_title
        pr_body = context.pr_description
        commit_message = context.commit_message
    else:
        score_val = score if score is not None else 0
        severity_val = severity
        confidence_val = confidence
        reasons_val = reasons or []
        recommendations_val = recommendations or []
        changed_files_val = changed_files or []
        metadata_val = metadata or {}
        
        repository = "unknown"
        branch = "main"
        evidence_list = []
        pr_title = ""
        pr_body = ""
        commit_message = ""

    # 2. Format common components
    findings_text = "\n".join(f"- {reason}" for reason in reasons_val) or "- none"
    recommendations_text = "\n".join(f"- {item}" for item in recommendations_val) or "- none"

    changed_files_text = []
    for file_entry in changed_files_val[:10]:
        filename = file_entry.get("filename", "unknown")
        patch = file_entry.get("patch", "<no diff>")
        changed_files_text.append(f"* {filename}: {patch[:1000].strip()}")

    changed_files_text = "\n".join(changed_files_text) or "- none"
    metadata_text = json.dumps(metadata_val, indent=2, sort_keys=True)

    # 3. Format evidence list if available, or fall back to original template
    if evidence_list:
        ev_blocks = []
        for ev in evidence_list:
            meta = ev.metadata
            ev_repo = meta.get("repository") or repository
            ev_branch = meta.get("branch") or branch
            ev_file = meta.get("file_path") or "unknown"
            ev_lines = meta.get("lines") or "0-0"
            ev_kind = meta.get("kind") or "source"
            ev_score = meta.get("score")
            ev_score_str = f"{ev_score:.2f}" if ev_score is not None else "N/A"

            block = (
                f"Repository: {ev_repo}\n"
                f"Branch: {ev_branch}\n"
                f"File: {ev_file}\n"
                f"Lines: {ev_lines}\n"
                f"Kind: {ev_kind}\n"
                f"Similarity Score: {ev_score_str}\n"
                f"Evidence:\n"
                f"{ev.text}"
            )
            ev_blocks.append(block)

        relevant_evidence_text = "\n---\n".join(ev_blocks)
        
        return PROMPT_TEMPLATE_EXTENDED.format(
            repository=repository,
            branch=branch,
            relevant_evidence=relevant_evidence_text,
            pr_title=pr_title or "unknown",
            pr_body=pr_body or "unknown",
            commit_message=commit_message or "unknown",
            score=score_val,
            severity=severity_val,
            confidence=confidence_val,
            findings=findings_text,
            recommendations=recommendations_text,
            changed_files=changed_files_text,
            metadata=metadata_text,
        )
    else:
        return PROMPT_TEMPLATE_ORIGINAL.format(
            score=score_val,
            severity=severity_val,
            confidence=confidence_val,
            findings=findings_text,
            recommendations=recommendations_text,
            changed_files=changed_files_text,
            metadata=metadata_text,
        )
