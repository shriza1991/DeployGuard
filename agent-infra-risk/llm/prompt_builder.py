"""
llm.prompt_builder
~~~~~~~~~~~~~~~~~~~
Builds the synthesis prompt sent to the LLM after deterministic analysis.

The LLM is tasked with writing a DevSecOps security review narrative —
NOT repeating individual findings, but synthesizing across them.
"""
from __future__ import annotations

import json
from typing import Any


_SYNTHESIS_PROMPT = """You are a Staff DevSecOps engineer performing a deployment gate review.
You have received the output of a deterministic static analysis of the infrastructure files \
modified in this pull request.

Your job is to write a security review synthesis — not a list of findings, but an expert \
interpretation of what the findings mean together.

-------------------------------------------------
DETERMINISTIC ANALYSIS RESULTS
Score        : {score} / 100
Severity     : {severity}
Infrastructure Files Analyzed: {infra_files}

Findings ({finding_count} total):
{findings_json}

-------------------------------------------------
DIFF CONTEXT (primary evidence — cite filenames, resource names, config values)
{changed_files}

-------------------------------------------------
PR METADATA (supporting context only)
{metadata}

-------------------------------------------------
SYNTHESIS INSTRUCTIONS

Write the following six sections. Be specific and evidence-based.

1. executive_summary
   2-3 sentences. What is the most important security fact about this PR?
   Reference the actual files or resources changed.

2. risk_narrative
   How do the findings interact? Are these isolated issues or systemic risk?
   Distinguish between configuration hygiene (LOW/MEDIUM) and exploitable \
vulnerabilities (HIGH/CRITICAL).
   Reference specific finding rule_ids and what they mean together.

3. deployment_recommendation
   One of: PROCEED | PROCEED_WITH_CONDITIONS | DO_NOT_DEPLOY
   Justify your choice in one sentence.

4. primary_attack_scenario
   Describe the single most credible, highest-impact attack chain that becomes \
possible if this PR is merged and deployed.
   Name the specific resources, CVE patterns, or techniques involved.
   Only describe attack paths that are supported by the deterministic findings.

5. reviewer_priorities
   A list of exactly 2 or 3 action items for the human reviewer.
   Each item should be specific (file name, line, config key) rather than generic.

6. confidence_explanation
   Where is the analysis uncertain? What context would change the assessment?
   Mention if there were no infra files, no diff, or ambiguous patterns.

-------------------------------------------------
STRICT RULES

- Base every claim on the deterministic findings or the diff. \
Do NOT invent risks that are not evidenced.
- Do NOT repeat the raw finding text verbatim. Synthesize and explain.
- Do NOT produce findings for file types not present in the diff \
(e.g. no Kubernetes findings if no k8s files were modified).
- If all findings are LOW severity or the score is below 15, \
state clearly that the change appears low-risk.
- If there are NO findings, say so and recommend PROCEED.

IMPORTANT: Return ONLY a valid JSON object. No Markdown. No code fences. \
No text before or after the JSON.
The response must start with {{ and end with }}.

Required JSON shape:
{{
  "executive_summary": "...",
  "risk_narrative": "...",
  "deployment_recommendation": "PROCEED",
  "primary_attack_scenario": "...",
  "reviewer_priorities": ["...", "...", "..."],
  "confidence_explanation": "...",
  "confidence": 0.91
}}
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
    # Format the deterministic findings as structured JSON for the LLM
    det_findings = metadata.get("deterministic_findings") or []
    finding_count = len(det_findings)

    # Compact JSON representation (rule_id, severity, what_changed, attack_path)
    findings_for_prompt = []
    for f in det_findings[:20]:  # cap at 20 to stay within token budget
        findings_for_prompt.append({
            "rule_id": f.get("rule_id"),
            "severity": f.get("severity"),
            "file": (f.get("evidence") or {}).get("file"),
            "matched": (f.get("evidence") or {}).get("matched"),
            "what_changed": f.get("what_changed") or f.get("description"),
            "attack_path": f.get("attack_path") or "",
            "blast_radius": f.get("blast_radius") or "",
        })
    findings_json = json.dumps(findings_for_prompt, indent=2) if findings_for_prompt else "[]"

    # Changed files diff context (capped per file to stay in token budget)
    changed_files_parts: list[str] = []
    for file_entry in changed_files[:10]:
        filename = file_entry.get("filename", "unknown")
        patch = file_entry.get("patch", "<no diff>")
        if patch and patch != "<no diff>":
            changed_files_parts.append(f"--- {filename} ---\n{patch[:1200].strip()}")
        else:
            changed_files_parts.append(f"--- {filename} --- (no patch available)")
    changed_files_text = "\n\n".join(changed_files_parts) or "- no diff available"

    # Infra files list
    infra_files = metadata.get("infra_files") or []
    infra_files_str = ", ".join(infra_files) if infra_files else "none"

    metadata_text = json.dumps(
        {k: v for k, v in metadata.items() if k not in ("findings", "deterministic_findings",
                                                          "score_breakdown", "confidence_factors")},
        indent=2, sort_keys=True, default=str,
    )

    return _SYNTHESIS_PROMPT.format(
        score=score,
        severity=severity,
        infra_files=infra_files_str,
        finding_count=finding_count,
        findings_json=findings_json,
        changed_files=changed_files_text,
        metadata=metadata_text,
    )
