from __future__ import annotations

from .base import TextAnalyzer, rule


class GitHubActionsAnalyzer(TextAnalyzer):
    name = "github_actions"

    rules = (
        rule(r"\buses\s*:\s*[^@\s]+/[^@\s]+@(main|master|latest)\b|\bunpinned\s+actions\b", "high", "GitHub Actions workflow uses an unpinned action.", "Pin actions to full commit SHAs."),
        rule(r"\bworkflow_dispatch\b", "low", "GitHub Actions workflow allows manual dispatch.", "Protect manual deployments with branch protections and environment approvals."),
        rule(r"\becho\s+\$(secret|aws_secret_access_key|github_token)\b|\bprints?\s+secrets?\b", "critical", "GitHub Actions workflow prints secrets.", "Never echo secrets in workflow logs; use masked secrets and scoped credentials."),
        rule(r"\bcurl\b[^\n|]*\|\s*(?:sh|bash)\b", "critical", "GitHub Actions workflow executes curl piped to shell.", "Pin and verify downloaded scripts before execution."),
        rule(r"\bwget\b[^\n|]*\|\s*(?:sh|bash)\b", "critical", "GitHub Actions workflow executes wget piped to shell.", "Pin and verify downloaded scripts before execution."),
    )
