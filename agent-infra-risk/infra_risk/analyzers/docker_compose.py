"""
infra_risk.analyzers.docker_compose
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Deterministic security detectors for docker-compose.yml files in a PR diff.

Rules
-----
COMPOSE_PRIVILEGED    – privileged: true
COMPOSE_HOST_NETWORK  – network_mode: host
COMPOSE_BIND_MOUNT    – host directory bound into container (./path:... or /abs:...)
COMPOSE_DOCKER_SOCK   – /var/run/docker.sock volume
COMPOSE_ROOT_USER     – user: root / user: "0"
"""
from __future__ import annotations

from .base import RichRule, TextAnalyzer, rich_rule


class DockerComposeAnalyzer(TextAnalyzer):
    name = "docker_compose"

    rich_rules: tuple[RichRule, ...] = (

        # ── COMPOSE_PRIVILEGED ────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*privileged\s*:\s*true\b",
            severity="CRITICAL",
            rule_id="COMPOSE_PRIVILEGED",
            category="docker_compose",
            subcategory="privilege",
            policy_action="BLOCK",
            confidence=0.98,
            reason=(
                "Docker Compose service runs in privileged mode, "
                "disabling all Linux namespace and capability restrictions."
            ),
            recommendation=(
                "Remove 'privileged: true' from the Compose service definition. "
                "Grant only the specific Linux capabilities required:\n"
                "cap_add:\n"
                "  - NET_BIND_SERVICE\n"
                "cap_drop:\n"
                "  - ALL"
            ),
            what_changed=(
                "The diff adds 'privileged: true' to a Docker Compose service definition, "
                "causing docker-compose up to start that container in fully privileged mode."
            ),
            why_dangerous=(
                "Privileged mode disables seccomp, AppArmor, and all Linux capability restrictions. "
                "The container process can modify host kernel parameters, load kernel modules, "
                "mount host filesystems, and access raw network and block devices. "
                "This is functionally equivalent to running as root on the host machine."
            ),
            attack_path=(
                "1. Application vulnerability gives code execution inside the container. "
                "2. Attacker uses privileged access to mount the host filesystem. "
                "3. They write a backdoor to host cron, systemd, or SSH authorized_keys. "
                "4. Persistent host-level compromise — survives container restart."
            ),
            blast_radius=(
                "Full host machine compromise. "
                "All other containers on the host at risk. "
                "Cloud IMDS credentials readable (AWS/GCP/Azure). "
                "Persistent backdoor installable on host."
            ),
        ),

        # ── COMPOSE_HOST_NETWORK ──────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*network_mode\s*:\s*host\b",
            severity="HIGH",
            rule_id="COMPOSE_HOST_NETWORK",
            category="docker_compose",
            subcategory="networking",
            policy_action="REVIEW_REQUIRED",
            confidence=0.96,
            reason=(
                "Docker Compose service uses 'network_mode: host', "
                "removing container network namespace isolation."
            ),
            recommendation=(
                "Replace network_mode: host with bridge networking and explicit port mappings:\n"
                "ports:\n"
                "  - \"8080:8080\"\n"
                "networks:\n"
                "  - internal\n"
                "Reserve host networking only for performance-critical services on dedicated hosts."
            ),
            what_changed=(
                "The diff sets 'network_mode: host' on a Docker Compose service, "
                "causing the container to share the host's network stack."
            ),
            why_dangerous=(
                "Host network mode bypasses Docker's port isolation. "
                "The container can bind to any host port, listen on all host interfaces, "
                "sniff traffic, and directly access cloud metadata endpoints. "
                "Docker Compose port mapping controls become ineffective."
            ),
            attack_path=(
                "1. Attacker compromises the service running in host-network mode. "
                "2. They access 169.254.169.254 (cloud IMDS) to steal IAM role credentials. "
                "3. They sniff unencrypted host-level traffic on all interfaces. "
                "4. They bind a backdoor listener on any host port (no Docker publish needed)."
            ),
            blast_radius=(
                "Host network perimeter exposed to the container. "
                "All services listening on host interfaces reachable. "
                "Cloud IAM credential theft possible via IMDS. "
                "Traffic on host interfaces may be captured."
            ),
        ),

        # ── COMPOSE_BIND_MOUNT ────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)volumes\s*:.*?(?:^\s+-\s+[./][^:]+:|^\s+-\s+/[^:]+:)",
            severity="MEDIUM",
            rule_id="COMPOSE_BIND_MOUNT",
            category="docker_compose",
            subcategory="storage",
            policy_action="REVIEW_REQUIRED",
            confidence=0.85,
            reason=(
                "Docker Compose service uses a bind mount (host directory mounted into the container). "
                "Bind mounts expose host filesystem paths to the container process."
            ),
            recommendation=(
                "Use named volumes instead of bind mounts for persistent data:\n"
                "volumes:\n"
                "  - app_data:/var/lib/app\n"
                "volumes:\n"
                "  app_data:\n"
                "If bind mounts are required (e.g. for local development), "
                "add ':ro' to make them read-only and never mount sensitive host directories."
            ),
            what_changed=(
                "The diff adds a volume entry that bind-mounts a host directory "
                "(relative './path:' or absolute '/path:') into the container."
            ),
            why_dangerous=(
                "Bind mounts give the container direct access to host filesystem paths. "
                "A container running as root can write to these paths and affect host-side files. "
                "If sensitive directories are mounted (e.g. ~/.ssh, /etc, /var/run), "
                "the container can read or modify critical host configuration."
            ),
            attack_path=(
                "1. Application compromise gives code execution inside the container. "
                "2. Container writes malicious content to the bind-mounted host path. "
                "3. If the host path is used by another service or cron, "
                "   the attacker's payload executes on the host. "
                "4. Host-level persistence established."
            ),
            blast_radius=(
                "Depends on which host path is mounted. "
                "Worst case (/ or /etc): full host configuration access. "
                "Sensitive paths (SSH keys, credentials, cloud configs) are readable by the container."
            ),
        ),

        # ── COMPOSE_DOCKER_SOCK ───────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)/var/run/docker\.sock",
            severity="CRITICAL",
            rule_id="COMPOSE_DOCKER_SOCK",
            category="docker_compose",
            subcategory="privilege",
            policy_action="BLOCK",
            confidence=0.98,
            reason=(
                "Docker Compose mounts the Docker socket (/var/run/docker.sock) into a service container, "
                "granting that container full control over the Docker daemon on the host."
            ),
            recommendation=(
                "Remove the docker.sock volume mount. "
                "For CI build services, use Kaniko or Buildah (rootless, daemon-free). "
                "For monitoring tools that genuinely require Docker API access, "
                "use Docker's TLS-authenticated TCP socket with a read-only client certificate "
                "and restrict which API endpoints are accessible."
            ),
            what_changed=(
                "The diff adds a volume entry mounting /var/run/docker.sock from the host "
                "into a Docker Compose service container."
            ),
            why_dangerous=(
                "The Docker socket is the root-equivalent control plane for the Docker daemon. "
                "Any process with access to the socket can create new privileged containers, "
                "mount any host path, execute commands in any running container, "
                "read environment variables and secrets from other containers, "
                "and exfiltrate all container filesystems. "
                "This is one of the most common and reliable container escape techniques."
            ),
            attack_path=(
                "1. Attacker gains code execution in the Compose service. "
                "2. They use the mounted socket to issue: "
                "   docker run -v /:/host --rm -it ubuntu chroot /host bash. "
                "3. Full read/write access to the host filesystem as root. "
                "4. SSH keys, cloud credentials, and other container secrets exfiltrated."
            ),
            blast_radius=(
                "Full host machine compromise. "
                "All Docker containers on the host accessible (read env, exec). "
                "Persistent backdoor can be installed on the host. "
                "Cloud IAM credentials stealable from IMDS."
            ),
        ),

        # ── COMPOSE_ROOT_USER ─────────────────────────────────────────────────
        rich_rule(
            pattern=r'(?m)^\+?\s*user\s*:\s*(?:root|"0"|\'0\'|0)\b',
            severity="HIGH",
            rule_id="COMPOSE_ROOT_USER",
            category="docker_compose",
            subcategory="privilege",
            policy_action="REVIEW_REQUIRED",
            confidence=0.96,
            reason=(
                "Docker Compose service is configured to run as root (user: root or user: 0). "
                "All container processes execute with UID 0."
            ),
            recommendation=(
                "Run the service as a non-root user:\n"
                "user: \"1000:1000\"  # non-root UID:GID\n"
                "Ensure the application image supports running as non-root "
                "(file permissions, port binding)."
            ),
            what_changed=(
                "The diff adds 'user: root' or 'user: 0' to a Docker Compose service, "
                "or the service is run without a 'user:' directive and the base image defaults to root."
            ),
            why_dangerous=(
                "Running as UID 0 means any code execution vulnerability in the application "
                "immediately gives the attacker root inside the container without needing privilege escalation. "
                "This amplifies the impact of every vulnerability in the application stack."
            ),
            attack_path=(
                "1. Application vulnerability (deserialization, command injection) gives code execution. "
                "2. Code runs as UID 0 — attacker writes to /etc, installs backdoors. "
                "3. If bind mounts or docker.sock are also present: host-level compromise. "
                "4. All secrets in the container filesystem and environment readable."
            ),
            blast_radius=(
                "Container-level: full filesystem access, all secrets readable. "
                "Host-level (if privileged mode or bind mounts): host machine at risk. "
                "Network-level: if host network mode is also set, host interfaces exposed."
            ),
        ),
    )
