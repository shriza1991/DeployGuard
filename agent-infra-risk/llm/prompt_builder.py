from __future__ import annotations

import json
from typing import Any


PROMPT_TEMPLATE = """You are a Staff DevSecOps Security Engineer performing a deployment gate review for an infrastructure change.
Your job is to reason about blast radius, security impact, runtime behavior, and interactions between components.
You reason strictly from actual evidence and inferred project capabilities — never from generic assumptions.

-------------------------------------------------
Inferred Repository Capabilities: {capabilities}
(Do NOT assume any unlisted infrastructure, containers, or CI/CD tooling. Evaluate risk strictly within present capabilities.)

-------------------------------------------------
Git Diff (primary evidence — use this first)
{changed_files}

-------------------------------------------------
Deterministic Security Findings
Score   : {score}
Severity: {severity}
Confidence: {confidence:.2f}

Findings:
{findings}

Recommendations:
{recommendations}

-------------------------------------------------
PR Metadata (supporting context only — never the primary trigger for risk)
{metadata}

-------------------------------------------------
Task
Enrich the deterministic assessment with additional explanation, blast-radius analysis, and practical recommendations.
Think like a Staff DevSecOps Engineer:
  - WHAT specifically changed in the diff (cite file names, resource types, config values)?
  - WHY does it create deployment risk within the detected technology capabilities?
  - WHICH cloud resources, services, or security boundaries are directly or transitively affected?
  - HOW severe is the blast radius in production?
  - DOES the change weaken any security control (IAM, network ACL, encryption, access policy)?

Rules:
  - Base your reasoning on the diff and deterministic findings first.
  - Do NOT assume the presence of unmentioned infrastructure (e.g. do not complain about missing Dockerfiles if Docker is not used).
  - Do NOT trigger risk from PR title or description alone.
  - Do NOT invent findings absent from the diff or deterministic output.
  - If the change appears safe or does not modify security-critical controls, state so explicitly.

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
    confidence: float,
    reasons: list[str],
    recommendations: list[str],
    changed_files: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    findings_text = "\n".join(f"- {reason}" for reason in reasons) or "- none"
    recommendations_text = "\n".join(f"- {item}" for item in recommendations) or "- none"

    changed_files_parts = []
    for file_entry in changed_files[:10]:
        filename = file_entry.get("filename", "unknown")
        patch = file_entry.get("patch", "<no diff>")
        if patch and patch != "<no diff>":
            changed_files_parts.append(f"--- {filename} ---\n{patch[:1500].strip()}")
        else:
            changed_files_parts.append(f"--- {filename} --- (no patch available)")

    changed_files_text = "\n\n".join(changed_files_parts) or "- none"
    metadata_text = json.dumps(metadata, indent=2, sort_keys=True)
    
    inferred_caps = metadata.get("inferred_capabilities") or ["general_code"]
    capabilities_str = ", ".join(inferred_caps)

    return PROMPT_TEMPLATE.format(
        capabilities=capabilities_str,
        score=score,
        severity=severity,
        confidence=float(confidence),
        findings=findings_text,
        recommendations=recommendations_text,
        changed_files=changed_files_text,
        metadata=metadata_text,
    )
