"""
analysis/detectors/python.py — Deterministic security detector for Python diffs.

Scans only lines that start with '+' (newly introduced code).
Never inspects '-' lines (removed code is not a new risk).
Returns a list of SecurityFinding objects — no prose, no recommendations.
"""
from __future__ import annotations

import re
from typing import List

from analysis.models import DiffFile, SecurityFinding

# ---------------------------------------------------------------------------
# Compiled regex patterns — all operate on individual diff lines
# ---------------------------------------------------------------------------

# injection / dangerous execution
_SHELL_TRUE       = re.compile(r"shell\s*=\s*True")
_EVAL             = re.compile(r"\beval\s*\(")
_EXEC             = re.compile(r"\bexec\s*\(")
_OS_SYSTEM        = re.compile(r"\bos\.system\s*\(")
_OS_POPEN         = re.compile(r"\bos\.popen\s*\(")

# deserialization
_PICKLE_LOADS     = re.compile(r"\bpickle\.loads?\s*\(")
_YAML_LOAD_UNSAFE = re.compile(r"\byaml\.load\s*\((?![^)]*Loader\s*=)")

# hardcoded secrets (added lines only)
_HARDCODED_CRED   = re.compile(
    r"""(?ix)
    (?:password|passwd|secret|api[_\-]?key|access[_\-]?token|
       client[_\-]?secret|private[_\-]?key|auth[_\-]?token)
    \s*[:=]\s*['"][^'"]{4,}['"]
    """
)
_JWT_SECRET       = re.compile(
    r"""(?ix)
    (?:jwt|secret[_\-]?key|signing[_\-]?key)\s*[:=]\s*['"][^'"]{4,}['"]
    """
)

# SQL injection
_SQL_FSTRING      = re.compile(r'f["\'].*\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER)\b.*\{', re.IGNORECASE)
_SQL_CONCAT       = re.compile(r'(?:SELECT|INSERT|UPDATE|DELETE)\b.*["\']?\s*\+', re.IGNORECASE)

# TLS / network
_NO_VERIFY        = re.compile(r"verify\s*=\s*False")

# crypto
_WEAK_HASH        = re.compile(r"\b(?:md5|sha1)\s*\(")   # flag only in security context

# file / path
_PATH_TRAVERSAL   = re.compile(r"open\s*\([^)]*\.\./")
_TEMPFILE_MKTEMP  = re.compile(r"\btempfile\.mktemp\s*\(")

# subprocess without shell but with dangerous patterns
_SUBPROCESS_POPEN = re.compile(r"\bsubprocess\.Popen\s*\(")


def detect(diff_file: DiffFile) -> List[SecurityFinding]:
    """
    Run all Python detectors against *diff_file*.
    Returns one SecurityFinding per matched pattern instance.
    """
    findings: List[SecurityFinding] = []

    for line_number, line in _iter_added_lines(diff_file.patch):
        stripped = line[1:].strip()   # drop the leading '+' character
        _check_line(diff_file.filename, line_number, stripped, findings)

    return findings


def _iter_added_lines(patch: str):
    """Yield (line_number, raw_line) for every '+' line in the patch."""
    line_no = 0
    for raw in patch.splitlines():
        if raw.startswith("@@"):
            # Parse hunk header to get starting line number
            m = re.search(r"\+(\d+)", raw)
            if m:
                line_no = int(m.group(1)) - 1
            continue
        line_no += 1
        if raw.startswith("+") and not raw.startswith("+++"):
            yield line_no, raw


def _finding(rule_id, severity, category, filename, line_number, matched):
    return SecurityFinding(
        rule_id=rule_id,
        detector="python",
        severity=severity,
        category=category,
        file=filename,
        line_number=line_number,
        matched_text=matched[:200],
        confidence=0.92,
    )


def _check_line(filename: str, line_number: int, line: str, findings: List[SecurityFinding]) -> None:
    """Check one source line against all patterns."""

    if _SHELL_TRUE.search(line):
        findings.append(_finding(
            "PY_SHELL_TRUE", "HIGH", "injection/command_injection",
            filename, line_number, line,
        ))

    if _EVAL.search(line):
        findings.append(_finding(
            "PY_EVAL", "HIGH", "injection/code_execution",
            filename, line_number, line,
        ))

    if _EXEC.search(line):
        findings.append(_finding(
            "PY_EXEC", "HIGH", "injection/code_execution",
            filename, line_number, line,
        ))

    if _OS_SYSTEM.search(line) or _OS_POPEN.search(line):
        findings.append(_finding(
            "PY_OS_SYSTEM", "HIGH", "injection/command_injection",
            filename, line_number, line,
        ))

    if _PICKLE_LOADS.search(line):
        findings.append(_finding(
            "PY_PICKLE", "HIGH", "deserialization/unsafe_pickle",
            filename, line_number, line,
        ))

    if _YAML_LOAD_UNSAFE.search(line):
        findings.append(_finding(
            "PY_YAML_LOAD_UNSAFE", "MEDIUM", "deserialization/unsafe_yaml",
            filename, line_number, line,
        ))

    if _HARDCODED_CRED.search(line):
        findings.append(_finding(
            "PY_HARDCODED_CRED", "CRITICAL", "secrets/hardcoded_credential",
            filename, line_number, line,
        ))

    if _JWT_SECRET.search(line):
        findings.append(_finding(
            "PY_JWT_SECRET", "CRITICAL", "secrets/jwt_secret",
            filename, line_number, line,
        ))

    if _SQL_FSTRING.search(line) or _SQL_CONCAT.search(line):
        findings.append(_finding(
            "PY_SQL_INJECTION", "HIGH", "injection/sql_injection",
            filename, line_number, line,
        ))

    if _NO_VERIFY.search(line):
        findings.append(_finding(
            "PY_REQUESTS_NO_VERIFY", "MEDIUM", "tls/certificate_verification_disabled",
            filename, line_number, line,
        ))

    if _WEAK_HASH.search(line):
        findings.append(_finding(
            "PY_WEAK_CRYPTO", "MEDIUM", "crypto/weak_hash",
            filename, line_number, line,
        ))

    if _PATH_TRAVERSAL.search(line):
        findings.append(_finding(
            "PY_PATH_TRAVERSAL", "HIGH", "injection/path_traversal",
            filename, line_number, line,
        ))

    if _TEMPFILE_MKTEMP.search(line):
        findings.append(_finding(
            "PY_TEMPFILE_INSECURE", "LOW", "file/insecure_tempfile",
            filename, line_number, line,
        ))
