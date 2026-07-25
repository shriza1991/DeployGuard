"""
analysis/language_classifier.py — Classify each changed file by its language/type.

Pure function, no I/O. Returns a canonical language tag string that maps to a
specific detector module in analysis/detectors/.
"""
from __future__ import annotations

import os
import re
from typing import Dict, Optional

# Kubernetes manifest keywords — YAML files containing these are k8s, not plain YAML
_K8S_KIND_PATTERN = re.compile(
    r"^\s*kind\s*:\s*(Deployment|Service|StatefulSet|DaemonSet|Pod|Ingress|"
    r"CronJob|Job|ConfigMap|Secret|PersistentVolumeClaim|ClusterRole|"
    r"ClusterRoleBinding|Role|RoleBinding|NetworkPolicy|Namespace|"
    r"HorizontalPodAutoscaler|ResourceQuota|LimitRange)\s*$",
    re.MULTILINE,
)

# GitHub Actions workflow path pattern
_GHA_PATH = re.compile(r"\.github[/\\]workflows[/\\].+\.(ya?ml)$", re.IGNORECASE)

# Helm chart file patterns
_HELM_CHART = re.compile(r"(?:Chart\.ya?ml|values(?:\.\w+)?\.ya?ml|templates?[/\\].+\.ya?ml)$", re.IGNORECASE)


def classify(filename: str, patch: str = "") -> str:
    """
    Return a canonical language tag for *filename*.

    The *patch* parameter is optional but improves accuracy for YAML files
    (distinguishes Kubernetes manifests from plain config YAML).

    Canonical tags:
        python, javascript, typescript, terraform, docker, kubernetes,
        github_actions, helm, shell, json, secrets, generic
    """
    lower = filename.lower()
    basename = os.path.basename(lower)

    # ── Secrets / env files ────────────────────────────────────────────────
    if basename in (".env", ".env.local", ".env.production", ".env.staging"):
        return "secrets"
    if re.search(r"(?:^|\/)secrets?\.\w+$", lower):
        return "secrets"

    # ── Dockerfile ─────────────────────────────────────────────────────────
    if "dockerfile" in basename or basename.endswith(".dockerfile"):
        return "docker"

    # ── GitHub Actions (before generic YAML) ───────────────────────────────
    if _GHA_PATH.search(filename):
        return "github_actions"

    # ── Helm (before generic YAML) ─────────────────────────────────────────
    if _HELM_CHART.search(filename):
        return "helm"

    # ── Terraform ──────────────────────────────────────────────────────────
    if lower.endswith((".tf", ".tfvars", ".tf.json")):
        return "terraform"

    # ── YAML — probe patch content for k8s kinds ───────────────────────────
    if lower.endswith((".yml", ".yaml")):
        # Known k8s path patterns
        if any(seg in lower for seg in ("k8s/", "kubernetes/", "manifests/", "deploy/", "helm/")):
            return "kubernetes"
        # Content probe (requires patch to be available)
        if patch and _K8S_KIND_PATTERN.search(patch):
            return "kubernetes"
        return "generic"   # plain YAML / config

    # ── Shell ──────────────────────────────────────────────────────────────
    if lower.endswith((".sh", ".bash", ".zsh", ".fish")):
        return "shell"

    # ── Python ─────────────────────────────────────────────────────────────
    if lower.endswith(".py"):
        return "python"

    # ── JavaScript / TypeScript ────────────────────────────────────────────
    if lower.endswith((".js", ".mjs", ".cjs", ".jsx")):
        return "javascript"
    if lower.endswith((".ts", ".tsx")):
        return "typescript"

    # ── JSON ───────────────────────────────────────────────────────────────
    if lower.endswith(".json"):
        return "json"

    # ── Fallback ───────────────────────────────────────────────────────────
    return "generic"


def classify_all(diff_files) -> None:
    """
    Mutates each DiffFile in *diff_files* in-place, setting its ``language``
    field.  Accepts any iterable of DiffFile objects.
    """
    for df in diff_files:
        df.language = classify(df.filename, df.patch)
