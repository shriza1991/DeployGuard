from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

SECURITY_TERMS = {
    "auth",
    "crypto",
    "vulnerability",
    "privilege",
    "security",
    "secret",
    "token",
    "permission",
    "acl",
    "encryption",
    "hash",
    "jwt",
    "oauth",
    "session",
}

AUTH_TERMS = {
    "auth",
    "login",
    "signin",
    "session",
    "token",
    "jwt",
    "oauth",
    "permission",
    "role",
    "acl",
    "access",
}

DB_TERMS = {
    "migrate",
    "migration",
    "schema",
    "database",
    "sql",
    "ddl",
    "alter table",
    "create table",
    "drop column",
    "drop table",
    "index",
    "constraint",
}

CONFIG_TERMS = {
    "port",
    "host",
    "env",
    "environment",
    "command",
    "entrypoint",
    "volume",
    "network",
    "cpu",
    "memory",
    "privileged",
    "cap_add",
    "restart",
    "expose",
}

VALIDATION_TERMS = {
    "validate",
    "validation",
    "assert",
    "require",
    "check",
    "guard",
    "verify",
    "ensure",
    "throw",
    "raise",
}

CRITICAL_INFRA_FILES = {
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env",
    "nginx.conf",
    "terraform.tf",
    "main.tf",
    "helm/",
    "k8s/",
    "deployment.yaml",
    "deployment.yml",
    "service.yaml",
    "service.yml",
    "ingress.yaml",
    "ingress.yml",
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret|password|passwd|client[_-]?secret)\s*[:=]\s*['\"]?[^\s'\"]+"),
    re.compile(r"(?i)bearer\s+[a-z0-9._\-+/]+=*"),
    re.compile(r"(?i)gh[pousr]_[a-zA-Z0-9]{16,}"),
    re.compile(r"(?i)-----begin\s+(rsa\s+)?private\s+key-----"),
]


@dataclass
class AnalyzerFinding:
    score_delta: int
    reason: str
    recommendation: str
    rule_id: str = "CODE_RISK_RULE"
    category: str = "code_risk"
    subcategory: str = "general"
    policy_action: str = "REVIEW_REQUIRED"
    severity: str = "MEDIUM"
    confidence: float = 0.85
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        file_path = self.metadata.get("file", "unknown")
        line_val = self.metadata.get("line")
        matched_str = line_val if isinstance(line_val, str) else self.reason

        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "rule_id": self.rule_id,
            "severity": self.severity.upper(),
            "policy_action": self.policy_action,
            "confidence": self.confidence,
            "evidence": {
                "file": file_path,
                "line": self.metadata.get("line_number"),
                "matched": str(matched_str)[:200],
            },
            "description": self.reason,
            "recommendation": self.recommendation,
            "reason": self.reason,
            "weight": self.score_delta,
            "metadata": self.metadata,
        }


class BaseAnalyzer(ABC):
    name: str = "base"

    @abstractmethod
    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        raise NotImplementedError


class SecuritySensitiveAnalyzer(BaseAnalyzer):
    name = "security-sensitive"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        for file_name, line in _iter_changed_lines(context):
            normalized = line.lower()
            if not any(term in normalized for term in SECURITY_TERMS):
                continue
            return AnalyzerFinding(
                score_delta=12,
                reason="Security-sensitive terms were introduced or modified in code diff.",
                recommendation="Review the affected code paths for access control, encryption, and privilege handling.",
                rule_id="CODE_SECURITY_SENSITIVE",
                category="authentication",
                subcategory="access_control",
                policy_action="REVIEW_REQUIRED",
                severity="MEDIUM",
                confidence=0.85,
                metadata={"file": file_name, "line": line.strip()},
            )
        return None


class AuthenticationAnalyzer(BaseAnalyzer):
    name = "authentication"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        for file_name, line in _iter_changed_lines(context):
            normalized = line.lower()
            if not any(term in normalized for term in AUTH_TERMS):
                continue
            if file_name.endswith((".py", ".js", ".ts", ".go", ".java", ".rb")):
                return AnalyzerFinding(
                    score_delta=15,
                    reason="Code diff touches authentication-related logic (sessions, credentials, roles).",
                    recommendation="Validate authentication flows, role changes, and session handling with focused tests.",
                    rule_id="CODE_AUTH_MODIFIED",
                    category="authentication",
                    subcategory="auth_logic",
                    policy_action="REVIEW_REQUIRED",
                    severity="HIGH",
                    confidence=0.90,
                    metadata={"file": file_name, "line": line.strip()},
                )
        return None


class DatabaseMigrationAnalyzer(BaseAnalyzer):
    name = "database-migration"

    _SQL_TOKENS = ("alter table", "create table", "drop column", "drop table", "create index")
    _FILE_TOKENS = ("migration", "migrations", ".sql")

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        changed_files = context.get("changed_files", [])
        for file_entry in changed_files:
            file_name = str(file_entry.get("filename", "")).lower()
            patch = str(file_entry.get("patch", ""))
            if any(token in file_name for token in self._FILE_TOKENS):
                return AnalyzerFinding(
                    score_delta=15,
                    reason="Database migration or schema definition file modified.",
                    recommendation="Review the migration for backward compatibility and transactional safety.",
                    rule_id="CODE_DB_MIGRATION",
                    category="dependencies",
                    subcategory="database_schema",
                    policy_action="REVIEW_REQUIRED",
                    severity="HIGH",
                    confidence=0.95,
                    metadata={"file": file_name},
                )
            if any(token in patch.lower() for token in self._SQL_TOKENS):
                return AnalyzerFinding(
                    score_delta=15,
                    reason="The patch includes schema-altering DDL SQL statements.",
                    recommendation="Validate the migration plan, rollback path, and data preservation strategy.",
                    rule_id="CODE_DDL_SQL",
                    category="dependencies",
                    subcategory="database_schema",
                    policy_action="REVIEW_REQUIRED",
                    severity="HIGH",
                    confidence=0.95,
                    metadata={"file": file_name},
                )
        return None


class DangerousConfigurationAnalyzer(BaseAnalyzer):
    name = "dangerous-configuration"

    _INFRA_FILE_TOKENS = ("docker", ".env", "k8s", "helm", "terraform", "nginx", "compose", "deployment", "ingress", "service")

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        for file_name, line in _iter_changed_lines(context):
            normalized = line.lower()
            normalized_name = file_name.lower()
            if any(token in normalized_name for token in self._INFRA_FILE_TOKENS):
                if any(token in normalized for token in CONFIG_TERMS):
                    return AnalyzerFinding(
                        score_delta=13,
                        reason="Infrastructure configuration changed in a security-sensitive way.",
                        recommendation="Review configuration changes for production blast radius and secrets.",
                        rule_id="CODE_INFRA_CONFIG_CHANGED",
                        category="docker",
                        subcategory="config",
                        policy_action="REVIEW_REQUIRED",
                        severity="MEDIUM",
                        confidence=0.85,
                        metadata={"file": file_name, "line": line.strip()},
                    )
        return None


class LargeChangeAnalyzer(BaseAnalyzer):
    name = "large-change"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        file_count = int(context.get("changed_file_count") or 0)
        line_count = int(context.get("changed_line_count") or 0)
        if file_count >= 10 or line_count >= 300:
            return AnalyzerFinding(
                score_delta=10,
                reason="The change is broad and touches many files or lines.",
                recommendation="Break the change into smaller PRs for safer auditability.",
                rule_id="CODE_LARGE_CHANGE",
                category="code_risk",
                subcategory="blast_radius",
                policy_action="REVIEW_REQUIRED",
                severity="MEDIUM",
                confidence=0.80,
                metadata={"files": file_count, "lines": line_count},
            )
        return None


class DeletedValidationAnalyzer(BaseAnalyzer):
    name = "deleted-validation"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        for file_name, line in _iter_changed_lines(context):
            if not line.startswith("-"):
                continue
            normalized = line.lower()
            if any(term in normalized for term in VALIDATION_TERMS) or "auth" in normalized or "session" in normalized or "guard" in normalized:
                return AnalyzerFinding(
                    score_delta=18,
                    reason="Input validation, assertion, or guard check was deleted in patch.",
                    recommendation="Verify that deleted validation code was superseded by equivalent safety guards.",
                    rule_id="REMOVED_AUTH_MIDDLEWARE",
                    category="authentication",
                    subcategory="middleware_removal",
                    policy_action="REVIEW_REQUIRED",
                    severity="HIGH",
                    confidence=0.92,
                    metadata={"file": file_name, "line": line.strip()},
                )
        return None


class SecretCredentialAnalyzer(BaseAnalyzer):
    name = "secrets"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        for file_name, line in _iter_changed_lines(context):
            if line.startswith("-"):
                continue
            for pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    return AnalyzerFinding(
                        score_delta=30,
                        reason="Potential secret or hardcoded credential detected in patch.",
                        recommendation="Remove hardcoded secret material and store in a secret manager.",
                        rule_id="HARDCODED_SECRET",
                        category="secrets",
                        subcategory="api_key",
                        policy_action="BLOCK",
                        severity="CRITICAL",
                        confidence=0.98,
                        metadata={"file": file_name, "line": line.strip()},
                    )
        return None


class CriticalInfrastructureAnalyzer(BaseAnalyzer):
    name = "critical-infrastructure"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        for file_entry in context.get("changed_files", []):
            filename = str(file_entry.get("filename", "")).lower()
            patch = str(file_entry.get("patch", ""))
            if "dockerfile" in filename and ("user root" in patch.lower() or "user 0" in patch.lower()):
                return AnalyzerFinding(
                    score_delta=20,
                    reason="Dockerfile diff configures container to run as root user.",
                    recommendation="Use a dedicated non-root USER instruction.",
                    rule_id="DOCKER_ROOT_USER",
                    category="docker",
                    subcategory="privilege",
                    policy_action="REVIEW_REQUIRED",
                    severity="HIGH",
                    confidence=0.98,
                    metadata={"file": filename},
                )
        return None


def _get_searchable_text(context: dict[str, Any]) -> str:
    """Assemble searchable text from patches, PR metadata, and commit message.
    
    Priority order:
    1. Patch text (most reliable)
    2. PR title and body
    3. Commit message
    4. File names
    
    Returns combined text for analyzers to search when patches are unavailable.
    """
    parts = []
    
    # Add patch text if available
    for file_entry in context.get("changed_files", []):
        patch = str(file_entry.get("patch", ""))
        if patch:
            parts.append(patch)
        filename = str(file_entry.get("filename", ""))
        if filename:
            parts.append(filename)
    
    # Add PR metadata
    pr = context.get("pull_request") or {}
    if pr.get("title"):
        parts.append(str(pr.get("title")))
    if pr.get("body"):
        parts.append(str(pr.get("body")))
    
    # Add commit message
    head_commit = context.get("head_commit") or {}
    if head_commit.get("message"):
        parts.append(str(head_commit.get("message")))
    
    # Combine all text
    combined = "\n".join(parts)
    return combined.lower()


def _iter_changed_lines(context: dict[str, Any]):
    for file_entry in context.get("changed_files", []):
        file_name = str(file_entry.get("filename", ""))
        patch = str(file_entry.get("patch", ""))
        for line in patch.splitlines():
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                yield file_name, line


def fetch_pull_request_files(pr_url: str) -> list[dict[str, Any]]:
    if not GITHUB_TOKEN or not pr_url:
        return []

    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    files_url = pr_url.rstrip("/") + "/files"
    try:
        response = requests.get(files_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        return response.json()
    except requests.RequestException:
        return []


def build_analysis_context(payload: dict[str, Any]) -> dict[str, Any]:
    pr = payload.get("pull_request") or {}
    head_commit = payload.get("head_commit") or {}
    repository = payload.get("repository") or {}
    files: list[dict[str, Any]] = []

    if isinstance(payload.get("changed_files"), list):
        files.extend(payload.get("changed_files", []))

    if isinstance(payload.get("files"), list):
        files.extend(payload.get("files", []))
    if isinstance(payload.get("diffs"), list):
        files.extend(payload.get("diffs", []))

    if isinstance(pr, dict) and pr.get("url"):
        fetched_files = fetch_pull_request_files(pr.get("url", ""))
        if fetched_files:
            files = fetched_files

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

    # Preserve actual patch content so analyzers can inspect it.
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
        "repository": repository,
        "changed_line_count": changed_line_count,
        "patch_text": patch_text,
        "text": " ".join(
            [
                str(pr.get("title", "")),
                str(pr.get("body", "")),
                str(head_commit.get("message", "")),
                str(payload.get("commit_message", "")),
            ]
        ).lower(),
    }


def analyze_code_risk(payload: dict[str, Any]) -> dict[str, Any]:
    context = build_analysis_context(payload)
    files = context.get("changed_files", [])
    findings: list[AnalyzerFinding] = []

    # Detect documentation-only pull requests
    all_filenames = [str(f.get("filename", "")).lower() for f in files if f.get("filename")]
    is_docs_only = len(all_filenames) > 0 and all(
        fn.endswith((".md", ".txt", ".rst")) or fn.startswith("docs/") or "readme" in fn or "license" in fn
        for fn in all_filenames
    )

    if is_docs_only:
        deterministic_dicts: list[dict[str, Any]] = []
        return {
            "score": 5,
            "severity": "low",
            "confidence": 0.95,
            "reasons": ["Documentation-only pull request detected."],
            "recommendations": ["No code security review required for documentation changes."],
            "deterministic_findings": deterministic_dicts,
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
            },
        }

    for analyzer in (
        SecuritySensitiveAnalyzer(),
        AuthenticationAnalyzer(),
        DatabaseMigrationAnalyzer(),
        DangerousConfigurationAnalyzer(),
        LargeChangeAnalyzer(),
        DeletedValidationAnalyzer(),
        SecretCredentialAnalyzer(),
        CriticalInfrastructureAnalyzer(),
    ):
        finding = analyzer.analyze(context)
        if finding:
            findings.append(finding)

    # --- Adaptive Scoring ---
    if findings:
        score = min(100, 10 + sum(f.score_delta for f in findings))
    else:
        score = min(25, 5 + min(15, int(context.get("changed_file_count") or 0) * 2))

    score = int(max(0, min(100, score)))

    if score >= 80 or any(f.severity.upper() == "CRITICAL" for f in findings):
        severity = "critical"
    elif score >= 55 or any(f.severity.upper() == "HIGH" for f in findings):
        severity = "high"
    elif score >= 30 or any(f.severity.upper() == "MEDIUM" for f in findings):
        severity = "medium"
    else:
        severity = "low"

    confidence = 0.85 if context.get("patch_text") else 0.50

    reasons = [finding.reason for finding in findings]
    recommendations = [finding.recommendation for finding in findings]
    deterministic_dicts = [f.to_dict() for f in findings]

    return {
        "score": score,
        "severity": severity,
        "confidence": confidence,
        "reasons": reasons,
        "recommendations": recommendations,
        "deterministic_findings": deterministic_dicts,
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
        },
    }

