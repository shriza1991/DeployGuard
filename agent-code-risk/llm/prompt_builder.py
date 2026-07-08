from __future__ import annotations

import json
from typing import Any


PROMPT_TEMPLATE = """You are reviewing a deployment risk assessment for a code change.

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


def build_prompt(
    score: int,
    severity: str,
    confidence: int,
    reasons: list[str],
    recommendations: list[str],
    changed_files: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    findings_text = "\n".join(f"- {reason}" for reason in reasons) or "- none"
    recommendations_text = "\n".join(f"- {item}" for item in recommendations) or "- none"

    changed_files_text = []
    for file_entry in changed_files[:10]:
        filename = file_entry.get("filename", "unknown")
        patch = file_entry.get("patch", "<no diff>")
        changed_files_text.append(f"* {filename}: {patch[:1000].strip()}")

    changed_files_text = "\n".join(changed_files_text) or "- none"
    metadata_text = json.dumps(metadata, indent=2, sort_keys=True)

    return PROMPT_TEMPLATE.format(
        score=score,
        severity=severity,
        confidence=confidence,
        findings=findings_text,
        recommendations=recommendations_text,
        changed_files=changed_files_text,
        metadata=metadata_text,
    )
