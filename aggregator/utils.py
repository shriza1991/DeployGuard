from datetime import datetime, timezone
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

def build_executive_summary(
    agents: Dict[str, Dict[str, Any]],
    decision: str,
    overall_score: int
) -> str:
    code_risk = agents.get("code-risk")
    infra_risk = agents.get("infra-risk")
    history_risk = agents.get("incident-history")

    code_reasons = code_risk.get("reasons", []) if code_risk else []
    infra_reasons = infra_risk.get("reasons", []) if infra_risk else []
    history_reasons = history_risk.get("reasons", []) if history_risk else []
    similar_incidents = history_risk.get("similar_incidents", []) if history_risk else []

    app_risks = []
    infra_risks = []
    hist_risks = []

    # Parse code risk
    all_code_text = " ".join(code_reasons).lower()
    if any(k in all_code_text for k in ["auth", "login", "permission", "credential"]):
        app_risks.append("authentication changes")
    if any(k in all_code_text for k in ["database", "migration", "schema", "sql"]):
        app_risks.append("database migrations")
    if any(k in all_code_text for k in ["secret", "key", "password", "token"]):
        app_risks.append("exposed credentials")
    if any(k in all_code_text for k in ["large", "many files", "broad"]):
        app_risks.append("large-scale code updates")
    if not app_risks and code_risk and code_risk.get("score", 0) > 30:
        app_risks.append("elevated code modification anomalies")

    # Parse infra risk
    all_infra_text = " ".join(infra_reasons).lower()
    if any(k in all_infra_text for k in ["privileged", "root", "capabilities"]):
        infra_risks.append("privileged container definitions")
    if any(k in all_infra_text for k in ["cpu", "load"]):
        infra_risks.append("high simulated CPU usage")
    if any(k in all_infra_text for k in ["error rate", "latency", "failure"]):
        infra_risks.append("elevated metrics errors")
    if any(k in all_infra_text for k in ["out of hours", "window", "weekend"]):
        infra_risks.append("deployment time-window risk")
    if not infra_risks and infra_risk and infra_risk.get("score", 0) > 30:
        infra_risks.append("infrastructure heuristic flags")

    # Parse incident history
    all_hist_text = " ".join(history_reasons).lower()
    # Check similar incident outcomes
    outcomes = [str(inc.get("outcome", "")).lower() for inc in similar_incidents]
    severities = [str(inc.get("severity", "")).lower() for inc in similar_incidents]
    
    if any("auth" in o or "auth" in str(inc.get("title", "")).lower() for inc, o in zip(similar_incidents, outcomes)):
        hist_risks.append("authentication failures")
    elif any("rollback" in o for o in outcomes):
        hist_risks.append("deployment rollbacks")
    elif any(o in ["production outage", "partial outage", "outage"] for o in outcomes):
        hist_risks.append("production outages")
    elif similar_incidents:
        hist_risks.append("similar past failures")

    # Build sentences
    sentences = []
    
    risk_level = "elevated"
    if overall_score >= 85:
        risk_level = "critical"
    elif overall_score >= 60:
        risk_level = "high"
    elif overall_score < 30:
        risk_level = "minimal"

    sentences.append(f"The deployment shows {risk_level} application risk.")

    if app_risks:
        sentences.append(f"Application risk factors include {', '.join(app_risks)}.")
    if infra_risks:
        sentences.append(f"Infrastructure analysis detected {', '.join(infra_risks)}.")
    if hist_risks:
        sentences.append(f"Historical incidents indicate similar deployments previously caused {', '.join(hist_risks)}.")
    else:
        if similar_incidents:
            sentences.append("Historical lookup matched past similar incidents.")

    if decision == "BLOCK":
        sentences.append("Rollout is blocked pending risk remediation.")
    elif decision == "REVIEW":
        sentences.append("Manual review is recommended.")
    else:
        sentences.append("Deployment is safe to proceed.")

    return " ".join(sentences)
