from __future__ import annotations

import json
import os
import re
from typing import Any
from llm.context_assembly import AssembledContext

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
