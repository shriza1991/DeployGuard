from __future__ import annotations

import json
import os
import re
from typing import Any, TYPE_CHECKING
from llm.context_assembly import AssembledContext

if TYPE_CHECKING:
    from analysis.models import AnalysisReport

def generate_chunk_summary(file_path: str, code_content: str) -> str:
    """
    Generates a compact summary of the chunk based on its filepath and contents.
    """
    # 1. Map of known files/components to clear summaries
    known_summaries = {
        "gateway/routers/webhook.py": "Handles webhook ingestion and Redis metadata persistence.",
        "gateway/redis.py": "Redis client initialization and connection management.",
        "gateway/app.py": "Gateway FastAPI application setup and middleware.",
        "gateway/routers/analytics.py": "Handles analytics query endpoints and data aggregation.",
        "gateway/routers/dashboard.py": "Handles dashboard querying and data serialization.",
        "gateway/routers/deployments.py": "Handles deployment event querying and lifecycle tracking.",
        "gateway/routers/incidents.py": "Handles incident querying and reporting endpoints.",
        "aggregator/redis_store.py": "Aggregator Redis storage and caching mechanisms.",
        "services/qdrant_service.py": "Manages connection, indexing, and vector searches on Qdrant.",
        "services/redis_service.py": "Handles connection, indexing status, and manifest caching in Redis.",
        "services/chunker.py": "Performs file chunking with language-specific heuristics.",
        "services/embedding_service.py": "Generates sentence embeddings for code search.",
        "services/indexer.py": "Coordinates repository cloning, chunking, and database indexing.",
        "services/clone_service.py": "Handles git cloning and branch management.",
    }
    
    # Check exact match or substring match in known_summaries
    normalized_path = file_path.replace("\\", "/")
    for path_key, summary in known_summaries.items():
        if normalized_path == path_key or path_key in normalized_path:
            return summary

    # 2. General heuristic fallback based on file type and content
    filename = os.path.basename(file_path)
    
    # Try to find class or function names in python
    classes = re.findall(r"class\s+(\w+)", code_content)
    functions = re.findall(r"def\s+(\w+)", code_content)
    
    if classes or functions:
        summary_parts = []
        if classes:
            summary_parts.append(f"Defines class{'es' if len(classes) > 1 else ''}: {', '.join(classes[:2])}")
        if functions:
            summary_parts.append(f"Defines function{'s' if len(functions) > 1 else ''}: {', '.join(functions[:3])}")
        return " ".join(summary_parts)

    if file_path.endswith(".md"):
        return f"Documentation file containing information about {filename}."
    elif file_path.endswith((".yml", ".yaml", ".json")):
        return f"Configuration file defining settings for {filename}."
    elif "dockerfile" in filename.lower():
        return "Dockerfile defining container build steps and environment setup."
    elif "docker-compose" in filename.lower():
        return "Docker Compose file defining services and dependencies."
    
    return f"Source code file containing implementation details for {filename}."

def generate_repo_context_summary(evidence_list: list[Any]) -> str:
    """
    Generates a compact repository context summary including files involved
    and related components based on the retrieved evidence chunks.
    """
    if not evidence_list:
        return ""

    # Extract unique files involved
    files_involved = []
    for ev in evidence_list:
        file_path = ev.metadata.get("file_path") or "unknown"
        if file_path not in files_involved:
            files_involved.append(file_path)

    # Determine related components based on files and text keywords
    related_components = []
    for ev in evidence_list:
        file_path = (ev.metadata.get("file_path") or "").lower()
        text = ev.text.lower()
        
        if "webhook" in file_path or "webhook" in text:
            related_components.append("Webhook routing")
            related_components.append("Webhook ingestion")
        if "redis" in file_path or "redis" in text:
            related_components.append("Redis lifecycle")
            related_components.append("Metadata persistence")
            related_components.append("Redis storage")
        if "qdrant" in file_path or "qdrant" in text:
            related_components.append("Qdrant vector search")
        if "embedding" in file_path or "embedding" in text:
            related_components.append("Embedding generation")
        if "indexer" in file_path or "chunker" in file_path:
            related_components.append("Repository indexing")
        if "clone" in file_path:
            related_components.append("Repository cloning")
        if "search" in file_path or "search" in text:
            related_components.append("Semantic search routing")
        if "incident" in file_path or "incident" in text:
            related_components.append("Incident reporting")
        if "dashboard" in file_path or "analytics" in file_path:
            related_components.append("Dashboard querying")
            related_components.append("Analytics aggregation")
        if "deployment" in file_path or "deployment" in text:
            related_components.append("Deployment tracking")

    # Deduplicate related components while preserving order
    unique_components = []
    for comp in related_components:
        if comp not in unique_components:
            unique_components.append(comp)

    # If no components matched, provide fallback
    if not unique_components:
        unique_components.append("General code analysis")

    # Build the summary string
    lines = [
        "Repository Context Summary",
        "",
        "Files involved:"
    ]
    for f in files_involved:
        lines.append(f)
    lines.append("")
    lines.append("Related components:")
    for c in unique_components:
        lines.append(c)
    lines.append("")
    
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
# Evidence ordering strictly enforces: Diff > Repo Context > Deterministic
# Findings > PR Metadata. Metadata (title/body/commit) comes LAST so the LLM
# never treats it as the primary risk signal.

PROMPT_TEMPLATE_ORIGINAL = """You are a Staff DevSecOps Security Engineer performing a deployment gate review.
Your job is to reason about blast radius, security impact, runtime behavior, and interaction between changes.
You reason strictly from actual evidence and inferred project capabilities — never from generic assumptions.

-------------------------------------------------
Inferred Repository Capabilities: {capabilities}
(Do NOT assume any unlisted infrastructure, containers, or CI/CD tooling. Evaluate risk strictly within present capabilities.)

-------------------------------------------------
Git Diff (primary evidence)
{changed_files}

-------------------------------------------------
Deterministic Security Findings
Score  : {score}
Severity: {severity}
Confidence: {confidence:.2f}

Findings:
{findings}

Recommendations:
{recommendations}

-------------------------------------------------
PR Metadata (supporting evidence only — never the primary trigger)
{metadata}

-------------------------------------------------
Task
Enrich the deterministic assessment with additional explanation, blast-radius analysis, and practical recommendations.
Think like a Staff DevSecOps Engineer:
  - WHAT specifically changed in the diff?
  - WHY does it create deployment risk?
  - WHICH systems, services, or security boundaries are affected?
  - HOW severe is the potential blast radius?

Rules:
  - Base your reasoning on the diff and deterministic findings above.
  - Do NOT assume the presence of unmentioned infrastructure.
  - Do NOT trigger risk from PR title/description alone.
  - Do NOT invent findings absent from the diff.
  - If no risk is found, say so clearly and return a low confidence score.
  - Calibrate confidence: HIGH if backed by diff evidence; LOW if metadata-only.

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

PROMPT_TEMPLATE_EXTENDED = """You are a Staff DevSecOps Security Engineer performing a deployment gate review.
Your job is to reason about blast radius, security impact, runtime behavior, and interaction between changes.
You reason strictly from actual evidence and inferred project capabilities — never from generic assumptions.

-------------------------------------------------
Repository: {repository}   Branch: {branch}
Inferred Repository Capabilities: {capabilities}
(Do NOT assume any unlisted infrastructure, containers, or CI/CD tooling. Evaluate risk strictly within present capabilities.)

-------------------------------------------------
Git Diff (primary evidence — use this first)
{changed_files}

-------------------------------------------------
Repository Context (related code retrieved via semantic search)
{relevant_evidence}

-------------------------------------------------
Deterministic Security Findings
Score  : {score}
Severity: {severity}
Confidence: {confidence:.2f}

Findings:
{findings}

Recommendations:
{recommendations}

-------------------------------------------------
PR Metadata (supporting context only — never the primary trigger for risk)
Title      : {pr_title}
Description: {pr_body}
Commit     : {commit_message}

-------------------------------------------------
Task
Enrich the deterministic assessment with additional explanation, blast-radius analysis, and practical recommendations.
Think like a Staff DevSecOps Engineer:
  - WHAT specifically changed in the diff (cite file names, line content)?
  - WHY does it create deployment risk (security boundary, data exposure, privilege escalation)?
  - WHICH downstream systems, services, or security boundaries are affected?
  - HOW severe is the potential blast radius?
  - DOES the repository context show that related components depend on what changed?

Rules:
  - Base your reasoning on the diff and deterministic findings first.
  - Use repository context only as supporting evidence for downstream impact.
  - Do NOT trigger risk from PR title or description alone.
  - Do NOT invent findings absent from the diff.
  - If no risk is found, say so clearly.
  - Confidence calibration:
      >= 0.90 → finding backed by explicit diff evidence + deterministic rule
      0.70-0.89 → finding backed by diff but no deterministic rule
      0.50-0.69 → finding inferred from context, no diff line match
      < 0.50 → metadata-only, no diff or context evidence

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
    confidence: float = 0.0,
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
        confidence_val = float(context.confidence)
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
        confidence_val = float(confidence) if confidence else 0.0
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

    # Build diff section: file path header + patch content, truncated to 1500 chars per file
    changed_files_text = []
    for file_entry in (changed_files_val or [])[:10]:
        filename = file_entry.get("filename", "unknown")
        patch = file_entry.get("patch", "<no diff>")
        if patch and patch != "<no diff>":
            changed_files_text.append(f"--- {filename} ---\n{patch[:1500].strip()}")
        else:
            changed_files_text.append(f"--- {filename} --- (no patch available)")

    changed_files_text_str = "\n\n".join(changed_files_text) or "- none"
    metadata_text = json.dumps(metadata_val, indent=2, sort_keys=True)

    inferred_caps = metadata_val.get("inferred_capabilities") or ["general_code"]
    capabilities_str = ", ".join(inferred_caps)

    # 3. Format evidence list if available, or fall back to original template
    if evidence_list:
        summary_block = generate_repo_context_summary(evidence_list)
        
        ev_blocks = []
        for ev in evidence_list:
            meta = ev.metadata
            ev_file = meta.get("file_path") or "unknown"
            ev_score = meta.get("score")
            score_val_str = f"{ev_score:.3f}" if ev_score is not None else "N/A"
            reason_matched = meta.get("retrieval_reason") or "Semantic similarity lookup"

            block = (
                f"File: {ev_file}\n"
                f"Matched chunk:\n{ev.text}\n"
                f"Similarity: {score_val_str}\n"
                f"Reason matched: {reason_matched}"
            )
            ev_blocks.append(block)

        evidence_section = "Repository Search Evidence\n\n" + "\n\n--------------------\n\n".join(ev_blocks)
        
        if summary_block:
            relevant_evidence_text = summary_block + "\n" + evidence_section
        else:
            relevant_evidence_text = evidence_section
        
        return PROMPT_TEMPLATE_EXTENDED.format(
            repository=repository,
            branch=branch,
            capabilities=capabilities_str,
            relevant_evidence=relevant_evidence_text,
            pr_title=pr_title or "unknown",
            pr_body=pr_body or "unknown",
            commit_message=commit_message or "unknown",
            score=score_val,
            severity=severity_val,
            confidence=confidence_val,
            findings=findings_text,
            recommendations=recommendations_text,
            changed_files=changed_files_text_str,
        )
    else:
        return PROMPT_TEMPLATE_ORIGINAL.format(
            capabilities=capabilities_str,
            score=score_val,
            severity=severity_val,
            confidence=confidence_val,
            findings=findings_text,
            recommendations=recommendations_text,
            changed_files=changed_files_text_str,
            metadata=metadata_text,
        )


# =============================================================================
# Phase 2 prompt — build_security_review_prompt
# =============================================================================
# This function is the ONLY prompt entry point for Phase 2.
# It receives a fully typed AnalysisReport — never the raw webhook payload.
# The LLM is instructed to REASON, not to DETECT.
# =============================================================================

_SYSTEM_ROLE = """\
You are a Staff Application Security Engineer conducting a professional pull request \
security review for a production deployment gate.

Your ONLY job is to REASON about the verified findings below — not to discover new ones.

MANDATORY RULES:
1. Every conclusion MUST reference a specific rule_id, filename, or quoted line of code.
2. Do NOT produce generic statements such as "large PR", "many files changed", or \
"manual review recommended" unless they directly follow from a cited finding.
3. Do NOT invent vulnerabilities not present in the Verified Findings section.
4. AI Observations MUST cite a specific file or diff line — never speculate in the abstract.
5. Confidence must be explained in plain language, not just stated as a number.
"""

_FINDINGS_PROMPT = """\
{system_role}

=== VERIFIED SECURITY FINDINGS ({finding_count} total) ===
{findings_block}

=== REPOSITORY CONTEXT (semantic neighbors of changed files) ===
{context_block}

=== DIFF SUMMARY ===
Repository : {repository}
Branch     : {branch}
Commit     : {commit}
Files      : {file_summary}
Languages  : {languages}
Functions modified: {functions}
Imports added     : {imports}

PR Title  : {pr_title}
Commit Msg: {commit_message}

=== YOUR TASK ===

For EACH finding in the Verified Findings list above, answer ALL SIX questions.
Use the finding's rule_id as a header. Be specific — cite the matched text, filename, \
and line number in your answers.

For each finding, structure your answer as a JSON object with these exact fields:
  rule_id                  — copy from the finding
  severity                 — copy from the finding
  why_dangerous            — Q1: WHY IS THIS DANGEROUS? Explain the security implication \
in practical, concrete terms. Not a textbook definition.
  exploitability           — Q2: CAN THIS BE EXPLOITED? Describe a realistic attack scenario \
an adversary could execute against this specific codebase.
  blast_radius             — Q3: WHAT SYSTEMS COULD BE AFFECTED? Name specific services, \
data stores, or infrastructure components at risk.
  false_positive_likelihood — Q4: IS THIS LIKELY A FALSE POSITIVE? Give your reasoning. \
Consider context, test code, and the specific matched text.
  block_recommendation     — Q5: SHOULD THIS BLOCK DEPLOYMENT? true or false, with a \
one-sentence rationale. Consider severity, exploitability, and blast radius.
  remediation              — Q6: WHAT IS THE SAFEST REMEDIATION? Give specific \
implementation guidance. Include code examples if relevant.

Then provide the overall review as additional top-level JSON fields:

  executive_summary        — 2-4 sentences. Reference specific rule_ids and files. \
Do not restate the full findings list.
  deployment_decision      — Exactly one of: "SAFE", "REVIEW", or "BLOCK".
                             BLOCK if any CRITICAL finding has block_recommendation=true.
                             REVIEW if any HIGH/MEDIUM finding warrants manual confirmation.
                             SAFE only if all findings are LOW/INFO with no exploitation path.
  ai_observations          — List of architectural/design concerns you observe that are \
NOT covered by the verified findings. Each entry MUST cite a specific file or diff line. \
Return [] if none.
  prioritized_risks        — Ordered list of the top risks, most severe first. \
Each entry must reference a rule_id.
  remediation_plan         — Ordered, actionable remediation steps. Each step must \
reference a specific file, line, or rule_id.
  confidence               — Float 0.0 to 1.0.
  confidence_rationale     — Explain in plain language why you chose this confidence \
level. Consider: diff coverage, finding quality, context availability.

Return ONLY a valid JSON object. No Markdown. No code fences. No text before or after the JSON.
The response must start with {{ and end with }}.

Required JSON shape:
{{
  "executive_summary": "...",
  "deployment_decision": "BLOCK",
  "finding_analyses": [
    {{
      "rule_id": "PY_SHELL_TRUE",
      "severity": "HIGH",
      "why_dangerous": "...",
      "exploitability": "...",
      "blast_radius": "...",
      "false_positive_likelihood": "...",
      "block_recommendation": true,
      "remediation": "..."
    }}
  ],
  "ai_observations": ["..."],
  "prioritized_risks": ["..."],
  "remediation_plan": ["..."],
  "confidence": 0.92,
  "confidence_rationale": "..."
}}
"""

_ARCH_REVIEW_PROMPT = """\
{system_role}

No deterministic security findings were detected for this change.

=== DIFF SUMMARY ===
Repository : {repository}
Branch     : {branch}
Commit     : {commit}
Files      : {file_summary}
Languages  : {languages}
Functions modified: {functions}
Imports added     : {imports}

PR Title  : {pr_title}
Commit Msg: {commit_message}

=== REPOSITORY CONTEXT ===
{context_block}

=== YOUR TASK — ARCHITECTURAL SECURITY REVIEW ===

Perform a professional architectural security review of this change.
Focus on dimensions that deterministic detectors cannot evaluate:

1. Authentication flows — are new endpoints/functions protected?
2. Authorization — are permission checks present where expected?
3. Request validation — are inputs validated and sanitized?
4. Secrets handling — are secrets accessed safely, not hardcoded?
5. Logging — could new log statements expose PII or sensitive operational data?
6. Configuration — are new settings production-safe (timeouts, limits, defaults)?
7. Dependency updates — are new packages or version bumps security-relevant?
8. CI/CD changes — do workflow changes affect security gates or deployment controls?
9. Deployment workflows — could new infra changes create unexpected exposure?

IMPORTANT:
- Every observation MUST cite a specific file, function name, or diff line.
- Do NOT raise concerns that you cannot tie to a specific code artifact.
- Do NOT produce generic warnings.
- Mark ALL your output as AI Observations — not Verified Findings.

Return ONLY valid JSON. No Markdown. No code fences.

Required JSON shape:
{{
  "executive_summary": "...",
  "deployment_decision": "SAFE",
  "finding_analyses": [],
  "ai_observations": [
    "app/auth.py: The new /admin/reset-password endpoint does not appear to check \
    the caller's role before processing the request (line ~47).",
    "...additional specific, cited observations..."
  ],
  "prioritized_risks": [],
  "remediation_plan": [],
  "confidence": 0.75,
  "confidence_rationale": "..."
}}
"""


def build_security_review_prompt(report: "AnalysisReport") -> str:
    """
    Build the Phase 2 Gemini prompt from a fully typed AnalysisReport.

    Selects between two templates:
    - _FINDINGS_PROMPT: when deterministic findings are present
    - _ARCH_REVIEW_PROMPT: when no findings were detected (architectural review only)

    Never sends the raw webhook payload to the LLM.
    """
    # ── Common fields ─────────────────────────────────────────────────────
    repo_ctx_lines: list[str] = []
    for chunk in report.repository_context[:8]:      # cap at 8 chunks
        repo_ctx_lines.append(
            f"File: {chunk.file}  Lines: {chunk.lines}  Similarity: {chunk.similarity:.2f}\n"
            f"Reason: {chunk.reason}\n"
            f"{chunk.text[:800]}\n"                  # cap per chunk for token budget
            f"---"
        )
    context_block = "\n".join(repo_ctx_lines) if repo_ctx_lines else "(no repository context available)"

    # Language breakdown
    lang_counts: dict[str, int] = {}
    all_functions: list[str] = []
    all_imports: list[str] = []
    file_statuses: dict[str, list[str]] = {"added": [], "modified": [], "deleted": []}

    for df in report.diff_files:
        lang_counts[df.language] = lang_counts.get(df.language, 0) + 1
        all_functions.extend(df.functions_modified)
        all_imports.extend(df.imports_added)
        status = df.status if df.status in file_statuses else "modified"
        file_statuses[status].append(df.filename)

    languages_str = ", ".join(
        f"{lang} ({cnt})" for lang, cnt in sorted(lang_counts.items(), key=lambda x: -x[1])
    ) or "unknown"

    file_summary_parts = []
    if report.files_added:
        file_summary_parts.append(f"added: {', '.join(report.files_added[:5])}")
    if report.files_modified:
        file_summary_parts.append(f"modified: {', '.join(report.files_modified[:5])}")
    if report.files_deleted:
        file_summary_parts.append(f"deleted: {', '.join(report.files_deleted[:5])}")
    file_summary = " | ".join(file_summary_parts) or f"{len(report.diff_files)} file(s)"

    unique_fns = list(dict.fromkeys(all_functions))[:10]
    unique_imports = list(dict.fromkeys(all_imports))[:10]

    common_kwargs = dict(
        system_role=_SYSTEM_ROLE,
        repository=report.repository or "unknown",
        branch=report.branch or "main",
        commit=report.commit[:12] if report.commit else "unknown",
        file_summary=file_summary,
        languages=languages_str,
        functions=", ".join(unique_fns) if unique_fns else "none detected",
        imports=", ".join(unique_imports) if unique_imports else "none detected",
        pr_title=report.pr_title or "(none)",
        commit_message=(report.commit_message or "(none)")[:200],
        context_block=context_block,
    )

    # ── Branch A: findings present ─────────────────────────────────────────
    if report.findings:
        findings_lines: list[str] = []
        for idx, finding in enumerate(report.findings, start=1):
            loc = f"{finding.file}"
            if finding.line_number:
                loc += f":{finding.line_number}"
            findings_lines.append(
                f"[{idx}] Rule: {finding.rule_id}  Severity: {finding.severity}  "
                f"Detector: {finding.detector}\n"
                f"    File: {loc}\n"
                f"    Matched: {finding.matched_text}\n"
                f"    Category: {finding.category}"
            )
        findings_block = "\n\n".join(findings_lines)

        return _FINDINGS_PROMPT.format(
            finding_count=len(report.findings),
            findings_block=findings_block,
            **common_kwargs,
        )

    # ── Branch B: no findings — architectural review ───────────────────────
    return _ARCH_REVIEW_PROMPT.format(**common_kwargs)
