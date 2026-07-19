from __future__ import annotations

import re
from .base import Finding, TextAnalyzer, rule


class KubernetesAnalyzer(TextAnalyzer):
    name = "kubernetes"

    rules = (
        rule(
            r"\bprivileged\s*:\s*true\b|\bkubernetes\b[^\n.]*\bprivileged\b",
            severity="CRITICAL",
            reason="Kubernetes pod is configured with privileged: true.",
            recommendation="Remove privileged mode and use narrowly scoped Linux capabilities only when strictly required.",
            rule_id="K8S_PRIVILEGED_POD",
            category="kubernetes",
            subcategory="privilege",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"\bcapabilities\s*:\s*(?:\[?\s*[\"']?(?:CAP_SYS_ADMIN|ALL)[\"']?\s*\]?)",
            severity="CRITICAL",
            reason="Kubernetes container requests dangerous Linux capability (CAP_SYS_ADMIN or ALL).",
            recommendation="Drop ALL capabilities and add back only minimal required Linux capabilities.",
            rule_id="K8S_DANGEROUS_CAPABILITIES",
            category="kubernetes",
            subcategory="capabilities",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"\brunasuser\s*:\s*0\b|\brunasroot\b",
            severity="HIGH",
            reason="Kubernetes workload is configured to run as UID 0 (root).",
            recommendation="Set runAsNonRoot: true and specify a non-zero runAsUser.",
            rule_id="K8S_RUN_AS_ROOT",
            category="kubernetes",
            subcategory="privilege",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
        ),
        rule(
            r"\bhostnetwork\s*:\s*true\b",
            severity="HIGH",
            reason="Kubernetes hostNetwork: true is enabled.",
            recommendation="Disable hostNetwork to preserve pod network namespace isolation.",
            rule_id="K8S_HOST_NETWORK",
            category="kubernetes",
            subcategory="networking",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
        ),
        rule(
            r"\bhostpid\s*:\s*true\b|\bhostipc\s*:\s*true\b",
            severity="HIGH",
            reason="Kubernetes hostPID or hostIPC namespace sharing is enabled.",
            recommendation="Disable hostPID and hostIPC to maintain pod namespace isolation.",
            rule_id="K8S_HOST_NAMESPACE",
            category="kubernetes",
            subcategory="isolation",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
        ),
        rule(
            r"\bpath\s*:\s*[\"']?/(?:proc|sys|var/run/docker\.sock|dev)[\"']?\b|\bhostpath\b",
            severity="CRITICAL",
            reason="Kubernetes volume mount points to sensitive host path (/proc, /sys, /var/run/docker.sock).",
            recommendation="Avoid hostPath mounts into sensitive node directories.",
            rule_id="K8S_UNSAFE_VOLUME_MOUNT",
            category="kubernetes",
            subcategory="storage",
            policy_action="BLOCK",
            confidence=0.98,
        ),
        rule(
            r"\ballowprivilegeescalation\s*:\s*true\b",
            severity="HIGH",
            reason="Kubernetes allowPrivilegeEscalation is set to true.",
            recommendation="Set allowPrivilegeEscalation: false in securityContext.",
            rule_id="K8S_PRIVILEGE_ESCALATION",
            category="kubernetes",
            subcategory="privilege",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
        ),
        rule(
            r"\bimage\s*:\s*\S+:latest\b",
            severity="HIGH",
            reason="Kubernetes deployment image tag uses latest.",
            recommendation="Pin container images to specific immutable tags or digests.",
            rule_id="K8S_LATEST_TAG",
            category="kubernetes",
            subcategory="unpinned_version",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
        ),
    )

    def analyze(self, text: str, file_path: str = "deployment.yaml") -> list[Finding]:
        findings = super().analyze(text, file_path=file_path)
        mentions_kubernetes = any(token in text.lower() for token in ("kubernetes", "k8s", "deployment", "pod", "helm"))
        
        if mentions_kubernetes and "resources:" not in text.lower() and "limits:" not in text.lower():
            findings.append(
                Finding(
                    severity="MEDIUM",
                    weight=8,
                    reason="Kubernetes resource limits are missing.",
                    recommendation="Define CPU and memory requests and limits for each container.",
                    rule_id="K8S_MISSING_RESOURCE_LIMITS",
                    category="kubernetes",
                    subcategory="resources",
                    policy_action="REVIEW_REQUIRED",
                    confidence=0.80,
                    evidence={"file": file_path, "matched": "missing resources/limits"},
                )
            )
        return findings

