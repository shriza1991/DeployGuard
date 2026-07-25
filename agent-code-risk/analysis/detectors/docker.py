"""
analysis/detectors/docker.py — Deterministic security detector for Dockerfile diffs.

Scans both the full file content (for structural checks like HEALTHCHECK) and
individual added lines (for instruction-level rules).
No LLM, no external dependencies.
"""
from __future__ import annotations

import re
from typing import List

from analysis.models import DiffFile, SecurityFinding

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# USER root / USER 0
_USER_ROOT        = re.compile(r"^\+?\s*USER\s+(?:root|0)\s*$", re.IGNORECASE | re.MULTILINE)
# FROM image:latest (no pinned digest or version)
_LATEST_TAG       = re.compile(r"^\+?\s*FROM\s+[^\s]+:latest\b", re.IGNORECASE | re.MULTILINE)
# Docker socket mount
_DOCKER_SOCK      = re.compile(r"/var/run/docker\.sock")
# --privileged flag in RUN instructions
_PRIVILEGED       = re.compile(r"--privileged")
# ADD with a remote URL (should use COPY + curl/wget instead for reproducibility)
_ADD_REMOTE       = re.compile(r"^\+?\s*ADD\s+https?://", re.IGNORECASE | re.MULTILINE)
# EXPOSE with a broad range or all-interfaces binding
_EXPOSE_ALL       = re.compile(r"^\+?\s*EXPOSE\s+(?:0\.0\.0\.0|\d+/\w+)", re.IGNORECASE | re.MULTILINE)
# Running as root via RUN su -
_RUN_SU_ROOT      = re.compile(r"^\+?\s*RUN\s+.*\bsu\s+-\b", re.IGNORECASE | re.MULTILINE)
# Secrets stored in ENV or ARG (common mistake)
_SECRET_IN_ENV    = re.compile(
    r"^\+?\s*(?:ENV|ARG)\s+\S*(?:PASSWORD|SECRET|TOKEN|KEY|PASS)\S*\s*=\s*\S+",
    re.IGNORECASE | re.MULTILINE,
)


def detect(diff_file: DiffFile) -> List[SecurityFinding]:
    """Run all Docker detectors against *diff_file*."""
    findings: List[SecurityFinding] = []
    patch = diff_file.patch
    filename = diff_file.filename

    # Reconstruct a plausible full-file view from added lines (imperfect but fast)
    full_text = "\n".join(
        line[1:] for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )

    # ── Structural checks (whole-file) ────────────────────────────────────
    if _USER_ROOT.search(patch):
        findings.append(_finding(
            "DOCKER_ROOT_USER", "HIGH", "docker/privilege_escalation",
            filename, _first_match_line(patch, _USER_ROOT),
            "USER root / USER 0 instruction detected",
        ))

    if _LATEST_TAG.search(patch):
        findings.append(_finding(
            "DOCKER_LATEST_TAG", "MEDIUM", "docker/unpinned_image",
            filename, _first_match_line(patch, _LATEST_TAG),
            "FROM image:latest — no pinned digest or version tag",
        ))

    if _DOCKER_SOCK.search(patch):
        findings.append(_finding(
            "DOCKER_SOCK_MOUNT", "CRITICAL", "docker/docker_socket",
            filename, _first_match_line(patch, _DOCKER_SOCK),
            "/var/run/docker.sock mounted — grants host Docker daemon access",
        ))

    if _PRIVILEGED.search(patch):
        findings.append(_finding(
            "DOCKER_PRIVILEGED", "CRITICAL", "docker/privileged_mode",
            filename, _first_match_line(patch, _PRIVILEGED),
            "--privileged flag grants full host capabilities",
        ))

    if _ADD_REMOTE.search(patch):
        findings.append(_finding(
            "DOCKER_ADD_REMOTE_URL", "LOW", "docker/reproducibility",
            filename, _first_match_line(patch, _ADD_REMOTE),
            "ADD with remote URL — use COPY + explicit download for reproducibility",
        ))

    if _SECRET_IN_ENV.search(patch):
        findings.append(_finding(
            "DOCKER_SECRET_IN_ENV", "HIGH", "docker/secret_exposure",
            filename, _first_match_line(patch, _SECRET_IN_ENV),
            "Secret/password stored in ENV or ARG — visible in image layers",
        ))

    if _RUN_SU_ROOT.search(patch):
        findings.append(_finding(
            "DOCKER_SU_ROOT", "HIGH", "docker/privilege_escalation",
            filename, _first_match_line(patch, _RUN_SU_ROOT),
            "RUN su - command detected — potential privilege escalation",
        ))

    # HEALTHCHECK absence: check only if the diff adds a new FROM (new stage)
    # or is the only Dockerfile in the diff and no HEALTHCHECK is present.
    if _LATEST_TAG.search(patch) or "FROM" in full_text.upper():
        if "HEALTHCHECK" not in full_text.upper() and "HEALTHCHECK" not in patch.upper():
            findings.append(_finding(
                "DOCKER_NO_HEALTHCHECK", "LOW", "docker/missing_healthcheck",
                filename, None,
                "No HEALTHCHECK instruction — orchestrators cannot detect unhealthy containers",
            ))

    return findings


def _finding(rule_id, severity, category, filename, line_number, matched):
    return SecurityFinding(
        rule_id=rule_id,
        detector="docker",
        severity=severity,
        category=category,
        file=filename,
        line_number=line_number,
        matched_text=matched[:200],
        confidence=0.93,
    )


def _first_match_line(patch: str, pattern: re.Pattern) -> int | None:
    """Return the approximate line number of the first match in the patch."""
    line_no = 0
    for line in patch.splitlines():
        if line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            if m:
                line_no = int(m.group(1)) - 1
        line_no += 1
        if pattern.search(line):
            return line_no
    return None
