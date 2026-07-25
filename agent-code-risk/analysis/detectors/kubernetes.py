"""
analysis/detectors/kubernetes.py — Deterministic security detector for Kubernetes manifests.

Also used for Helm chart templates (same YAML format, same security risks).
Inspects added lines for privilege, host namespace, and resource limit issues.
No LLM, no external dependencies.
"""
from __future__ import annotations

import re
from typing import List

from analysis.models import DiffFile, SecurityFinding

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Host namespace flags
_HOST_NETWORK     = re.compile(r"\bhostNetwork\s*:\s*true\b", re.IGNORECASE)
_HOST_PID         = re.compile(r"\bhostPID\s*:\s*true\b", re.IGNORECASE)
_HOST_IPC         = re.compile(r"\bhostIPC\s*:\s*true\b", re.IGNORECASE)

# Privileged containers
_PRIVILEGED       = re.compile(r"\bprivileged\s*:\s*true\b", re.IGNORECASE)
_ALLOW_PRIV_ESC   = re.compile(r"\ballowPrivilegeEscalation\s*:\s*true\b", re.IGNORECASE)

# Running as root
_RUN_AS_ROOT      = re.compile(r"\brunAsUser\s*:\s*0\b")
_RUN_AS_NON_ROOT_FALSE = re.compile(r"\brunAsNonRoot\s*:\s*false\b", re.IGNORECASE)

# Host path mounts (volume host path including docker sock)
_HOST_PATH        = re.compile(r"\bhostPath\s*:", re.IGNORECASE)
_DOCKER_SOCK      = re.compile(r"docker\.sock")

# Missing resource limits (structural — checked on full added block)
_RESOURCES_BLOCK  = re.compile(r"\bresources\s*:", re.IGNORECASE)
_LIMITS_BLOCK     = re.compile(r"\blimits\s*:", re.IGNORECASE)

# Dangerous capabilities
_CAP_ADD_ALL      = re.compile(r"\bcapabilities\b.*\badd\b.*\bALL\b", re.IGNORECASE | re.DOTALL)
_NET_ADMIN_CAP    = re.compile(r"\bNET_ADMIN\b")
_SYS_ADMIN_CAP    = re.compile(r"\bSYS_ADMIN\b")

# Secrets stored as plain env vars
_SECRET_AS_ENV    = re.compile(
    r"\benv\b.*\bname\s*:\s*\S*(?:PASSWORD|SECRET|TOKEN|KEY)\S*.*\bvalue\s*:\s*\S",
    re.IGNORECASE | re.DOTALL,
)

# Image using :latest tag
_IMAGE_LATEST     = re.compile(r"\bimage\s*:\s*[^\s:]+:latest\b", re.IGNORECASE)

# default namespace (less severe — awareness only)
_DEFAULT_NS       = re.compile(r"\bnamespace\s*:\s*default\b", re.IGNORECASE)


def detect(diff_file: DiffFile) -> List[SecurityFinding]:
    """Run all Kubernetes/Helm detectors against *diff_file*."""
    findings: List[SecurityFinding] = []
    patch = diff_file.patch
    filename = diff_file.filename

    # Structural check — was a resources block added without limits?
    added_block = "\n".join(
        line[1:] for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    if _RESOURCES_BLOCK.search(added_block) and not _LIMITS_BLOCK.search(added_block):
        findings.append(_finding(
            "K8S_NO_RESOURCE_LIMITS", "MEDIUM", "kubernetes/missing_limits",
            filename, None, "resources: block added without limits: — containers may consume unbounded CPU/memory",
        ))

    for line_number, line in _iter_added_lines(patch):
        stripped = line[1:].strip()
        _check_line(filename, line_number, stripped, findings)

    return findings


def _check_line(filename: str, line_number: int, line: str, findings: List[SecurityFinding]) -> None:
    if _HOST_NETWORK.search(line):
        findings.append(_finding(
            "K8S_HOST_NETWORK", "HIGH", "kubernetes/host_namespace",
            filename, line_number, line,
        ))

    if _HOST_PID.search(line):
        findings.append(_finding(
            "K8S_HOST_PID", "HIGH", "kubernetes/host_namespace",
            filename, line_number, line,
        ))

    if _HOST_IPC.search(line):
        findings.append(_finding(
            "K8S_HOST_IPC", "HIGH", "kubernetes/host_namespace",
            filename, line_number, line,
        ))

    if _PRIVILEGED.search(line):
        findings.append(_finding(
            "K8S_PRIVILEGED_CONTAINER", "CRITICAL", "kubernetes/privilege_escalation",
            filename, line_number, line,
        ))

    if _ALLOW_PRIV_ESC.search(line):
        findings.append(_finding(
            "K8S_ALLOW_PRIVILEGE_ESCALATION", "HIGH", "kubernetes/privilege_escalation",
            filename, line_number, line,
        ))

    if _RUN_AS_ROOT.search(line):
        findings.append(_finding(
            "K8S_RUN_AS_ROOT", "HIGH", "kubernetes/root_container",
            filename, line_number, line,
        ))

    if _RUN_AS_NON_ROOT_FALSE.search(line):
        findings.append(_finding(
            "K8S_RUN_AS_NON_ROOT_FALSE", "HIGH", "kubernetes/root_container",
            filename, line_number, line,
        ))

    if _HOST_PATH.search(line):
        findings.append(_finding(
            "K8S_HOST_PATH_MOUNT", "HIGH", "kubernetes/host_path_mount",
            filename, line_number, line,
        ))

    if _DOCKER_SOCK.search(line):
        findings.append(_finding(
            "K8S_DOCKER_SOCK", "CRITICAL", "kubernetes/docker_socket",
            filename, line_number, line,
        ))

    if _NET_ADMIN_CAP.search(line):
        findings.append(_finding(
            "K8S_CAP_NET_ADMIN", "HIGH", "kubernetes/dangerous_capability",
            filename, line_number, line,
        ))

    if _SYS_ADMIN_CAP.search(line):
        findings.append(_finding(
            "K8S_CAP_SYS_ADMIN", "CRITICAL", "kubernetes/dangerous_capability",
            filename, line_number, line,
        ))

    if _IMAGE_LATEST.search(line):
        findings.append(_finding(
            "K8S_IMAGE_LATEST_TAG", "MEDIUM", "kubernetes/unpinned_image",
            filename, line_number, line,
        ))

    if _DEFAULT_NS.search(line):
        findings.append(_finding(
            "K8S_DEFAULT_NAMESPACE", "INFO", "kubernetes/default_namespace",
            filename, line_number, line,
        ))


def _finding(rule_id, severity, category, filename, line_number, matched):
    return SecurityFinding(
        rule_id=rule_id,
        detector="kubernetes",
        severity=severity,
        category=category,
        file=filename,
        line_number=line_number,
        matched_text=matched[:200],
        confidence=0.92,
    )


def _iter_added_lines(patch: str):
    line_no = 0
    for raw in patch.splitlines():
        if raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            if m:
                line_no = int(m.group(1)) - 1
            continue
        line_no += 1
        if raw.startswith("+") and not raw.startswith("+++"):
            yield line_no, raw
