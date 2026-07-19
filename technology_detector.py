from __future__ import annotations

import re
from typing import Any, Set


def infer_repository_capabilities(context: dict[str, Any]) -> Set[str]:
    """
    Holistically infers repository technology capabilities by combining:
    1. Repository Context & Evidence (RAG retrieved chunks, indexed context)
    2. Git Diff Patch Content & AST/Syntax tokens
    3. Changed File Contents
    4. Repository & PR Metadata

    Path-based heuristics alone NEVER determine analyzer activation.
    """
    capabilities: set[str] = set()

    files = context.get("changed_files", []) or []
    patch_text = str(context.get("patch_text") or "")
    text_content = str(context.get("text") or "").lower()
    evidence_list = context.get("evidence_list") or []

    # Assemble searchable text across all available sources
    all_content_parts = [patch_text, text_content]
    
    for f in files:
        if isinstance(f, dict):
            fn = str(f.get("filename", "") or f.get("file_path", ""))
            patch = str(f.get("patch", ""))
            all_content_parts.append(f"{fn}\n{patch}")

    for ev in evidence_list:
        ev_text = getattr(ev, "text", "") or str(ev)
        all_content_parts.append(ev_text)

    combined_text = "\n".join(all_content_parts)

    # --- Signal Layer 1: Docker / Containerization ---
    docker_patterns = (
        r"(?i)\bFROM\s+\S+",
        r"(?i)\bUSER\s+(?:root|0|\w+)\b",
        r"(?i)\bHEALTHCHECK\b",
        r"(?i)\bENTRYPOINT\b\s*\[",
        r"(?i)\bCMD\b\s*\[",
        r"(?i)docker-compose",
        r"(?i)\bcontainer[s]?\b",
        r"(?i)dockerfile",
    )
    if any(re.search(p, combined_text) for p in docker_patterns):
        capabilities.add("docker")

    # --- Signal Layer 2: Kubernetes / Container Orchestration ---
    k8s_patterns = (
        r"(?i)\bapiVersion:\s*",
        r"(?i)\bkind:\s*(?:Deployment|Pod|Service|Ingress|StatefulSet|DaemonSet|ConfigMap|Secret|CronJob)\b",
        r"(?i)\bsecurityContext:\b",
        r"(?i)\bprivileged:\s*(?:true|false)\b",
        r"(?i)\bhelm\b",
        r"(?i)\bk8s\b",
        r"(?i)deployment\.yaml",
        r"(?i)service\.yaml",
    )
    if any(re.search(p, combined_text) for p in k8s_patterns):
        capabilities.add("kubernetes")

    # --- Signal Layer 3: Terraform / Infrastructure as Code ---
    tf_patterns = (
        r"(?i)\bresource\s+[\"'][a-z0-9_]+[\"']\s+[\"'][a-z0-9_]+[\"']",
        r"(?i)\bprovider\s+[\"'][a-z0-9_]+[\"']",
        r"(?i)\bvariable\s+[\"'][a-z0-9_]+[\"']",
        r"(?i)\boutput\s+[\"'][a-z0-9_]+[\"']",
        r"(?i)\bterraform\b",
        r"(?i)\.tf\b",
        r"(?i)\.tfvars\b",
        r"(?i)aws_s3_bucket",
        r"(?i)aws_security_group",
    )
    if any(re.search(p, combined_text) for p in tf_patterns):
        capabilities.add("terraform")

    # --- Signal Layer 4: GitHub Actions / CI-CD ---
    gha_patterns = (
        r"(?i)\bjobs:\s*",
        r"(?i)\bon:\s*(?:push|pull_request|workflow_dispatch)",
        r"(?i)\buses:\s*actions/",
        r"(?i)\bpermissions:\s*",
        r"(?i)\.github/workflows",
        r"(?i)\.github/actions",
    )
    if any(re.search(p, combined_text) for p in gha_patterns):
        capabilities.add("github_actions")

    # --- Signal Layer 5: Database & Schema Migrations ---
    db_patterns = (
        r"(?i)\balter\s+table\b",
        r"(?i)\bcreate\s+table\b",
        r"(?i)\bdrop\s+column\b",
        r"(?i)\bdrop\s+table\b",
        r"(?i)\bmigration[s]?\b",
        r"(?i)\.sql\b",
        r"(?i)\balembic\b",
        r"(?i)\bprisma\b",
    )
    if any(re.search(p, combined_text) for p in db_patterns):
        capabilities.add("database_migration")

    # --- Signal Layer 6: Authentication & Access Control ---
    auth_patterns = (
        r"(?i)\bauth(?:entication)?\b",
        r"(?i)\bsession[s]?\b",
        r"(?i)\bjwt\b",
        r"(?i)\boauth\b",
        r"(?i)\bverify_token\b",
        r"(?i)\bcheck_session\b",
        r"(?i)\bmiddleware\b",
        r"(?i)\bacl\b",
        r"(?i)\brbac\b",
        r"(?i)\bpermission[s]?\b",
    )
    if any(re.search(p, combined_text) for p in auth_patterns):
        capabilities.add("authentication")

    # --- Signal Layer 7: Secrets & Sensitive Material (Universal) ---
    capabilities.add("secrets")

    return capabilities
