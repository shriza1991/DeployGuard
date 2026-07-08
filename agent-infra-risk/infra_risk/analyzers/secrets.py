from __future__ import annotations

from .base import TextAnalyzer, rule


class SecretAnalyzer(TextAnalyzer):
    name = "secrets"

    rules = (
        rule(r"\baws_access_key_id\b", "critical", "AWS credentials detected.", "Remove AWS access keys and rotate any exposed credentials."),
        rule(r"\baws_secret_access_key\b", "critical", "AWS secret access key detected.", "Remove AWS secret keys and rotate any exposed credentials."),
        rule(r"\bgcp_service_account\b|\bgoogle_application_credentials\b", "critical", "GCP service account credentials detected.", "Remove GCP credentials and use workload identity or a secret manager."),
        rule(r"\bazure_client_secret\b", "critical", "Azure client secret detected.", "Remove Azure client secrets and rotate any exposed credentials."),
        rule(r"\bkube_token\b|\bkubeconfig\b", "critical", "Kubernetes credentials detected.", "Remove Kubernetes credentials and use short-lived scoped access."),
        rule(r"\bdocker_password\b", "critical", "Docker registry password detected.", "Remove Docker passwords and rotate the exposed credential."),
        rule(r"\bprivate_key\b|\bbegin private key\b|-----begin [a-z ]*private key-----", "critical", "Private key material detected.", "Remove private keys from the deployment and rotate the key pair."),
        rule(r"\btoken\s*=", "critical", "Plaintext token detected.", "Move tokens to a secret manager and rotate exposed values."),
        rule(r"\bsecret\s*=", "critical", "Plaintext secret detected.", "Move secrets to a secret manager and rotate exposed values."),
        rule(r"\bpassword\s*=", "critical", "Plaintext password detected.", "Move passwords to a secret manager and rotate exposed values."),
        rule(r"\bapi_key\s*=", "critical", "Plaintext API key detected.", "Move API keys to a secret manager and rotate exposed values."),
        rule(r"\bbearer\s+[a-z0-9._\-+/]+=*", "critical", "Bearer token detected.", "Remove bearer tokens from code and rotate exposed credentials."),
        rule(r"\bjwt\b|eyj[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+", "high", "JWT token material detected.", "Avoid committing JWTs or token examples that can be mistaken for live credentials."),
        rule(r"\bgh[pousr]_[a-z0-9]{16,}\b|\bgithub\s+pat\b", "critical", "GitHub personal access token detected.", "Revoke the GitHub token and replace it with scoped short-lived credentials."),
    )
