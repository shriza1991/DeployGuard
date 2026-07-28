from datetime import datetime, timezone
import re
from typing import Any, Dict, List


def get_utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def deduplicate_list(items: List[str]) -> List[str]:
    seen = set()
    deduped = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        normalized = cleaned.lower()
        if normalized not in seen:
            seen.add(normalized)
            deduped.append(cleaned)
    return deduped


def merge_and_condense_recommendations(recs: List[str]) -> List[str]:
    """
    Merge overlapping recommendations into concise, actionable reviewer directives (max 3).
    """
    if not recs:
        return [
            "Validate automated test coverage before proceeding.",
            "Verify configuration values match staging environment.",
            "Ensure standard release monitoring is active.",
        ]

    cleaned = deduplicate_list(recs)
    categories: Dict[str, List[str]] = {
        "k8s": [],
        "docker": [],
        "terraform": [],
        "auth": [],
        "secrets": [],
        "general": [],
    }

    for rec in cleaned:
        rec_lower = rec.lower()
        if any(k in rec_lower for k in ["k8s", "kubernetes", "pod", "hostpath", "hostnetwork", "securitycontext"]):
            categories["k8s"].append(rec)
        elif any(k in rec_lower for k in ["docker", "container", "user root", "latest"]):
            categories["docker"].append(rec)
        elif any(k in rec_lower for k in ["terraform", "s3", "iam", "ingress", "0.0.0.0"]):
            categories["terraform"].append(rec)
        elif any(k in rec_lower for k in ["auth", "token", "jwt", "login"]):
            categories["auth"].append(rec)
        elif any(k in rec_lower for k in ["secret", "aws", "key", "password", "credential"]):
            categories["secrets"].append(rec)
        else:
            categories["general"].append(rec)

    condensed: List[str] = []

    if categories["k8s"]:
        condensed.append(
            "Harden Kubernetes workload definitions by enforcing non-root execution, dropping unused Linux capabilities, and restricting hostPath/hostNetwork access."
        )

    if categories["docker"]:
        condensed.append(
            "Harden Docker container build by switching to an unprivileged user (UID 10001), pinning base images to SHA256 digests, and defining healthchecks."
        )

    if categories["terraform"]:
        condensed.append(
            "Remediate Infrastructure-as-Code definitions by blocking public S3 access, scoping IAM policies to explicit resources, and restricting open ingress CIDRs."
        )

    if categories["secrets"]:
        condensed.append(
            "Purge plaintext credentials from version control, rotate exposed keys immediately, and inject secrets via environment variables or secret managers."
        )

    if categories["auth"]:
        condensed.append(
            "Enforce mandatory authentication guards on all external API endpoints and verify token signature validation."
        )

    if categories["general"]:
        for item in categories["general"]:
            if len(condensed) < 3 and item not in condensed:
                condensed.append(item)

    if not condensed:
        condensed = cleaned[:3]

    return condensed[:3]


def build_executive_summary(
    agents: Dict[str, Dict[str, Any]],
    decision: str,
    overall_score: int
) -> str:
    """
    Generate a 5-sentence final deployment review covering:
    1. Overall deployment health
    2. Major concerns
    3. Historical comparison
    4. Deployment decision
    5. Highest-priority remediation
    """
    code_risk = agents.get("code-risk") or {}
    infra_risk = agents.get("infra-risk") or {}
    history_risk = agents.get("incident-history") or {}

    code_score = code_risk.get("score", 0)
    infra_score = infra_risk.get("score", 0)
    history_score = history_risk.get("score", 0)
    similar_incidents = history_risk.get("similar_incidents", [])

    # Sentence 1: Overall deployment health
    health_label = "healthy"
    if overall_score >= 80:
        health_label = "severely compromised"
    elif overall_score >= 50:
        health_label = "elevated"
    elif overall_score >= 25:
        health_label = "moderate"
    s1 = f"The pull request exhibits an overall risk score of {overall_score}/100, indicating a {health_label} security risk profile."

    # Sentence 2: Major concerns
    concerns = []
    if code_score >= 40:
        concerns.append("application code vulnerabilities")
    if infra_score >= 40:
        concerns.append("infrastructure specification misconfigurations")
    if not concerns:
        concerns.append("baseline change risk")
    s2 = f"Primary security concerns originate from {', '.join(concerns)}."

    # Sentence 3: Historical comparison
    if similar_incidents:
        top_inc = similar_incidents[0]
        inc_title = top_inc.get("title") or "past production outage"
        s3 = f"Historical retrieval matched {len(similar_incidents)} similar production event(s), most notably '{inc_title}'."
    else:
        s3 = "Historical incident retrieval identified zero matching past production outages for this change pattern."

    # Sentence 4: Deployment decision
    if decision == "BLOCK":
        s4 = "Based on policy evaluation, the deployment decision is BLOCK pending resolution of critical findings."
    elif decision == "REVIEW":
        s4 = "Based on policy evaluation, the deployment decision is REVIEW requiring senior engineering sign-off."
    else:
        s4 = "Based on policy evaluation, the deployment decision is PROCEED as no blocking security risks were detected."

    # Sentence 5: Highest-priority remediation
    if overall_score >= 60 or decision in {"BLOCK", "REVIEW"}:
        s5 = "The highest-priority remediation is to resolve identified privilege escalation and access control findings prior to production release."
    else:
        s5 = "No blocking remediation is required; standard release monitoring and automated tests should be enforced."

    return f"{s1} {s2} {s3} {s4} {s5}"
