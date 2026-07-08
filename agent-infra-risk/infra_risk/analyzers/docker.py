from __future__ import annotations

from .base import Finding, TextAnalyzer, rule


class DockerAnalyzer(TextAnalyzer):
    name = "docker"

    rules = (
        rule(r"\buser\s+root\b|\bdocker[^\n.]*\brun(?:s|ning)?\s+as\s+root\b|\bcontainer[s]?[^\n.]*\brun(?:s|ning)?\s+as\s+root\b|\broot\s+container\b", "critical", "Docker container runs as root.", "Run containers using a dedicated non-root user."),
        rule(r"\bfrom\s+(?:ubuntu|alpine):latest\b", "high", "Docker base image uses a latest tag.", "Pin base images to a specific immutable version or digest."),
        rule(r"\bfrom\s+\S+:latest\b|\blatest\s+image\s+tags?\b|\buses?\s+latest\b", "high", "Docker image uses the latest tag.", "Pin Docker images to a specific version or digest."),
        rule(r"\bdocker[^\n.]*\bprivileged\b|\bprivileged[^\n.]*\bdocker\b|\bcontainer[^\n.]*\bprivileged\b|\b--privileged\b", "critical", "Privileged Docker container detected.", "Remove privileged mode and grant only the specific capabilities required."),
        rule(r"(?m)^\s*add\s+|\badd\s+instruction\b", "medium", "Dockerfile uses ADD instruction.", "Use COPY unless ADD-specific archive extraction behavior is required."),
        rule(r"\bcurl\b[^\n|]*\|\s*(?:sh|bash)\b", "critical", "Docker build executes curl piped to shell.", "Download scripts, verify integrity, and execute them explicitly."),
        rule(r"\bwget\b[^\n|]*\|\s*(?:sh|bash)\b", "critical", "Docker build executes wget piped to shell.", "Download scripts, verify integrity, and execute them explicitly."),
        rule(r"\bapt-get\s+install\b", "medium", "Docker build installs packages with apt-get.", "Pin package versions and remove package manager caches in the same layer."),
        rule(r"\bapk\s+add\b", "medium", "Docker build installs packages with apk add.", "Pin package versions and avoid unnecessary runtime packages."),
        rule(r"\byum\s+install\b", "medium", "Docker build installs packages with yum.", "Pin package versions and avoid unnecessary runtime packages."),
        rule(r"\bdnf\s+install\b", "medium", "Docker build installs packages with dnf.", "Pin package versions and avoid unnecessary runtime packages."),
        rule(r"(?:token|secret|password|api[_-]?key)\s*=", "critical", "Docker configuration appears to contain embedded secrets.", "Move secrets to a secret manager or runtime secret injection."),
        rule(r"\bexpose\s+22\b|\bopens?\s+22\b", "high", "Docker container exposes SSH port 22.", "Avoid exposing SSH from application containers."),
        rule(r"\bexpose\s+3306\b|\bopens?\s+3306\b", "high", "Docker container exposes MySQL port 3306.", "Do not expose database ports publicly from containers."),
        rule(r"\bexpose\s+5432\b|\bopens?\s+5432\b", "high", "Docker container exposes PostgreSQL port 5432.", "Do not expose database ports publicly from containers."),
    )

    def analyze(self, text: str) -> list[Finding]:
        findings = super().analyze(text)
        mentions_docker = any(token in text for token in ("docker", "dockerfile", "container"))
        has_user_instruction = bool(self._has_user_instruction(text))
        if mentions_docker and not has_user_instruction:
            findings.append(Finding(
                severity="medium",
                weight=8,
                reason="Dockerfile is missing a USER instruction.",
                recommendation="Add a USER instruction that runs the container as a non-root account.",
                confidence=70,
            ))
        if mentions_docker and "healthcheck" not in text:
            findings.append(Finding(
                severity="low",
                weight=3,
                reason="Dockerfile is missing a HEALTHCHECK.",
                recommendation="Add a HEALTHCHECK so unhealthy containers can be detected and replaced.",
                confidence=65,
            ))
        return findings

    @staticmethod
    def _has_user_instruction(text: str) -> bool:
        return "user " in text or " user=" in text
