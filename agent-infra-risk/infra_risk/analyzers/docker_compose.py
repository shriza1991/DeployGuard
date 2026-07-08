from __future__ import annotations

from .base import TextAnalyzer, rule


class DockerComposeAnalyzer(TextAnalyzer):
    name = "docker_compose"

    rules = (
        rule(r"\bprivileged\s*:\s*true\b", "critical", "Docker Compose service runs in privileged mode.", "Remove privileged mode and grant only specific capabilities."),
        rule(r"\bnetwork_mode\s*:\s*host\b", "high", "Docker Compose service uses host networking.", "Use bridge networking and expose only required ports."),
        rule(r"\bpid\s*:\s*host\b", "high", "Docker Compose service shares the host PID namespace.", "Do not share the host PID namespace with containers."),
        rule(r"\bvolumes\s*:.*?/var/run/docker\.sock|/var/run/docker\.sock", "critical", "Docker Compose mounts the Docker socket.", "Avoid mounting the Docker socket because it grants host-level control."),
        rule(r"\bimage\s*:\s*\S+:latest\b|\bcompose\b[^\n.]*\blatest\s+image\b", "high", "Docker Compose service uses a latest image tag.", "Pin Compose service images to immutable versions or digests."),
        rule(r"\buser\s*:\s*root\b|\broot\s+user\b", "critical", "Docker Compose service runs as root.", "Run Compose services as non-root users."),
        rule(r"(?:token|secret|password|api[_-]?key)\s*=", "critical", "Docker Compose configuration appears to contain plaintext secrets.", "Move secrets to Docker secrets or an external secret manager."),
    )
