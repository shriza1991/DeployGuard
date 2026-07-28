from __future__ import annotations

from .base import Finding, RichRule, dedupe_findings, rich_rule, rule
from .docker import DockerAnalyzer
from .docker_compose import DockerComposeAnalyzer
from .github_actions import GitHubActionsAnalyzer
from .kubernetes import KubernetesAnalyzer
from .secrets import SecretAnalyzer
from .terraform import TerraformAnalyzer


# Ordered list of analyzers dispatched by the InfraFileRouter.
# SecretAnalyzer is intentionally excluded here — the router runs it
# separately across all infra files as a cross-cutting concern.
ANALYZERS = (
    DockerAnalyzer(),
    KubernetesAnalyzer(),
    TerraformAnalyzer(),
    GitHubActionsAnalyzer(),
    DockerComposeAnalyzer(),
    SecretAnalyzer(),
)

__all__ = [
    "ANALYZERS",
    "Finding",
    "RichRule",
    "dedupe_findings",
    "rich_rule",
    "rule",
]
