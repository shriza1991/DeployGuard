from __future__ import annotations

import re
from .base import Finding, TextAnalyzer, rule


class DockerAnalyzer(TextAnalyzer):
    name = "docker"

    rules = (
        rule(
            r"(?m)^\s*user\s+(?:root|0)\b|\bdocker[^\n.]*\brun(?:s|ning)?\s+as\s+root\b|\bcontainer[s]?[^\n.]*\brun(?:s|ning)?\s+as\s+root\b|\broot\s+container\b",
            severity="HIGH",
            reason="Docker container is configured to run as root user.",
            recommendation="Run containers using a dedicated non-root user (e.g. USER nonroot).",
            rule_id="DOCKER_ROOT_USER",
            category="docker",
            subcategory="privilege",
            policy_action="REVIEW_REQUIRED",
            confidence=0.98,
        ),
        rule(
            r"(?m)^-\s*user\s+(?!(?:root|0)\b)\w+",
            severity="HIGH",
            reason="Non-root USER instruction was removed from Dockerfile.",
            recommendation="Retain a dedicated non-root user instruction in the container build.",
            rule_id="DOCKER_REMOVED_NON_ROOT_USER",
            category="docker",
            subcategory="privilege",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
        ),
        rule(
            r"(?m)^\s*from\s+(?:\S+/)?(?:ubuntu|alpine|python|node|golang|debian|centos|fedora|amazonlinux)(?::latest|\s*$)",
            severity="HIGH",
            reason="Docker base image uses an unpinned or :latest tag.",
            recommendation="Pin base images to an immutable version tag or SHA256 digest.",
            rule_id="DOCKER_LATEST_TAG",
            category="docker",
            subcategory="unpinned_version",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
        ),
        rule(
            r"\bfrom\s+\S+:latest\b|\blatest\s+image\s+tags?\b",
            severity="HIGH",
            reason="Docker image tag is set to latest.",
            recommendation="Pin container images to specific immutable versions.",
            rule_id="DOCKER_LATEST_TAG",
            category="docker",
            subcategory="unpinned_version",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
        ),
        rule(
            r"\bdocker[^\n.]*\bprivileged\b|\bprivileged[^\n.]*\bdocker\b|\bcontainer[^\n.]*\bprivileged\b|\b--privileged\b",
            severity="CRITICAL",
            reason="Privileged Docker container mode detected.",
            recommendation="Remove privileged mode and grant only minimal necessary Linux capabilities.",
            rule_id="DOCKER_PRIVILEGED",
            category="docker",
            subcategory="privilege",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"(?m)^\s*add\s+|\badd\s+instruction\b",
            severity="MEDIUM",
            reason="Dockerfile uses ADD instruction instead of COPY.",
            recommendation="Use COPY unless tarball auto-extraction is explicitly required.",
            rule_id="DOCKER_ADD_INSTRUCTION",
            category="docker",
            subcategory="best_practice",
            policy_action="REVIEW_REQUIRED",
            confidence=0.90,
        ),
        rule(
            r"\bcurl\b[^\n|]*\|\s*(?:sh|bash)\b|\bwget\b[^\n|]*\|\s*(?:sh|bash)\b",
            severity="CRITICAL",
            reason="Docker build executes unverified remote script via shell pipe (curl | bash).",
            recommendation="Download scripts to disk, verify checksums/signatures, and execute explicitly.",
            rule_id="DOCKER_CURL_BASH",
            category="docker",
            subcategory="remote_execution",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"(?m)^\s*run\s+.*apt-get\s+install(?!.*rm\s+-rf\s+/var/lib/apt/lists)",
            severity="MEDIUM",
            reason="Package manager apt-get installed packages without cleaning cache lists.",
            recommendation="Append '&& rm -rf /var/lib/apt/lists/*' in the same RUN layer.",
            rule_id="DOCKER_CACHE_NOT_CLEANED",
            category="docker",
            subcategory="image_size",
            policy_action="REVIEW_REQUIRED",
            confidence=0.90,
        ),
        rule(
            r"(?m)^\s*entrypoint\s+[\"']?[a-zA-Z0-9_\-./]+[\"']?\s+[^\s\[]",
            severity="MEDIUM",
            reason="Dockerfile uses shell-form ENTRYPOINT instead of JSON array exec-form.",
            recommendation="Use JSON array syntax ENTRYPOINT [\"executable\", \"param\"] to pass signals correctly.",
            rule_id="DOCKER_SHELL_ENTRYPOINT",
            category="docker",
            subcategory="best_practice",
            policy_action="REVIEW_REQUIRED",
            confidence=0.85,
        ),
        rule(
            r"(?:token|secret|password|api[_-]?key)\s*=\s*[\"'][^\"']{8,}[\"']",
            severity="CRITICAL",
            reason="Dockerfile contains embedded secrets or API keys.",
            recommendation="Use secret injection or environment variables at runtime instead of hardcoding secrets.",
            rule_id="DOCKER_EXPOSED_SECRET",
            category="secrets",
            subcategory="exposure",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"\bexpose\s+22\b|\bopens?\s+22\b",
            severity="HIGH",
            reason="Docker container exposes SSH port 22.",
            recommendation="Remove SSH server from container and use container exec for debugging.",
            rule_id="DOCKER_EXPOSE_SSH",
            category="networking",
            subcategory="exposure",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
        ),
    )

    def analyze(self, text: str, file_path: str = "Dockerfile") -> list[Finding]:
        findings = super().analyze(text, file_path=file_path)
        mentions_docker = any(token in text.lower() for token in ("docker", "dockerfile", "container", "from "))
        has_user_instruction = bool(self._has_user_instruction(text))
        
        if mentions_docker and not has_user_instruction:
            findings.append(
                Finding(
                    severity="HIGH",
                    weight=15,
                    reason="Dockerfile is missing a USER instruction.",
                    recommendation="Add a USER instruction to run the container as a non-root account.",
                    rule_id="DOCKER_MISSING_USER",
                    category="docker",
                    subcategory="privilege",
                    policy_action="REVIEW_REQUIRED",
                    confidence=0.85,
                    evidence={"file": file_path, "matched": "missing USER"},
                )
            )
        if mentions_docker and "healthcheck" not in text.lower():
            findings.append(
                Finding(
                    severity="LOW",
                    weight=3,
                    reason="Dockerfile is missing a HEALTHCHECK instruction.",
                    recommendation="Add a HEALTHCHECK so orchestrators can detect unhealthy containers.",
                    rule_id="DOCKER_MISSING_HEALTHCHECK",
                    category="docker",
                    subcategory="health",
                    policy_action="SAFE",
                    confidence=0.80,
                    evidence={"file": file_path, "matched": "missing HEALTHCHECK"},
                )
            )
        return findings

    @staticmethod
    def _has_user_instruction(text: str) -> bool:
        return bool(re.search(r"(?m)^\s*user\s+", text, re.IGNORECASE))

