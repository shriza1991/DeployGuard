"""
risk_analyzers
~~~~~~~~~~~~~~
Deterministic infrastructure security analysis for pull-request diffs.

Key design principles
---------------------
1. Only infrastructure files present in the PR diff are analyzed — never the
   whole repository.
2. Each file is routed to the correct analyzer(s) by filename pattern.
3. Scoring is purely additive (severity weights × decay) with synergy bonuses.
   No hardcoded per-rule score overrides.
4. If no infrastructure files are found in the diff the analysis returns
   immediately with score=0 and a descriptive message.
"""
from __future__ import annotations

import os
import logging
import re
import time
from pathlib import Path
from typing import Any

import requests

from infra_risk.analyzers import ANALYZERS, dedupe_findings
from infra_risk.analyzers.base import Finding

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
logger = logging.getLogger("infra-risk-agent.analyzers")




def _classify_file(filename: str) -> tuple[bool, list[str], str, str]:
    """
    Path-aware classification of filenames to infrastructure categories and analyzers.
    Returns: (is_infra_file, analyzer_names, category, display_name_or_skip_reason)
    """
    if not filename or filename in ("<unknown>", "<diff>"):
        return False, [], "unknown", "invalid filename"

    # Normalize slashes for cross-platform / Windows path compatibility
    norm_path = filename.replace("\\", "/").lower().strip()
    path_obj = Path(norm_path)
    basename = path_obj.name
    parent_parts = [p.lower() for p in path_obj.parts[:-1]]

    # 1. Dockerfile (e.g. Dockerfile, docker/Dockerfile, Dockerfile.dev, ci.dockerfile)
    if basename == "dockerfile" or basename.startswith("dockerfile.") or basename.endswith(".dockerfile"):
        return True, ["docker"], "docker", "Docker analyzer"

    # 2. Docker Compose (e.g. docker-compose.yml, docker/docker-compose.yaml, compose.yml, docker-compose.prod.yml)
    if (basename.startswith("docker-compose") or basename.startswith("compose")) and basename.endswith((".yml", ".yaml")):
        return True, ["docker_compose"], "docker_compose", "Docker Compose analyzer"

    # 3. Terraform (e.g. main.tf, terraform/main.tf, infra/main.tf, vars.tfvars)
    if basename.endswith(".tf") or basename.endswith(".tfvars"):
        return True, ["terraform"], "terraform", "Terraform analyzer"

    # 4. GitHub Actions (e.g. .github/workflows/ci.yml, .github/workflows/deploy.yaml)
    if ".github/workflows/" in norm_path and basename.endswith((".yml", ".yaml")):
        return True, ["github_actions"], "github_actions", "GitHub Actions analyzer"

    # 5. Kubernetes & Helm (e.g. kubernetes/deployment.yaml, k8s/deployment.yaml, helm/chart/values.yaml, deploy/pod.yml)
    is_yaml = basename.endswith((".yml", ".yaml"))
    k8s_file_stems = {
        "deployment", "service", "ingress", "statefulset", "daemonset",
        "job", "cronjob", "configmap", "pod", "replicaset", "namespace", "rbac",
        "clusterrole", "clusterrolebinding", "rolebinding", "networkpolicy",
        "hpa", "pvc", "pv", "storageclass", "serviceaccount", "chart", "values"
    }
    k8s_dir_keywords = {"kubernetes", "k8s", "manifests", "deploy", "helm", "templates"}

    if is_yaml:
        stem = path_obj.stem
        if stem in k8s_file_stems or basename in ("chart.yaml", "values.yaml"):
            return True, ["kubernetes"], "kubernetes", "Kubernetes analyzer"
        if any(d in k8s_dir_keywords for d in parent_parts) or "templates/" in norm_path:
            return True, ["kubernetes"], "kubernetes", "Kubernetes analyzer"

    # 6. nginx (e.g. nginx.conf, sites-available/default, app.nginx)
    if basename == "nginx.conf" or basename.endswith(".nginx") or "sites-available/" in norm_path or "sites-enabled/" in norm_path:
        return True, [], "nginx", "Nginx configuration"

    # 7. Caddyfile (e.g. Caddyfile, caddy/Caddyfile)
    if basename == "caddyfile" or basename.endswith(".caddyfile") or basename.startswith("caddyfile"):
        return True, [], "caddy", "Caddyfile configuration"

    # 8. cloud-init (e.g. cloud-init.yml, user-data)
    if basename.startswith("cloud-init") or basename.startswith("user-data"):
        return True, [], "cloud_init", "cloud-init configuration"

    # 9. Ansible (e.g. playbook.yml, site.yml, roles/web/tasks/main.yml)
    if basename.endswith((".ansible.yml", ".ansible.yaml")):
        return True, [], "ansible", "Ansible playbook"
    if is_yaml and (basename.startswith("playbook") or basename == "site.yml" or "roles/" in norm_path):
        return True, [], "ansible", "Ansible playbook"

    # Determine skip reason
    if basename.endswith((".md", ".txt", ".rst")) or "docs/" in norm_path or "readme" in basename or "license" in basename:
        skip_reason = "documentation file"
    elif basename.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".c", ".cpp", ".rs", ".rb", ".php")):
        skip_reason = "application source"
    else:
        skip_reason = "non-infrastructure file"

    return False, [], "skipped", skip_reason


# Map analyzer names to analyzer instances
_ANALYZER_BY_NAME: dict[str, Any] = {a.name: a for a in ANALYZERS}




def extract_github_pr_identifiers(payload: dict[str, Any]) -> tuple[str, str, Any, str]:
    """Extract owner, repo_name, pull_number, and pr_url from a GitHub webhook payload."""
    repo_obj = payload.get("repository") or {}
    pr_obj = payload.get("pull_request") or {}

    owner = ""
    if isinstance(repo_obj.get("owner"), dict):
        owner = repo_obj["owner"].get("login") or repo_obj["owner"].get("name") or ""
    full_name = repo_obj.get("full_name") or ""
    if not owner and "/" in full_name:
        owner = full_name.split("/")[0]

    repo_name = repo_obj.get("name") or ""
    if not repo_name and "/" in full_name:
        repo_name = full_name.split("/")[1]

    pull_number = pr_obj.get("number") or payload.get("number") or payload.get("pr_number")
    pr_url = pr_obj.get("url") or ""

    return owner, repo_name, pull_number, pr_url


def fetch_pull_request_files_from_api(
    owner: str = "",
    repo: str = "",
    pull_number: Any = None,
    pr_url: str = ""
) -> list[dict[str, Any]]:
    """Fetch PR files from GitHub REST API: GET /repos/{owner}/{repo}/pulls/{pull_number}/files"""
    files_url = None
    if owner and repo and pull_number:
        files_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files"
    elif pr_url:
        files_url = pr_url.rstrip("/") + "/files"

    if not files_url:
        return []

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "DeployGuard-Agent/1.0"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    try:
        response = requests.get(files_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
        return []
    except requests.RequestException:
        return []


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def _build_analysis_context(payload: dict[str, Any]) -> dict[str, Any]:
    pr = payload.get("pull_request") or {}
    head_commit = payload.get("head_commit") or {}

    seen_files: set[str] = set()
    files: list[dict[str, Any]] = []

    def _normalize_item(item: Any) -> dict[str, Any] | None:
        if isinstance(item, str) and item.strip():
            return {"filename": item.strip(), "patch": ""}
        elif isinstance(item, dict):
            fn = str(
                item.get("filename")
                or item.get("file_path")
                or item.get("path")
                or item.get("name")
                or ""
            ).strip()
            patch = str(item.get("patch") or item.get("diff") or "")
            if fn:
                return {"filename": fn, "patch": patch}
        return None

    sources = [
        payload.get("changed_files"),
        payload.get("files"),
        payload.get("diffs"),
        pr.get("files"),
        pr.get("changed_files"),
        pr.get("diffs"),
    ]

    if isinstance(head_commit, dict):
        commit_files = (head_commit.get("added") or []) + (head_commit.get("modified") or [])
        if commit_files:
            sources.append(commit_files)

    for src in sources:
        if isinstance(src, list):
            for item in src:
                norm = _normalize_item(item)
                if norm and norm["filename"] not in seen_files:
                    seen_files.add(norm["filename"])
                    files.append(norm)

    # Check if files already have non-empty patch text
    has_patches = any(isinstance(f, dict) and bool(f.get("patch")) for f in files)

    # If payload lacks files or patches, attempt GitHub API fetch
    if not files or not has_patches:
        owner, repo_name, pr_number, pr_url = extract_github_pr_identifiers(payload)
        fetched_files = fetch_pull_request_files_from_api(
            owner=owner, repo=repo_name, pull_number=pr_number, pr_url=pr_url
        )
        if fetched_files:
            for item in fetched_files:
                norm = _normalize_item(item)
                if norm and norm["filename"] not in seen_files:
                    seen_files.add(norm["filename"])
                    files.append(norm)

    # Single-file diff shorthand
    if isinstance(payload.get("diff"), str) and payload.get("diff"):
        fn = str(payload.get("filename") or "<diff>")
        if fn not in seen_files:
            seen_files.add(fn)
            files.append({
                "filename": fn,
                "patch": payload["diff"],
            })

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

    patch_text = "\n".join(str(f.get("patch", "")) for f in files if f.get("patch"))
    file_names = "\n".join(str(f.get("filename", "")) for f in files if f.get("filename"))
    changed_line_count = sum(
        len([
            line for line in str(f.get("patch", "")).splitlines()
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
        ])
        for f in files
    )

    return {
        "payload": payload,
        "pull_request": pr,
        "head_commit": head_commit,
        "changed_files": files,
        "changed_file_count": len(files) if files else payload_changed_files,
        "payload_changed_file_count": payload_changed_files,
        "changed_line_count": changed_line_count,
        "patch_text": patch_text,
        "file_names": file_names,
        "repository": payload.get("repository") or {},
        "text": "\n".join([
            str(pr.get("title", "")),
            str(pr.get("body", "")),
            str(head_commit.get("message", "")),
            str(payload.get("commit_message", "")),
            file_names,
            patch_text,
        ]).lower(),
    }


# ---------------------------------------------------------------------------
# Scoring model
# ---------------------------------------------------------------------------

_SEVERITY_BASE_WEIGHT: dict[str, float] = {
    "CRITICAL": 35.0,
    "HIGH": 20.0,
    "MEDIUM": 8.0,
    "LOW": 3.0,
}

_DECAY_MULTIPLIERS = [1.0, 0.7, 0.5, 0.3]


def _score_findings(findings: list[Finding], patch_text: str) -> tuple[float, float]:
    """Return (deterministic_score, pre_existing_penalty).

    Findings scored with severity-based weights and per-severity decay.
    Findings whose matched text does not appear in the diff are penalised
    (likely pre-existing).
    """
    by_severity: dict[str, list[Finding]] = {k: [] for k in _SEVERITY_BASE_WEIGHT}
    for f in findings:
        sev = f.severity.upper()
        bucket = sev if sev in by_severity else "MEDIUM"
        by_severity[bucket].append(f)

    det_score = 0.0
    penalty = 0.0
    has_patch = bool(patch_text.strip())

    for sev, group in by_severity.items():
        base_w = _SEVERITY_BASE_WEIGHT[sev]
        for idx, finding in enumerate(group):
            decay = _DECAY_MULTIPLIERS[min(idx, len(_DECAY_MULTIPLIERS) - 1)]
            effective = base_w * decay

            matched_str = str((finding.evidence or {}).get("matched") or "").strip()
            is_new = (matched_str and matched_str in patch_text) if has_patch else True

            if is_new:
                det_score += effective
            else:
                det_score += effective * 0.20
                penalty += effective * 0.80

    return round(det_score, 1), round(penalty, 1)



def _synergy_bonus(findings: list[Finding]) -> int:
    """Award bonus points for dangerous finding combinations."""
    rule_ids = {f.rule_id for f in findings}
    bonus = 0

    # Hardcoded credentials / secrets exposure
    if "HARDCODED_AWS_CREDENTIALS" in rule_ids or "HARDCODED_SECRET" in rule_ids:
        bonus += 60

    # Docker socket + root = trivial full host escape
    if "DOCKER_SOCK_MOUNT" in rule_ids and "DOCKER_ROOT_USER" in rule_ids:
        bonus += 20

    # Root + no healthcheck + latest tag: reliability + supply-chain compound
    if "DOCKER_ROOT_USER" in rule_ids and (
        "DOCKER_LATEST_TAG" in rule_ids or "DOCKER_MISSING_HEALTHCHECK" in rule_ids
    ):
        bonus += 10
    # Public S3 + wildcard IAM = full account data exposure
    if "TF_PUBLIC_S3" in rule_ids and "TF_WILDCARD_IAM" in rule_ids:
        bonus += 20
    # Public S3 + open ingress = fully exposed cloud env
    if "TF_PUBLIC_S3" in rule_ids and "TF_OPEN_INGRESS" in rule_ids:
        bonus += 15
    # Privileged K8s + host network = trivial node escape
    if "K8S_PRIVILEGED" in rule_ids and "K8S_HOST_NETWORK" in rule_ids:
        bonus += 15
    # K8s privileged + hostPath = confirmed node escape
    if "K8S_PRIVILEGED" in rule_ids and "K8S_HOST_PATH" in rule_ids:
        bonus += 15
    # Any secret exposure + any open network = credential immediately usable
    secret_rules = {"HARDCODED_AWS_CREDENTIALS", "HARDCODED_SECRET", "DOCKER_EXPOSED_SECRET", "GHA_SECRETS_ECHO"}
    open_net_rules = {"TF_OPEN_INGRESS", "TF_PUBLIC_S3", "TF_PUBLIC_DB", "COMPOSE_HOST_NETWORK"}
    if rule_ids & secret_rules and rule_ids & open_net_rules:
        bonus += 25
    # Two or more CRITICAL findings = systemic risk
    critical_count = sum(1 for f in findings if f.severity.upper() == "CRITICAL")
    if critical_count >= 2:
        bonus += 10

    return bonus


# ---------------------------------------------------------------------------
# Infra file presence bonus
# ---------------------------------------------------------------------------

def _infra_presence_score(infra_file_count: int) -> int:
    """Small base score reflecting that infra files are present in the PR."""
    if infra_file_count == 0:
        return 0
    # Max 5 points just for touching infra files (no findings)
    return min(5, 2 + infra_file_count)


# ---------------------------------------------------------------------------
# Severity label
# ---------------------------------------------------------------------------

def _severity_label(score: int, findings: list[Finding]) -> str:
    has_critical = any(f.severity.upper() == "CRITICAL" for f in findings)
    has_high = any(f.severity.upper() == "HIGH" for f in findings)
    has_medium = any(f.severity.upper() == "MEDIUM" for f in findings)

    if score >= 75 or has_critical:
        return "critical"
    if score >= 45 or has_high:
        return "high"
    if score >= 15 or has_medium:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------

def _compute_confidence(
    has_diff: bool,
    findings: list[Finding],
    infra_file_count: int,
) -> tuple[float, list[str]]:
    factors: list[str] = []

    if infra_file_count > 0:
        factors.append(f"{infra_file_count} infrastructure file(s) scoped from PR diff")
    if has_diff:
        factors.append("Patch text available for evidence matching")
    if findings:
        factors.append("Deterministic IaC security rules evaluated")
    else:
        factors.append("No infrastructure misconfigurations detected in scoped files")

    critical_or_high = [f for f in findings if f.severity.upper() in ("CRITICAL", "HIGH")]
    if critical_or_high:
        factors.append(f"{len(critical_or_high)} HIGH/CRITICAL finding(s) confirmed against diff")

    if has_diff and findings:
        confidence = 0.95
    elif has_diff and infra_file_count > 0:
        confidence = 0.92
    elif findings:
        confidence = 0.70
    elif infra_file_count > 0:
        confidence = 0.60
    else:
        confidence = 0.40

    return round(confidence, 2), factors


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

_NO_INFRA_MESSAGE = "No infrastructure-related files were modified in this pull request."


def analyze_infra_risk(payload: dict[str, Any]) -> dict[str, Any]:
    started_at = time.perf_counter()
    context = _build_analysis_context(payload)

    files: list[dict[str, Any]] = context["changed_files"]
    patch_text: str = context["patch_text"]

    # ── Documentation-only fast-path ─────────────────────────────────────────
    all_filenames = [str(f.get("filename", "")).lower() for f in files if f.get("filename")]
    is_docs_only = bool(all_filenames) and all(
        fn.endswith((".md", ".txt", ".rst")) or fn.startswith("docs/")
        or "readme" in fn or "license" in fn
        for fn in all_filenames
    )
    if is_docs_only:
        return _make_result(
            score=0,
            severity="low",
            confidence=0.95,
            confidence_factors=["Documentation-only pull request: no infrastructure risk analysis required"],
            findings=[],
            reasons=["Documentation-only pull request detected."],
            recommendations=["No infrastructure risk review required for documentation changes."],
            context=context,
            infra_file_count=0,
            started_at=started_at,
        )

    # ── DIAG 2: inputs handed to InfraFileRouter ───────────────────────────
    _router_input_names = [
        str(fe.get("filename") or fe.get("file_path") or "<unknown>")
        for fe in files
    ]
    logger.debug(
        "[infra-risk][diag] InfraFileRouter input — "
        "total_changed_files=%d files=%s",
        len(_router_input_names), _router_input_names,
    )
    # ─────────────────────────────────────────────────────────────────────────

    # ── Route each changed file to its analyzer(s) ───────────────────────────
    findings: list[Finding] = []
    infra_files_seen: list[str] = []

    if not files and context.get("text"):
        # Fallback for text/metadata-only payloads without explicit changed_files
        text_content = str(context.get("text") or "")
        for analyzer in ANALYZERS:
            results = analyzer.analyze(text_content, file_path="infrastructure.yaml")
            findings.extend(results)
        if findings:
            infra_files_seen.append("infrastructure.yaml")

    for file_entry in files:
        if isinstance(file_entry, str):
            filename = file_entry
            patch = ""
        elif isinstance(file_entry, dict):
            filename = str(
                file_entry.get("filename")
                or file_entry.get("file_path")
                or file_entry.get("path")
                or "unknown"
            )
            patch = str(file_entry.get("patch") or "")
        else:
            continue

        content = f"{filename}\n{patch}" if patch else filename

        logger.info("Received filename: %s", filename)

        is_infra, analyzer_names, category, display_or_reason = _classify_file(filename)

        if not is_infra:
            logger.info("%s → skipped (%s)", filename, display_or_reason)
            continue

        logger.info("%s → %s", filename, display_or_reason)
        infra_files_seen.append(filename)

        for name in analyzer_names:
            analyzer = _ANALYZER_BY_NAME.get(name)
            if analyzer:
                results = analyzer.analyze(content, file_path=filename)
                findings.extend(results)

    # Always run the secrets analyzer across ALL infra files (cross-cutting concern)
    secrets_analyzer = _ANALYZER_BY_NAME.get("secrets")
    if secrets_analyzer and infra_files_seen:
        for file_entry in files:
            filename = str(
                file_entry if isinstance(file_entry, str)
                else (file_entry.get("filename") or file_entry.get("file_path") or "unknown")
            )
            is_infra, _, _, _ = _classify_file(filename)
            if is_infra:
                patch = str(file_entry.get("patch") if isinstance(file_entry, dict) else "")
                content = f"{filename}\n{patch}" if patch else filename
                findings.extend(secrets_analyzer.analyze(content, file_path=filename))

    findings = dedupe_findings(findings)

    infra_file_count = len(infra_files_seen)

    # ── DIAG 3: InfraFileRouter output ────────────────────────────────────
    logger.debug(
        "[infra-risk][diag] InfraFileRouter output — "
        "infra_file_count=%d infra_files=%s",
        infra_file_count, infra_files_seen,
    )
    # ─────────────────────────────────────────────────────────────────────────

    # ── No infra files detected ───────────────────────────────────────────────
    if infra_file_count == 0:
        return _make_result(
            score=0,
            severity="low",
            confidence=0.98,
            confidence_factors=["PR diff contains no infrastructure files — analysis skipped"],
            findings=[],
            reasons=[_NO_INFRA_MESSAGE],
            recommendations=[],
            context=context,
            infra_file_count=0,
            started_at=started_at,
        )

    # ── Dynamic scoring ───────────────────────────────────────────────────────
    presence_score = _infra_presence_score(infra_file_count)
    det_score, pre_existing_penalty = _score_findings(findings, patch_text)
    synergy = _synergy_bonus(findings)

    # Urgency keywords in PR metadata (minimal contribution)
    pr_meta_text = context.get("text", "")
    metadata_score = 0
    if any(kw in pr_meta_text for kw in ("hotfix", "urgent", "bypass", "emergency", "skip review")):
        metadata_score = 3

    raw_total = presence_score + det_score + synergy + metadata_score
    score = int(max(0, min(100, round(raw_total))))

    if not findings:
        score = max(0, min(5, presence_score + metadata_score))

    severity = _severity_label(score, findings)
    has_diff = bool(patch_text.strip() or files)
    confidence, confidence_factors = _compute_confidence(has_diff, findings, infra_file_count)

    reasons = [f.reason for f in findings]
    recommendations = [f.recommendation for f in findings]

    breakdown = {
        "infra_file_presence": int(presence_score),
        "deterministic_findings": int(det_score),
        "synergy_bonus": int(synergy),
        "metadata": int(metadata_score),
        "pre_existing_penalty": int(pre_existing_penalty),
    }

    execution_time_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "Infra analysis complete: score=%s severity=%s findings=%d files=%d execution_ms=%s",
        score, severity, len(findings), infra_file_count, execution_time_ms,
    )

    return _make_result(
        score=score,
        severity=severity,
        confidence=confidence,
        confidence_factors=confidence_factors,
        findings=findings,
        reasons=reasons,
        recommendations=recommendations,
        context=context,
        infra_file_count=infra_file_count,
        started_at=started_at,
        breakdown=breakdown,
        infra_files_seen=infra_files_seen,
    )


def _make_result(
    *,
    score: int,
    severity: str,
    confidence: float,
    confidence_factors: list[str],
    findings: list[Finding],
    reasons: list[str],
    recommendations: list[str],
    context: dict[str, Any],
    infra_file_count: int,
    started_at: float,
    breakdown: dict[str, Any] | None = None,
    infra_files_seen: list[str] | None = None,
) -> dict[str, Any]:
    det_dicts = [f.to_dict() for f in findings]
    execution_time_ms = round((time.perf_counter() - started_at) * 1000, 2)

    if breakdown is None:
        breakdown = {
            "infra_file_presence": 0,
            "deterministic_findings": 0,
            "synergy_bonus": 0,
            "metadata": 0,
            "pre_existing_penalty": 0,
        }

    # Keep legacy breakdown keys for aggregator compatibility
    compat_breakdown = {
        "git_diff": breakdown.get("infra_file_presence", 0),
        "deterministic_findings": breakdown.get("deterministic_findings", 0),
        "repository_context": 0,
        "incident_history": 0,
        "metadata": breakdown.get("metadata", 0),
        "synergy_bonus": breakdown.get("synergy_bonus", 0),
        "pre_existing_penalty": breakdown.get("pre_existing_penalty", 0),
    }

    return {
        "score": score,
        "severity": severity,
        "confidence": confidence,
        "confidence_factors": confidence_factors,
        "reasons": reasons,
        "recommendations": recommendations,
        "deterministic_findings": det_dicts,
        "score_breakdown": compat_breakdown,
        "metadata": {
            "changed_files": context.get("changed_file_count"),
            "changed_lines": context.get("changed_line_count"),
            "infra_files_analyzed": infra_file_count,
            "infra_files": infra_files_seen or [],
            "pull_request_title": (context.get("pull_request") or {}).get("title"),
            "pull_request_body": (context.get("pull_request") or {}).get("body"),
            "commit_message": (context.get("head_commit") or {}).get("message"),
            "repository": (context.get("repository") or {}).get("name"),
            "source": "pull_request" if context.get("pull_request") else "commit",
            "findings": det_dicts,
            "deterministic_findings": det_dicts,
            "score_breakdown": compat_breakdown,
            "confidence_factors": confidence_factors,
            "analysis_execution_ms": execution_time_ms,
        },
    }
