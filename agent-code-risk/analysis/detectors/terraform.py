"""
analysis/detectors/terraform.py — Deterministic security detector for Terraform diffs.

Inspects added lines only ('+' prefix). Covers S3, IAM, Security Groups,
encryption, and public database exposure.
No LLM, no external dependencies.
"""
from __future__ import annotations

import re
from typing import List

from analysis.models import DiffFile, SecurityFinding

# ---------------------------------------------------------------------------
# Patterns — all match on added lines only
# ---------------------------------------------------------------------------

# S3 bucket public ACL
_S3_PUBLIC_ACL    = re.compile(r'\bacl\s*=\s*"public(?:-read|-read-write)?"', re.IGNORECASE)

# IAM wildcard actions or resources
_IAM_WILDCARD_ACTION   = re.compile(r'"Action"\s*:\s*(?:"\*"|\["?\*"?\])', re.IGNORECASE)
_IAM_WILDCARD_RESOURCE = re.compile(r'"Resource"\s*:\s*(?:"\*"|\["?\*"?\])', re.IGNORECASE)

# Security group open ingress (0.0.0.0/0 or ::/0 on ingress rule)
_SG_OPEN_INGRESS  = re.compile(r'cidr_blocks\s*=\s*\[?"0\.0\.0\.0/0"', re.IGNORECASE)
_SG_OPEN_IPV6     = re.compile(r'ipv6_cidr_blocks\s*=\s*\[?"::/0"', re.IGNORECASE)

# Unencrypted storage
_ENCRYPTED_FALSE  = re.compile(r'\bencrypted\s*=\s*false\b', re.IGNORECASE)
_STORAGE_ENCRYPTED = re.compile(r'\bstorage_encrypted\s*=\s*false\b', re.IGNORECASE)

# Publicly accessible databases
_PUBLIC_DB        = re.compile(r'\bpublicly_accessible\s*=\s*true\b', re.IGNORECASE)

# MFA delete disabled on S3
_NO_MFA_DELETE    = re.compile(r'\bmfa_delete\s*=\s*"Disabled"', re.IGNORECASE)

# Unrestricted egress (less severe but worth flagging)
_SG_OPEN_EGRESS   = re.compile(r'(?:egress|from_port\s*=\s*0.*to_port\s*=\s*0).*0\.0\.0\.0/0', re.IGNORECASE | re.DOTALL)

# Hardcoded credentials in Terraform variable defaults
_TF_HARDCODED_CRED = re.compile(
    r'(?:password|secret|token|key)\s*=\s*"[^"]{4,}"',
    re.IGNORECASE,
)


def detect(diff_file: DiffFile) -> List[SecurityFinding]:
    """Run all Terraform detectors against *diff_file*."""
    findings: List[SecurityFinding] = []
    patch = diff_file.patch
    filename = diff_file.filename

    for line_number, line in _iter_added_lines(patch):
        stripped = line[1:].strip()

        if _S3_PUBLIC_ACL.search(stripped):
            findings.append(_finding(
                "TF_S3_PUBLIC_ACL", "CRITICAL", "cloud/public_storage",
                filename, line_number, stripped,
            ))

        if _IAM_WILDCARD_ACTION.search(stripped):
            findings.append(_finding(
                "TF_IAM_WILDCARD_ACTION", "CRITICAL", "iam/wildcard_permission",
                filename, line_number, stripped,
            ))

        if _IAM_WILDCARD_RESOURCE.search(stripped):
            findings.append(_finding(
                "TF_IAM_WILDCARD_RESOURCE", "CRITICAL", "iam/wildcard_permission",
                filename, line_number, stripped,
            ))

        if _SG_OPEN_INGRESS.search(stripped):
            findings.append(_finding(
                "TF_SG_OPEN_INGRESS", "HIGH", "network/unrestricted_ingress",
                filename, line_number, stripped,
            ))

        if _SG_OPEN_IPV6.search(stripped):
            findings.append(_finding(
                "TF_SG_OPEN_INGRESS_IPV6", "HIGH", "network/unrestricted_ingress",
                filename, line_number, stripped,
            ))

        if _ENCRYPTED_FALSE.search(stripped) or _STORAGE_ENCRYPTED.search(stripped):
            findings.append(_finding(
                "TF_UNENCRYPTED_STORAGE", "HIGH", "encryption/storage_unencrypted",
                filename, line_number, stripped,
            ))

        if _PUBLIC_DB.search(stripped):
            findings.append(_finding(
                "TF_PUBLIC_DB", "CRITICAL", "cloud/public_database",
                filename, line_number, stripped,
            ))

        if _NO_MFA_DELETE.search(stripped):
            findings.append(_finding(
                "TF_NO_MFA_DELETE", "MEDIUM", "cloud/mfa_delete_disabled",
                filename, line_number, stripped,
            ))

        if _TF_HARDCODED_CRED.search(stripped):
            findings.append(_finding(
                "TF_HARDCODED_CREDENTIAL", "HIGH", "secrets/hardcoded_credential",
                filename, line_number, stripped,
            ))

    return findings


def _finding(rule_id, severity, category, filename, line_number, matched):
    return SecurityFinding(
        rule_id=rule_id,
        detector="terraform",
        severity=severity,
        category=category,
        file=filename,
        line_number=line_number,
        matched_text=matched[:200],
        confidence=0.91,
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
