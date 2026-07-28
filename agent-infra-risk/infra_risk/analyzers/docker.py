"""
infra_risk.analyzers.docker
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Deterministic security detectors for Dockerfile content found in a PR diff.

Rules
-----
DOCKER_ROOT_USER          – USER root / USER 0 / missing USER instruction
DOCKER_PRIVILEGED         – --privileged flag present
DOCKER_SOCK_MOUNT         – docker.sock bind-mounted inside the build
DOCKER_HOST_NETWORK       – --network=host
DOCKER_LATEST_TAG         – FROM image:latest (unpinned)
DOCKER_MISSING_HEALTHCHECK– No HEALTHCHECK instruction
DOCKER_EXPOSED_SECRET     – ARG / ENV with inline token / password value
DOCKER_ADD_REMOTE_URL     – ADD http(s):// (remote fetch with auto-extract)
"""
from __future__ import annotations

import re
from .base import Finding, RichRule, TextAnalyzer, rich_rule, SEVERITY_WEIGHTS


class DockerAnalyzer(TextAnalyzer):
    name = "docker"

    rich_rules: tuple[RichRule, ...] = (

        # ── DOCKER_ROOT_USER ──────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*USER\s+(?:root|0)\b",
            severity="HIGH",
            rule_id="DOCKER_ROOT_USER",
            category="docker",
            subcategory="privilege",
            policy_action="REVIEW_REQUIRED",
            confidence=0.97,
            reason="Dockerfile explicitly sets the container user to root (USER root / USER 0).",
            recommendation=(
                "Create a dedicated application user during the build and switch to it: "
                "RUN addgroup -S appgroup && adduser -S appuser -G appgroup\n"
                "USER appuser"
            ),
            what_changed=(
                "The PR adds or retains a 'USER root' or 'USER 0' instruction, "
                "meaning every process inside the running container executes as UID 0."
            ),
            why_dangerous=(
                "A process running as root inside a container has full capability set by default. "
                "Any command injection, path traversal, or library vulnerability can be directly "
                "exploited without needing a privilege-escalation step. "
                "Combined with writable volumes or mounted host paths the blast radius reaches the host."
            ),
            attack_path=(
                "1. Attacker finds RCE in application (e.g. deserialization, SSRF to internal service). "
                "2. Code runs as UID 0 — attacker writes to /etc/cron.d or /etc/passwd directly. "
                "3. If any hostPath or docker.sock is mounted, attacker escapes to host node. "
                "4. Lateral movement to other pods via shared node credentials or IMDS token theft."
            ),
            blast_radius=(
                "Container-level: full filesystem write. "
                "Node-level (if hostPath / sock present): complete node compromise. "
                "Cluster-level (if RBAC is misconfigured): cross-namespace pod creation."
            ),
        ),

        # ── DOCKER_PRIVILEGED ─────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)--privileged\b",
            severity="CRITICAL",
            rule_id="DOCKER_PRIVILEGED",
            category="docker",
            subcategory="privilege",
            policy_action="BLOCK",
            confidence=0.98,
            reason="Container is started with --privileged, disabling all Linux namespace isolation.",
            recommendation=(
                "Remove --privileged. "
                "Grant only the specific capabilities the application needs: "
                "docker run --cap-add=NET_BIND_SERVICE --cap-drop=ALL ..."
            ),
            what_changed=(
                "The diff introduces --privileged in a RUN instruction, entrypoint wrapper, "
                "or docker-run invocation inside CI/CD."
            ),
            why_dangerous=(
                "--privileged disables seccomp, AppArmor, and all capability restrictions. "
                "The container can load kernel modules, access raw devices, and modify host namespaces. "
                "This is functionally equivalent to running directly on the host as root."
            ),
            attack_path=(
                "1. Any process inside the container can call mount(2) to remount the host filesystem. "
                "2. Attacker mounts host / and writes a backdoor to /etc/cron.d on the host. "
                "3. Direct kernel exploit surface is exposed (no seccomp filter)."
            ),
            blast_radius=(
                "Full host OS compromise. "
                "All sibling containers and pods sharing the node are reachable. "
                "Cloud IMDS credentials (AWS/GCP/Azure) readable from inside the container."
            ),
        ),

        # ── DOCKER_SOCK_MOUNT ─────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)/var/run/docker\.sock",
            severity="CRITICAL",
            rule_id="DOCKER_SOCK_MOUNT",
            category="docker",
            subcategory="privilege",
            policy_action="BLOCK",
            confidence=0.98,
            reason="Docker socket (/var/run/docker.sock) is mounted into the container.",
            recommendation=(
                "Remove the docker.sock mount. "
                "Use Docker-in-Docker (DinD) with TLS, Kaniko, or Buildah for container builds that need "
                "Docker API access without exposing the host socket."
            ),
            what_changed=(
                "The diff adds a volume mount binding the host Docker socket into the container, "
                "granting unrestricted Docker API access from within the container."
            ),
            why_dangerous=(
                "The Docker socket gives the container full control over the Docker daemon on the host. "
                "Any process inside can create new containers with arbitrary mounts, "
                "pull and run privileged images, or read volumes from other containers. "
                "This is a well-documented container escape technique (CVE-class: Docker socket abuse)."
            ),
            attack_path=(
                "1. Attacker achieves code execution inside the container (e.g. via RCE in app). "
                "2. They issue 'docker run -v /:/host ubuntu chroot /host' via the mounted socket. "
                "3. Full host filesystem is now accessible as root. "
                "4. SSH keys, cloud credentials, and secrets from all other containers are readable."
            ),
            blast_radius=(
                "Complete host OS compromise. "
                "All containers on the host node exposed. "
                "Persistent backdoor installable on the host (cron, systemd unit)."
            ),
        ),

        # ── DOCKER_HOST_NETWORK ───────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)--network[=\s]+host\b",
            severity="HIGH",
            rule_id="DOCKER_HOST_NETWORK",
            category="docker",
            subcategory="networking",
            policy_action="REVIEW_REQUIRED",
            confidence=0.96,
            reason="Container uses host network mode (--network=host), removing network namespace isolation.",
            recommendation=(
                "Use bridge networking and publish only required ports: "
                "docker run -p 8080:8080 ... "
                "Reserve --network=host for performance-critical scenarios on dedicated hosts only."
            ),
            what_changed=(
                "The diff sets --network=host, causing the container to share the host's "
                "network stack including all open ports and interfaces."
            ),
            why_dangerous=(
                "Host network mode bypasses Docker's port isolation. "
                "The container can bind to any host port, sniff traffic on host interfaces, "
                "and is directly reachable on the host's IP without port-mapping controls. "
                "Services that should be internal-only become exposed on the node's primary interface."
            ),
            attack_path=(
                "1. Attacker compromises the container process. "
                "2. They bind a reverse shell on an unused host port (e.g. 31337). "
                "3. They can ARP-spoof or sniff unencrypted traffic on the host NIC. "
                "4. Internal metadata services (169.254.169.254) become directly accessible."
            ),
            blast_radius=(
                "Node network perimeter compromised. "
                "All host services reachable from inside the container. "
                "Cloud IMDS (AWS/GCP/Azure) directly accessible — IAM credential theft possible."
            ),
        ),

        # ── DOCKER_LATEST_TAG ─────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*FROM\s+\S+:latest\b",
            severity="MEDIUM",
            rule_id="DOCKER_LATEST_TAG",
            category="docker",
            subcategory="unpinned_version",
            policy_action="REVIEW_REQUIRED",
            confidence=0.94,
            reason="Dockerfile pulls a base image using the :latest tag, which is mutable and unpredictable.",
            recommendation=(
                "Pin the base image to a specific immutable digest or version tag: "
                "FROM python:3.11.9-slim@sha256:<digest> "
                "Use 'docker pull --quiet python:3.11.9-slim | docker inspect --format={{.Id}}' to get the digest."
            ),
            what_changed=(
                "The FROM instruction uses :latest, meaning each build may pull a different "
                "image layer without any change to the Dockerfile itself."
            ),
            why_dangerous=(
                ":latest is re-tagged by image maintainers on every release. "
                "A compromised upstream registry or a malicious maintainer push can silently "
                "introduce backdoored layers. "
                "Builds are non-reproducible, breaking rollback guarantees."
            ),
            attack_path=(
                "1. Attacker compromises upstream image maintainer account (supply-chain attack). "
                "2. New :latest tag is pushed with a malicious layer. "
                "3. Next CI build silently incorporates the backdoored layer. "
                "4. Malware runs inside production container on next deployment."
            ),
            blast_radius=(
                "Full application container compromise on next build. "
                "All environments that pull latest (dev, staging, prod) are affected simultaneously. "
                "Rollback is non-deterministic — there is no guarantee the previous :latest can be restored."
            ),
        ),

        # ── DOCKER_EXPOSED_SECRET ─────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*(?:ARG|ENV)\s+\S*(?:TOKEN|SECRET|PASSWORD|API_KEY|APIKEY|PRIVATE_KEY|ACCESS_KEY)\s*=\s*\S+",
            severity="CRITICAL",
            rule_id="DOCKER_EXPOSED_SECRET",
            category="secrets",
            subcategory="exposure",
            policy_action="BLOCK",
            confidence=0.96,
            reason=(
                "Dockerfile bakes a secret value into an ARG or ENV instruction. "
                "Secrets embedded in image layers are permanently recoverable from the image."
            ),
            recommendation=(
                "Never pass secrets as ARG or ENV at build time. "
                "Use Docker BuildKit secrets: RUN --mount=type=secret,id=mysecret ... "
                "At runtime, inject via orchestrator secrets (Kubernetes Secrets, AWS Secrets Manager, Vault)."
            ),
            what_changed=(
                "The diff introduces an ARG or ENV instruction whose name contains 'token', "
                "'secret', 'password', 'api_key', or 'access_key' with an inline value."
            ),
            why_dangerous=(
                "Docker image layers are immutable and cached. "
                "Even if a subsequent RUN instruction unsets the variable, "
                "the value is permanently readable via 'docker history --no-trunc'. "
                "Any registry push makes the secret recoverable to anyone with read access to the image."
            ),
            attack_path=(
                "1. Image is pushed to registry (private or public). "
                "2. Attacker pulls the image or gains registry read access. "
                "3. They run 'docker history --no-trunc <image>' to recover the secret. "
                "4. Credential is used to access API, database, or cloud account."
            ),
            blast_radius=(
                "Secret is leaked to every person or system with registry read access. "
                "Credential rotation does not clean up the exposed layer — image rebuild and re-push required. "
                "All downstream deployments of this image carry the exposed credential."
            ),
        ),

        # ── DOCKER_ADD_REMOTE_URL ─────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*ADD\s+https?://\S+",
            severity="HIGH",
            rule_id="DOCKER_ADD_REMOTE_URL",
            category="docker",
            subcategory="remote_execution",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
            reason=(
                "Dockerfile uses ADD with a remote URL. "
                "This fetches and auto-extracts content from the internet at build time without checksum verification."
            ),
            recommendation=(
                "Replace ADD <url> with a RUN curl/wget that verifies a SHA256 checksum before use: "
                "RUN curl -fsSL https://example.com/file.tar.gz -o /tmp/file.tar.gz "
                "    && echo '<expected-sha256>  /tmp/file.tar.gz' | sha256sum -c - "
                "    && tar -xzf /tmp/file.tar.gz -C /app"
            ),
            what_changed=(
                "The diff adds an ADD instruction pointing to an http/https URL. "
                "Docker fetches this URL at build time and automatically extracts archives."
            ),
            why_dangerous=(
                "ADD with a remote URL has no built-in integrity verification. "
                "A compromised CDN, DNS hijack, or MITM can serve a different file. "
                "If the URL serves a .tar.gz, Docker silently extracts it, "
                "potentially overwriting critical files in the image."
            ),
            attack_path=(
                "1. Attacker performs DNS hijack or CDN compromise for the target URL. "
                "2. Malicious archive is served in place of the legitimate file. "
                "3. ADD auto-extracts the archive, overwriting application binaries. "
                "4. Next container start runs the attacker's code."
            ),
            blast_radius=(
                "All images built from this Dockerfile may contain attacker-controlled binaries. "
                "Every environment that deploys these images is affected."
            ),
        ),
    )

    def analyze(self, text: str, file_path: str = "Dockerfile") -> list[Finding]:  # type: ignore[override]
        findings = super().analyze(text, file_path=file_path)

        is_dockerfile = (
            re.search(r"dockerfile", file_path, re.IGNORECASE)
            or bool(re.search(r"(?m)^\+?\s*FROM\s+\S+", text, re.IGNORECASE))
        )

        if not is_dockerfile:
            return findings

        # ── DOCKER_ROOT_USER (pattern-missed: no USER instruction at all) ────
        has_user_instruction = bool(re.search(r"(?m)^\+?\s*USER\s+", text, re.IGNORECASE))
        has_from = bool(re.search(r"(?m)^\+?\s*FROM\s+\S+", text, re.IGNORECASE))

        if has_from and not has_user_instruction:
            findings.append(
                Finding(
                    severity="HIGH",
                    weight=SEVERITY_WEIGHTS["HIGH"],
                    rule_id="DOCKER_ROOT_USER",
                    category="docker",
                    subcategory="privilege",
                    policy_action="REVIEW_REQUIRED",
                    confidence=0.88,
                    reason=(
                        "Dockerfile has no USER instruction — the container will run as root by default."
                    ),
                    recommendation=(
                        "Add a non-root USER at the end of the Dockerfile: "
                        "RUN addgroup -S app && adduser -S app -G app\n"
                        "USER app"
                    ),
                    evidence={"file": file_path, "matched": "missing USER instruction"},
                    what_changed=(
                        "The diff contains a Dockerfile with FROM but no USER instruction, "
                        "meaning the resulting image defaults to running as UID 0 (root)."
                    ),
                    why_dangerous=(
                        "Docker images without a USER instruction run all processes as root. "
                        "This violates the principle of least privilege and amplifies the impact "
                        "of any application-level vulnerability."
                    ),
                    attack_path=(
                        "1. Application vulnerability gives code execution (e.g. deserialization). "
                        "2. Code runs as UID 0 — writes to /etc, /usr/bin, cron directories. "
                        "3. If volumes or sidecar containers share paths, compromise spreads."
                    ),
                    blast_radius=(
                        "Full container filesystem writable by the attacker. "
                        "Host-level impact if privileged mode or hostPath volumes are also present."
                    ),
                )
            )

        # ── DOCKER_MISSING_HEALTHCHECK ─────────────────────────────────────────
        if has_from and "HEALTHCHECK" not in text.upper():
            findings.append(
                Finding(
                    severity="LOW",
                    weight=SEVERITY_WEIGHTS["LOW"],
                    rule_id="DOCKER_MISSING_HEALTHCHECK",
                    category="docker",
                    subcategory="health",
                    policy_action="SAFE",
                    confidence=0.80,
                    reason="Dockerfile does not define a HEALTHCHECK instruction.",
                    recommendation=(
                        "Add a HEALTHCHECK instruction so orchestrators can detect and restart "
                        "unhealthy containers:\n"
                        "HEALTHCHECK --interval=30s --timeout=5s --retries=3 \\\n"
                        "  CMD curl -f http://localhost:8080/health || exit 1"
                    ),
                    evidence={"file": file_path, "matched": "missing HEALTHCHECK"},
                    what_changed=(
                        "The Dockerfile in this PR does not include a HEALTHCHECK instruction."
                    ),
                    why_dangerous=(
                        "Without a HEALTHCHECK, Kubernetes and Docker Swarm cannot detect "
                        "when a container's application has crashed or is hung. "
                        "Traffic may be routed to a non-functional container, "
                        "causing silent service degradation."
                    ),
                    attack_path=(
                        "Availability risk rather than a direct attack path. "
                        "A hung container that is not restarted extends the outage window "
                        "following any incident."
                    ),
                    blast_radius=(
                        "Service availability impact. "
                        "Dependent services may see cascading timeouts if the unhealthy container "
                        "remains in the routing pool."
                    ),
                )
            )

        return findings
