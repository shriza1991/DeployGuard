"""
analysis/detectors/github_actions.py — Deterministic security detector for GitHub Actions workflows.

Scans added lines for dangerous workflow patterns: floating versions, secret echo,
expression injection, and overly broad permissions.
No LLM, no external dependencies.
"""
from __future__ import annotations

import re
from typing import List

from analysis.models import DiffFile, SecurityFinding

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Floating version pins (using branch names instead of SHAs)
_FLOATING_VERSION = re.compile(r"uses\s*:\s*\S+@(?:main|master|HEAD|v?\d+)\s*$", re.IGNORECASE)

# Debug secrets leaked
_ACTIONS_DEBUG    = re.compile(r"ACTIONS_STEP_DEBUG\s*:\s*true", re.IGNORECASE)

# Overly permissive write-all
_WRITE_ALL        = re.compile(r"permissions\s*:\s*write-all", re.IGNORECASE)

# Echoing secrets in run steps
_ECHO_SECRET      = re.compile(r"\becho\b.*\$\{\{\s*secrets\.", re.IGNORECASE)

# Using secrets directly in run: inline shell (injection risk)
_SECRET_IN_RUN    = re.compile(r"\$\{\{\s*secrets\.\w+\s*\}\}")

# GitHub context expression injection in run: block
# e.g. run: echo ${{ github.event.pull_request.title }}
_EXPR_INJECTION   = re.compile(r"\$\{\{\s*github\.event\.", re.IGNORECASE)

# Hardcoded tokens
_HARDCODED_TOKEN  = re.compile(r"(?:GITHUB_TOKEN|GH_TOKEN)\s*:\s*['\"][^'\"]{10,}['\"]", re.IGNORECASE)

# Self-hosted runners (potential supply chain risk)
_SELF_HOSTED      = re.compile(r"runs-on\s*:\s*self-hosted", re.IGNORECASE)

# Cache poisoning: using cache without hash key
_CACHE_NO_HASH    = re.compile(r"actions/cache@.*\n(?:(?!\s*key\s*:.*hashFiles).)*", re.DOTALL)

# Dangerous environment variable exposure
_ENV_EXPOSE_SECRET = re.compile(
    r"env\s*:.*\n(?:.*\n)*?\s*\S*(?:SECRET|TOKEN|PASSWORD|KEY)\S*\s*:\s*\$\{\{",
    re.IGNORECASE | re.DOTALL,
)

# workflow_dispatch trigger (allows manual triggering — flagged for awareness)
_WORKFLOW_DISPATCH = re.compile(r"workflow_dispatch\s*:", re.IGNORECASE)


def detect(diff_file: DiffFile) -> List[SecurityFinding]:
    """Run all GitHub Actions detectors against *diff_file*."""
    findings: List[SecurityFinding] = []
    patch = diff_file.patch
    filename = diff_file.filename

    for line_number, line in _iter_added_lines(patch):
        stripped = line[1:].strip()
        _check_line(filename, line_number, stripped, findings)

    return findings


def _check_line(filename: str, line_number: int, line: str, findings: List[SecurityFinding]) -> None:
    if _FLOATING_VERSION.search(line):
        findings.append(_finding(
            "GHA_FLOATING_VERSION", "MEDIUM", "supply_chain/unpinned_action",
            filename, line_number, line,
        ))

    if _ACTIONS_DEBUG.search(line):
        findings.append(_finding(
            "GHA_ACTIONS_DEBUG", "LOW", "information_disclosure/debug_enabled",
            filename, line_number, line,
        ))

    if _WRITE_ALL.search(line):
        findings.append(_finding(
            "GHA_WRITE_ALL_PERMISSIONS", "HIGH", "access_control/overly_permissive",
            filename, line_number, line,
        ))

    if _ECHO_SECRET.search(line):
        findings.append(_finding(
            "GHA_ECHO_SECRET", "CRITICAL", "secrets/secret_disclosure",
            filename, line_number, line,
        ))

    # SECRET_IN_RUN is HIGH when used in run: blocks — context matters
    if _SECRET_IN_RUN.search(line) and not _ECHO_SECRET.search(line):
        findings.append(_finding(
            "GHA_SECRET_IN_RUN", "HIGH", "secrets/secret_in_run_step",
            filename, line_number, line,
        ))

    if _EXPR_INJECTION.search(line):
        findings.append(_finding(
            "GHA_EXPRESSION_INJECTION", "HIGH", "injection/workflow_expression",
            filename, line_number, line,
        ))

    if _HARDCODED_TOKEN.search(line):
        findings.append(_finding(
            "GHA_HARDCODED_TOKEN", "CRITICAL", "secrets/hardcoded_token",
            filename, line_number, line,
        ))

    if _SELF_HOSTED.search(line):
        findings.append(_finding(
            "GHA_SELF_HOSTED_RUNNER", "MEDIUM", "supply_chain/self_hosted_runner",
            filename, line_number, line,
        ))

    if _WORKFLOW_DISPATCH.search(line):
        findings.append(_finding(
            "GHA_WORKFLOW_DISPATCH", "INFO", "access_control/manual_trigger",
            filename, line_number, line,
        ))


def _finding(rule_id, severity, category, filename, line_number, matched):
    return SecurityFinding(
        rule_id=rule_id,
        detector="github_actions",
        severity=severity,
        category=category,
        file=filename,
        line_number=line_number,
        matched_text=matched[:200],
        confidence=0.90,
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
