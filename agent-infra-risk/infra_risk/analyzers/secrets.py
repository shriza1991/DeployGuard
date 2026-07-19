from __future__ import annotations

from .base import TextAnalyzer, rule


class SecretAnalyzer(TextAnalyzer):
    name = "secrets"

    rules = (
        rule(
            r"\baws_secret_access_key\b|AKIA[0-9A-Z]{16}\b|\baws_access_key_id\b",
            severity="CRITICAL",
            reason="Hardcoded AWS access key ID or secret access key detected in source/config.",
            recommendation="Immediately revoke the exposed AWS credentials and use IAM roles / Workload Identity.",
            rule_id="HARDCODED_AWS_CREDENTIALS",
            category="secrets",
            subcategory="cloud_credentials",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"\bsk_live_[0-9a-zA-Z]{24,}\b|\bapi[_-]?key\s*[:=]\s*[\"'][a-zA-Z0-9_\-]{16,}|\bgh[pousr]_[a-zA-Z0-9]{16,}\b",
            severity="CRITICAL",
            reason="Hardcoded API secret token or personal access token detected.",
            recommendation="Move API keys to environment variables or secret manager and rotate exposed key.",
            rule_id="HARDCODED_SECRET",
            category="secrets",
            subcategory="api_key",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"-----begin\s+(?:rsa\s+)?private\s+key-----",
            severity="CRITICAL",
            reason="Hardcoded RSA/PEM private key material detected.",
            recommendation="Remove private key material from repository and rotate key pair immediately.",
            rule_id="HARDCODED_PRIVATE_KEY",
            category="secrets",
            subcategory="private_key",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"\bjwt\b|eyj[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+",
            severity="HIGH",
            reason="Plaintext JWT token material detected.",
            recommendation="Do not commit live JWT tokens to code or configuration files.",
            rule_id="JWT_TOKEN_EXPOSURE",
            category="secrets",
            subcategory="token",
            policy_action="REVIEW_REQUIRED",
            confidence=0.90,
        ),
    )

