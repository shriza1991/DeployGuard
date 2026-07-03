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
    confidence: int = 60
    metadata: dict[str, Any] = field(default_factory=dict)


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
                reason="Security-sensitive terms were introduced or modified in the patch.",
                recommendation="Review the affected code paths for access control, encryption, and privilege handling.",
                confidence=80,
                metadata={"file": file_name, "line": line.strip()},
            )
        return None


class AuthenticationAnalyzer(BaseAnalyzer):
    name = "authentication"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        # First, check patches for auth-related changes
        for file_name, line in _iter_changed_lines(context):
            normalized = line.lower()
            if not any(term in normalized for term in AUTH_TERMS):
                continue
            if file_name.endswith((".py", ".js", ".ts", ".go", ".java", ".rb")):
                return AnalyzerFinding(
                    score_delta=14,
                    reason="The diff touches authentication-related logic such as access control, sessions, or credentials.",
                    recommendation="Validate authentication flows, role changes, and session handling with focused tests.",
                    confidence=85,
                    metadata={"file": file_name, "line": line.strip()},
                )
        
        # Fallback: check searchable text (PR title, body, commit message) for removed authentication
        searchable_text = _get_searchable_text(context)
        if any(pattern in searchable_text for pattern in [
            "removed auth",
            "removed authentication", 
            "removed login",
            "remove auth",
            "remove authentication",
            "remove login",
            "disabled auth",
            "disable authentication",
        ]):
            return AnalyzerFinding(
                score_delta=14,
                reason="Authentication logic appears to have been removed or disabled in this change.",
                recommendation="Verify that authentication removal is intentional and that alternative security measures are in place.",
                confidence=80,
                metadata={"detection_method": "metadata_text"},
            )
        
        return None


class DatabaseMigrationAnalyzer(BaseAnalyzer):
    name = "database-migration"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        changed_files = context.get("changed_files", [])
        for file_entry in changed_files:
            file_name = str(file_entry.get("filename", "")).lower()
            patch = str(file_entry.get("patch", ""))
            if any(token in file_name for token in ("migration", "migrations", ".sql")):
                return AnalyzerFinding(
                    score_delta=15,
                    reason="Database migration or schema changes were detected.",
                    recommendation="Review the migration for backward compatibility and transactional safety.",
                    confidence=90,
                    metadata={"file": file_name},
                )
            if any(token in patch.lower() for token in ("alter table", "create table", "drop column", "drop table", "create index")):
                return AnalyzerFinding(
                    score_delta=15,
                    reason="The patch includes schema-altering SQL statements.",
                    recommendation="Validate the migration plan, rollback path, and data preservation strategy.",
                    confidence=90,
                    metadata={"file": file_name},
                )
        return None


class DangerousConfigurationAnalyzer(BaseAnalyzer):
    name = "dangerous-configuration"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        for file_name, line in _iter_changed_lines(context):
            normalized = line.lower()
            normalized_name = file_name.lower()
            if any(token in normalized_name for token in ("docker", ".env", "k8s", "helm", "terraform", "nginx", "compose", "deployment", "ingress", "service")):
                if any(token in normalized for token in CONFIG_TERMS):
                    return AnalyzerFinding(
                        score_delta=13,
                        reason="Infrastructure or environment configuration changed in a potentially sensitive way.",
                        recommendation="Review configuration changes for production blast radius, secrets, and compatibility.",
                        confidence=80,
                        metadata={"file": file_name, "line": line.strip()},
                    )
        return None


class LargeChangeAnalyzer(BaseAnalyzer):
    name = "large-change"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        file_count = int(context.get("changed_file_count") or 0)
        line_count = int(context.get("changed_line_count") or 0)
        if file_count >= 8 or line_count >= 250:
            return AnalyzerFinding(
                score_delta=12,
                reason="The change is broad and touches many files or a large number of lines.",
                recommendation="Break the change into smaller PRs or add targeted review coverage.",
                confidence=70,
                metadata={"files": file_count, "lines": line_count},
            )
        return None


class DeletedValidationAnalyzer(BaseAnalyzer):
    name = "deleted-validation"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        for file_entry in context.get("changed_files", []):
            patch = str(file_entry.get("patch", ""))
            for line in patch.splitlines():
                if not line.startswith("-"):
                    continue
                normalized = line[1:].strip().lower()
                if any(token in normalized for token in VALIDATION_TERMS):
                    return AnalyzerFinding(
                        score_delta=14,
                        reason="Validation or guard logic appears to have been removed.",
                        recommendation="Restore or replace the removed validation logic and add regression tests.",
                        confidence=85,
                        metadata={"file": file_entry.get("filename"), "line": line.strip()},
                    )
        return None


class SecretCredentialAnalyzer(BaseAnalyzer):
    name = "secrets"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        for file_entry in context.get("changed_files", []):
            patch = str(file_entry.get("patch", ""))
            for line in patch.splitlines():
                if not line.startswith("+"):
                    continue
                content = line[1:].strip()
                if any(pattern.search(content) for pattern in SECRET_PATTERNS):
                    return AnalyzerFinding(
                        score_delta=18,
                        reason="The patch adds credential-like values or secret management material.",
                        recommendation="Rotate any exposed credentials and move secrets to a secure secret store.",
                        confidence=95,
                        metadata={"file": file_entry.get("filename"), "line": content},
                    )
        return None


class CriticalInfrastructureAnalyzer(BaseAnalyzer):
    name = "critical-infrastructure"

    def analyze(self, context: dict[str, Any]) -> AnalyzerFinding | None:
        for file_entry in context.get("changed_files", []):
            file_name = str(file_entry.get("filename", "")).lower()
            if any(token in file_name for token in CRITICAL_INFRA_FILES):
                return AnalyzerFinding(
                    score_delta=12,
                    reason="Critical infrastructure or deployment files were modified.",
                    recommendation="Have the change reviewed by an operations or platform owner before shipping.",
                    confidence=80,
                    metadata={"file": file_name},
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
                yield file_name, line[1:].strip()


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
    files: list[dict[str, Any]] = []

    if isinstance(payload.get("files"), list):
        files.extend(payload.get("files", []))
    if isinstance(payload.get("diffs"), list):
        files.extend(payload.get("diffs", []))

    if isinstance(pr, dict) and pr.get("url"):
        fetched_files = fetch_pull_request_files(pr.get("url", ""))
        if fetched_files:
            files = fetched_files

    if isinstance(payload.get("diff"), str) and payload.get("diff"):
        files.append({"filename": payload.get("filename", "<diff>"), "patch": payload.get("diff")})

    payload_changed_files = int(
        payload.get("changed_files")
        or pr.get("changed_files")
        or payload.get("pull_request", {}).get("changed_files")
        or 0
    )

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
    findings = []

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

    score = 10 + min(20, int(context.get("changed_file_count") or 0) * 2) + min(20, int(context.get("changed_line_count") or 0) * 0.05)
    score += sum(finding.score_delta for finding in findings)
    score = int(max(0, min(100, score)))

    severity = "low"
    if score >= 80:
        severity = "critical"
    elif score >= 60:
        severity = "high"
    elif score >= 35:
        severity = "medium"

    confidence = 60
    if findings:
        confidence = int(sum(finding.confidence for finding in findings) / len(findings))
    if context.get("patch_text"):
        confidence = min(100, confidence + 10)
    if context.get("text"):
        confidence = min(100, confidence + 5)

    reasons = [finding.reason for finding in findings]
    recommendations = [finding.recommendation for finding in findings]

    return {
        "score": score,
        "severity": severity,
        "confidence": confidence,
        "reasons": reasons,
        "recommendations": recommendations,
        "metadata": {
            "changed_files": context.get("changed_file_count"),
            "changed_lines": context.get("changed_line_count"),
            "pull_request_title": (context.get("pull_request") or {}).get("title"),
            "pull_request_body": (context.get("pull_request") or {}).get("body"),
            "commit_message": (context.get("head_commit") or {}).get("message"),
            "repository": (context.get("repository") or {}).get("name"),
            "source": "pull_request" if context.get("pull_request") else "commit",
        },
    }
