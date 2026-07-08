from __future__ import annotations

from .base import Finding, TextAnalyzer, rule


class KubernetesAnalyzer(TextAnalyzer):
    name = "kubernetes"

    rules = (
        rule(r"\bprivileged\s*:\s*true\b|\bkubernetes\b[^\n.]*\bprivileged\b", "critical", "Kubernetes privileged mode is enabled.", "Remove privileged mode and use narrowly scoped Linux capabilities only when required."),
        rule(r"\bhostnetwork\s*:?\s*true\b|\bhostnetwork\b", "high", "Kubernetes hostNetwork is enabled.", "Disable hostNetwork unless the workload explicitly requires host-level networking."),
        rule(r"\bhostpid\s*:?\s*true\b|\bhostpid\b", "high", "Kubernetes hostPID is enabled.", "Disable hostPID to preserve pod process namespace isolation."),
        rule(r"\bhostipc\s*:?\s*true\b|\bhostipc\b", "high", "Kubernetes hostIPC is enabled.", "Disable hostIPC to preserve pod IPC namespace isolation."),
        rule(r"\bhostpath\b", "high", "Kubernetes hostPath volume detected.", "Replace hostPath with scoped persistent volumes or projected volumes where possible."),
        rule(r"\ballowprivilegeescalation\s*:?\s*true\b|\ballowprivilegeescalation\b", "high", "Kubernetes allows privilege escalation.", "Set allowPrivilegeEscalation to false."),
        rule(r"\brunasuser\s*:?\s*0\b", "critical", "Kubernetes workload runs as UID 0.", "Set runAsNonRoot to true and use a non-root runAsUser value."),
        rule(r"\brunasroot\b|\brun\s+as\s+root\b", "high", "Kubernetes workload is configured to run as root.", "Set runAsNonRoot to true and use a non-root user."),
        rule(r"\bautomountserviceaccounttoken\s*:?\s*true\b", "medium", "Kubernetes automounts the service account token.", "Set automountServiceAccountToken to false when API access is not required."),
        rule(r"\bimage\s*:\s*\S+:latest\b|\bkubernetes\b[^\n.]*\blatest\s+image\b", "high", "Kubernetes workload uses a latest image tag.", "Pin container images to immutable versions or digests."),
        rule(r"\bimagepullpolicy\s*:?\s*always\b", "medium", "Kubernetes imagePullPolicy is Always.", "Use immutable image tags and pull policies that support reproducible deployments."),
    )

    def analyze(self, text: str) -> list[Finding]:
        findings = super().analyze(text)
        mentions_kubernetes = any(token in text for token in ("kubernetes", "k8s", "deployment.yaml", "pod", "helm"))
        if mentions_kubernetes and "resources:" not in text and "limits:" not in text and "resource limits" not in text:
            findings.append(Finding("medium", "Kubernetes resource limits are missing.", "Define CPU and memory requests and limits for each workload.", 8, 70))
        if mentions_kubernetes and "readinessprobe" not in text and "readiness probe" not in text:
            findings.append(Finding("medium", "Kubernetes readinessProbe is missing.", "Add a readinessProbe so traffic only reaches ready pods.", 8, 70))
        if mentions_kubernetes and "livenessprobe" not in text and "liveness probe" not in text:
            findings.append(Finding("medium", "Kubernetes livenessProbe is missing.", "Add a livenessProbe so failed containers can be restarted.", 8, 70))
        return findings
