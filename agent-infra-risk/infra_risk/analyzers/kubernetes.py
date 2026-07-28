"""
infra_risk.analyzers.kubernetes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Deterministic security detectors for Kubernetes manifests and Helm values in a PR diff.

Rules
-----
K8S_PRIVILEGED          – privileged: true
K8S_HOST_PATH           – hostPath: volume
K8S_HOST_NETWORK        – hostNetwork: true
K8S_NET_ADMIN           – NET_ADMIN in capabilities.add
K8S_SYS_ADMIN           – SYS_ADMIN in capabilities.add
K8S_RUN_AS_ROOT         – runAsUser: 0 or runAsNonRoot: false
K8S_MISSING_LIMITS      – no resources.limits defined
K8S_MISSING_REQUESTS    – no resources.requests defined
"""
from __future__ import annotations

import re
from .base import Finding, RichRule, TextAnalyzer, rich_rule, SEVERITY_WEIGHTS


class KubernetesAnalyzer(TextAnalyzer):
    name = "kubernetes"

    rich_rules: tuple[RichRule, ...] = (

        # ── K8S_PRIVILEGED ────────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*privileged\s*:\s*true\b",
            severity="CRITICAL",
            rule_id="K8S_PRIVILEGED",
            category="kubernetes",
            subcategory="privilege",
            policy_action="BLOCK",
            confidence=0.98,
            reason="Kubernetes container security context sets 'privileged: true', disabling all Linux namespace isolation.",
            recommendation=(
                "Remove 'privileged: true' from the securityContext. "
                "If specific kernel capabilities are needed, add only the minimal required capabilities:\n"
                "securityContext:\n"
                "  capabilities:\n"
                "    drop: [\"ALL\"]\n"
                "    add: [\"NET_BIND_SERVICE\"]  # only if needed"
            ),
            what_changed=(
                "The diff sets 'privileged: true' in a container's securityContext, "
                "causing Kubernetes to run the container with all Linux capabilities enabled "
                "and all namespace isolation disabled."
            ),
            why_dangerous=(
                "A privileged container has unrestricted access to the host kernel and devices. "
                "It can load kernel modules, access raw block devices, modify host network interfaces, "
                "and escape the container entirely — effectively owning the Kubernetes node."
            ),
            attack_path=(
                "1. Attacker achieves code execution inside the privileged container. "
                "2. They mount the host filesystem via /proc/1/root or direct device access. "
                "3. They write a backdoor to the host's cron, systemd, or SSH authorized_keys. "
                "4. Full node compromise — all pods on the node, node's cloud IAM role, IMDS credentials."
            ),
            blast_radius=(
                "Full Kubernetes node compromise. "
                "All pods scheduled on the same node are accessible. "
                "Node's cloud provider IAM role credentials (AWS IRSA, GKE Workload Identity) are stealable. "
                "If the node has cluster-admin RBAC: full cluster compromise."
            ),
        ),

        # ── K8S_HOST_PATH ─────────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*hostPath\s*:",
            severity="HIGH",
            rule_id="K8S_HOST_PATH",
            category="kubernetes",
            subcategory="storage",
            policy_action="REVIEW_REQUIRED",
            confidence=0.96,
            reason=(
                "Kubernetes manifest uses a hostPath volume, mounting a directory "
                "from the underlying node's filesystem into the pod."
            ),
            recommendation=(
                "Replace hostPath with a PersistentVolumeClaim backed by a storage class:\n"
                "volumes:\n"
                "  - name: data\n"
                "    persistentVolumeClaim:\n"
                "      claimName: my-pvc\n"
                "If hostPath is strictly required (e.g. node-level monitoring agents), "
                "restrict the path to the minimum and set readOnly: true."
            ),
            what_changed=(
                "The diff adds a 'hostPath' volume definition that binds a node filesystem path "
                "into the pod, giving the pod access to host files at that path."
            ),
            why_dangerous=(
                "hostPath volumes break the container isolation boundary by design. "
                "Depending on which host path is mounted, the pod may access: "
                "node credentials, kubelet config, container runtime socket, "
                "other pods' secrets, or the host's /etc and /proc directories. "
                "Paths like /var/run/docker.sock or /var/run/containerd.sock are instant container escapes."
            ),
            attack_path=(
                "1. Pod mounts a sensitive hostPath (e.g. /var/run/docker.sock or /etc/kubernetes). "
                "2. Attacker exploits the application to get code execution. "
                "3. They use the mounted path to escape the pod or read node secrets. "
                "4. Node-level credentials harvested → lateral movement to other pods and API server."
            ),
            blast_radius=(
                "Varies by path: /var/run/docker.sock = full node; /etc = node credentials; "
                "/ = complete node compromise. "
                "All pods on the same node potentially exposed via node-level access."
            ),
        ),

        # ── K8S_HOST_NETWORK ─────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*hostNetwork\s*:\s*true\b",
            severity="HIGH",
            rule_id="K8S_HOST_NETWORK",
            category="kubernetes",
            subcategory="networking",
            policy_action="REVIEW_REQUIRED",
            confidence=0.96,
            reason=(
                "Kubernetes pod spec sets 'hostNetwork: true', sharing the node's network namespace "
                "with the pod and bypassing Kubernetes network isolation."
            ),
            recommendation=(
                "Remove hostNetwork: true. "
                "Use Kubernetes Services and proper NetworkPolicies for connectivity. "
                "Reserve hostNetwork for DaemonSets that genuinely require node-level network visibility "
                "(e.g. CNI plugins, node monitoring agents)."
            ),
            what_changed=(
                "The diff enables hostNetwork: true in a pod spec, "
                "causing the pod to use the node's network interfaces and bypass pod network isolation."
            ),
            why_dangerous=(
                "With hostNetwork, the pod shares the node's complete network stack. "
                "It can bind to any host port, capture traffic on all node interfaces, "
                "and bypass Kubernetes NetworkPolicies (which only apply to pod network namespaces). "
                "The pod can also reach cloud metadata endpoints directly."
            ),
            attack_path=(
                "1. Attacker gains code execution in the pod. "
                "2. They sniff unencrypted service-to-service traffic on the node's network interfaces. "
                "3. They access cloud metadata (169.254.169.254) to steal IAM credentials. "
                "4. They bind a backdoor listener on a host port, bypassing all Kubernetes network controls."
            ),
            blast_radius=(
                "Node network perimeter fully exposed to the pod. "
                "All unencrypted intra-node traffic readable. "
                "Cloud IMDS credentials accessible → IAM escalation possible. "
                "NetworkPolicy rules ineffective for this pod."
            ),
        ),

        # ── K8S_NET_ADMIN ─────────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*-\s*NET_ADMIN\b",
            severity="HIGH",
            rule_id="K8S_NET_ADMIN",
            category="kubernetes",
            subcategory="capabilities",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
            reason=(
                "Kubernetes container adds the NET_ADMIN Linux capability, "
                "granting broad network administration privileges inside the pod."
            ),
            recommendation=(
                "Remove NET_ADMIN from capabilities.add unless absolutely required. "
                "Drop all capabilities and add back only what is strictly needed:\n"
                "securityContext:\n"
                "  capabilities:\n"
                "    drop: [\"ALL\"]\n"
                "Consider using a dedicated CNI plugin or network operator instead of "
                "granting NET_ADMIN to application containers."
            ),
            what_changed=(
                "The diff adds 'NET_ADMIN' to the container's capabilities.add list in the securityContext."
            ),
            why_dangerous=(
                "NET_ADMIN allows the process to modify network interfaces, routing tables, "
                "firewall rules (iptables/nftables), and ARP tables. "
                "In a Kubernetes environment, this means the container can manipulate "
                "pod network routing to intercept or redirect traffic from other pods on the same node, "
                "or bypass NetworkPolicy rules."
            ),
            attack_path=(
                "1. Attacker gets code execution in the NET_ADMIN-capable container. "
                "2. They modify iptables to redirect traffic from other pods through their container. "
                "3. Service-to-service traffic (including auth tokens in HTTP headers) is intercepted. "
                "4. Credentials harvested from traffic used for lateral movement."
            ),
            blast_radius=(
                "All pods on the same node potentially subject to traffic interception. "
                "NetworkPolicies can be bypassed via iptables manipulation. "
                "Node-level networking can be disrupted."
            ),
        ),

        # ── K8S_SYS_ADMIN ─────────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*-\s*SYS_ADMIN\b",
            severity="CRITICAL",
            rule_id="K8S_SYS_ADMIN",
            category="kubernetes",
            subcategory="capabilities",
            policy_action="BLOCK",
            confidence=0.98,
            reason=(
                "Kubernetes container adds the SYS_ADMIN Linux capability. "
                "SYS_ADMIN is nearly equivalent to full root with no namespace restrictions."
            ),
            recommendation=(
                "Remove SYS_ADMIN from capabilities.add. "
                "This capability is almost never required by application workloads. "
                "If specific functionality needs SYS_ADMIN (e.g. FUSE mounts, cgroup management), "
                "use a dedicated sidecar with a tightly scoped securityContext and OPA/Kyverno policy."
            ),
            what_changed=(
                "The diff adds 'SYS_ADMIN' to the container's capabilities.add list, "
                "granting the container near-complete control over the host kernel."
            ),
            why_dangerous=(
                "SYS_ADMIN grants: mounting filesystems, changing kernel parameters (sysctl), "
                "creating user namespaces, loading eBPF programs, and dozens of other privileged operations. "
                "It is the most dangerous Linux capability and has been used in multiple "
                "container escape CVEs (runc, containerd). "
                "Security research has shown SYS_ADMIN containers can be escaped reliably."
            ),
            attack_path=(
                "1. Container with SYS_ADMIN starts on a Kubernetes node. "
                "2. Attacker exploits app to get shell inside the container. "
                "3. They use SYS_ADMIN to mount the host filesystem via cgroups release_agent trick "
                "   (CVE-2022-0492-style container escape). "
                "4. Full host node compromise without requiring any node vulnerability."
            ),
            blast_radius=(
                "Full Kubernetes node compromise. "
                "All pods on the node, node credentials, and IMDS tokens at risk. "
                "If node has cluster-admin ClusterRoleBinding: full cluster compromise."
            ),
        ),

        # ── K8S_RUN_AS_ROOT ──────────────────────────────────────────────────
        rich_rule(
            pattern=r"(?m)^\+?\s*runAsUser\s*:\s*0\b|^\+?\s*runAsNonRoot\s*:\s*false\b",
            severity="HIGH",
            rule_id="K8S_RUN_AS_ROOT",
            category="kubernetes",
            subcategory="privilege",
            policy_action="REVIEW_REQUIRED",
            confidence=0.95,
            reason=(
                "Kubernetes securityContext configures the container to run as UID 0 (root) "
                "or explicitly allows root execution (runAsNonRoot: false)."
            ),
            recommendation=(
                "Set a non-root runAsUser and enforce runAsNonRoot:\n"
                "securityContext:\n"
                "  runAsNonRoot: true\n"
                "  runAsUser: 10001\n"
                "  runAsGroup: 10001\n"
                "  allowPrivilegeEscalation: false"
            ),
            what_changed=(
                "The diff sets 'runAsUser: 0' or 'runAsNonRoot: false' in a pod or container "
                "securityContext, configuring the container to run processes as root."
            ),
            why_dangerous=(
                "A container running as UID 0 has root inside the container namespace. "
                "If container isolation is breached (breakout, hostPath, sock), "
                "the attacker already has root-level privileges without needing a privilege escalation step. "
                "Kubernetes OPA/Kyverno policies that block root can be bypassed."
            ),
            attack_path=(
                "1. Application vulnerability gives code execution as UID 0 inside the container. "
                "2. Attacker writes to container filesystem paths that may be shared via volumes. "
                "3. If allowPrivilegeEscalation is also true, setuid binaries can escalate further. "
                "4. Combined with any hostPath or privileged mode: node-level compromise."
            ),
            blast_radius=(
                "Container-level: full filesystem write, all application secrets readable. "
                "Node-level (with hostPath/privileged): complete node compromise. "
                "Kubernetes API: if service account token is auto-mounted, RBAC permissions may be exploited."
            ),
        ),
    )

    def analyze(self, text: str, file_path: str = "deployment.yaml") -> list[Finding]:  # type: ignore[override]
        findings = super().analyze(text, file_path=file_path)

        # ── K8S_MISSING_LIMITS ────────────────────────────────────────────────
        if "resources:" in text.lower() or "containers:" in text.lower() or "initcontainers:" in text.lower():
            has_limits = bool(re.search(r"(?m)^\s*limits\s*:", text, re.IGNORECASE))
            if not has_limits:
                findings.append(
                    Finding(
                        severity="MEDIUM",
                        weight=SEVERITY_WEIGHTS["MEDIUM"],
                        rule_id="K8S_MISSING_LIMITS",
                        category="kubernetes",
                        subcategory="resources",
                        policy_action="REVIEW_REQUIRED",
                        confidence=0.85,
                        reason=(
                            "Kubernetes container spec does not define resource limits (CPU/memory). "
                            "The container can consume unlimited node resources."
                        ),
                        recommendation=(
                            "Define resource limits for all containers:\n"
                            "resources:\n"
                            "  limits:\n"
                            "    cpu: \"500m\"\n"
                            "    memory: \"256Mi\"\n"
                            "  requests:\n"
                            "    cpu: \"100m\"\n"
                            "    memory: \"128Mi\""
                        ),
                        evidence={"file": file_path, "matched": "missing resources.limits"},
                        what_changed=(
                            "The diff contains a container spec without a 'limits' block under 'resources'."
                        ),
                        why_dangerous=(
                            "Without resource limits, a container can exhaust all CPU and memory on the node, "
                            "causing an OOMKill of other pods (denial of service) or complete node unresponsiveness. "
                            "This is also a common footprint expansion technique: a cryptominer spawned inside "
                            "an unlimited container consumes the entire node's compute."
                        ),
                        attack_path=(
                            "1. Container is compromised and used to run a CPU/memory-intensive process. "
                            "2. Unlimited resource consumption starves neighboring pods. "
                            "3. Node enters a degraded state — monitoring, logging, and security agents "
                            "   may also be evicted."
                        ),
                        blast_radius=(
                            "All pods on the same node at risk of resource starvation. "
                            "Node autoscaling costs may increase dramatically. "
                            "Cluster stability degraded."
                        ),
                    )
                )

        # ── K8S_MISSING_REQUESTS ─────────────────────────────────────────────
        if "resources:" in text.lower() or "containers:" in text.lower():
            has_requests = bool(re.search(r"(?m)^\s*requests\s*:", text, re.IGNORECASE))
            if not has_requests:
                findings.append(
                    Finding(
                        severity="LOW",
                        weight=SEVERITY_WEIGHTS["LOW"],
                        rule_id="K8S_MISSING_REQUESTS",
                        category="kubernetes",
                        subcategory="resources",
                        policy_action="SAFE",
                        confidence=0.80,
                        reason=(
                            "Kubernetes container spec does not define resource requests (CPU/memory). "
                            "The scheduler cannot make accurate placement decisions."
                        ),
                        recommendation=(
                            "Define resource requests for all containers:\n"
                            "resources:\n"
                            "  requests:\n"
                            "    cpu: \"100m\"\n"
                            "    memory: \"128Mi\""
                        ),
                        evidence={"file": file_path, "matched": "missing resources.requests"},
                        what_changed=(
                            "The diff contains a container spec without a 'requests' block under 'resources'."
                        ),
                        why_dangerous=(
                            "Without requests, the Kubernetes scheduler cannot guarantee sufficient resources "
                            "are available before scheduling the pod. "
                            "Pods may be scheduled on overloaded nodes, leading to degraded performance "
                            "and potential OOMKill events."
                        ),
                        attack_path=(
                            "Availability risk rather than a direct security attack path. "
                            "Resource contention on overloaded nodes can lead to pod eviction, "
                            "which increases the attack surface during recovery."
                        ),
                        blast_radius=(
                            "Application performance and availability impact. "
                            "Autoscaler decisions may be suboptimal."
                        ),
                    )
                )

        return findings
