from __future__ import annotations

from .base import Finding, dedupe_findings
from .docker import DockerAnalyzer
from .docker_compose import DockerComposeAnalyzer
from .github_actions import GitHubActionsAnalyzer
from .kubernetes import KubernetesAnalyzer
from .secrets import SecretAnalyzer
from .terraform import TerraformAnalyzer


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
    "dedupe_findings",
]
