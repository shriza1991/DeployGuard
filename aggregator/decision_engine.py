from typing import Any, Dict, List
from models import AgentResult, FinalDecision
from utils import deduplicate_list, build_executive_summary, get_utc_now_iso
from logger import logger

# Agent weights for scoring
WEIGHTS = {
    "code-risk": 0.40,
    "infra-risk": 0.35,
    "incident-history": 0.25
}

SEVERITY_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4
}

def check_repeated_production_failures(history_result: Dict[str, Any]) -> bool:
    similar_incidents = history_result.get("similar_incidents", [])
    reasons = history_result.get("reasons", [])
    
    # Heuristics check
    has_production_reason = any("production incidents" in r.lower() for r in reasons)
    
    failure_outcomes = {"production outage", "partial outage", "rollback", "hotfix", "security incident"}
    
    prod_failures_count = 0
    for inc in similar_incidents:
        outcome = str(inc.get("outcome", "")).lower()
        severity = str(inc.get("severity", "")).lower()
        if outcome in failure_outcomes or severity in {"high", "critical"}:
            prod_failures_count += 1
            
    # If we have >= 2 failures, or if we have at least 1 failures and incident-history flagged production reason
    if prod_failures_count >= 2 or (prod_failures_count >= 1 and has_production_reason):
        return True
    return False

def make_decision(correlation_id: str, agent_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    # Calculate score using available agents
    weighted_sum = 0.0
    weight_sum = 0.0
    confidences = []
    
    # Process scores and confidences
    for agent_name, result in agent_results.items():
        if agent_name in WEIGHTS:
            score = result.get("score", 0)
            weight = WEIGHTS[agent_name]
            weighted_sum += score * weight
            weight_sum += weight
            
            # Confidence
            conf = result.get("confidence", 0.0)
            confidences.append(conf)

    if weight_sum > 0:
        overall_score = round(weighted_sum / weight_sum)
    else:
        overall_score = 0

    # Increase score by +10 if historical incidents contain repeated production failures
    history_result = agent_results.get("incident-history")
    has_repeated_failures = False
    if history_result:
        has_repeated_failures = check_repeated_production_failures(history_result)
        if has_repeated_failures:
            overall_score += 10
            overall_score = min(overall_score, 100)
            logger.info(f"Repeated production failures detected. Score increased by +10 to {overall_score}")

    # Determine confidence
    if confidences:
        overall_confidence = round(sum(confidences) / len(confidences), 2)
    else:
        overall_confidence = 0.0

    # Determine decision
    if overall_score >= 60:
        decision = "BLOCK"
    elif overall_score >= 30:
        decision = "REVIEW"
    else:
        decision = "SAFE"

    # Override rules: ANY agent reports severity == CRITICAL -> immediately return BLOCK
    has_critical_override = False
    for agent_name, result in agent_results.items():
        if str(result.get("severity", "")).upper() == "CRITICAL":
            decision = "BLOCK"
            has_critical_override = True
            logger.info(f"Severity CRITICAL detected in {agent_name}. Overriding decision to BLOCK")

    # Determine overall severity based on overall score
    if overall_score >= 85:
        severity = "CRITICAL"
    elif overall_score >= 60:
        severity = "HIGH"
    elif overall_score >= 30:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    # Ensure overall severity matches max agent severity if agent has critical/high
    max_agent_severity_val = 0
    max_agent_severity_str = "LOW"
    for result in agent_results.values():
        agent_sev = str(result.get("severity", "")).lower()
        val = SEVERITY_ORDER.get(agent_sev, 1)
        if val > max_agent_severity_val:
            max_agent_severity_val = val
            max_agent_severity_str = agent_sev.upper()

    # If an agent was critical, final severity should be CRITICAL
    if has_critical_override or max_agent_severity_str == "CRITICAL":
        severity = "CRITICAL"
    elif max_agent_severity_str == "HIGH" and severity not in {"HIGH", "CRITICAL"}:
        severity = "HIGH"

    # Merge reasons and recommendations
    reasons: List[str] = []
    recommendations: List[str] = []
    
    # Sort agents by severity order to merge their reasons
    sorted_agents = sorted(
        agent_results.items(),
        key=lambda item: SEVERITY_ORDER.get(str(item[1].get("severity", "")).lower(), 1),
        reverse=True
    )
    
    for agent_name, result in sorted_agents:
        reasons.extend(result.get("reasons", []))
        recommendations.extend(result.get("recommendations", []))

    reasons = deduplicate_list(reasons)
    recommendations = deduplicate_list(recommendations)

    # Executive summary
    summary = build_executive_summary(agent_results, decision, overall_score)

    return {
        "correlation_id": correlation_id,
        "overall_score": overall_score,
        "overall_confidence": overall_confidence,
        "decision": decision,
        "severity": severity,
        "agents": agent_results,
        "summary": summary,
        "reasons": reasons,
        "recommendations": recommendations,
        "generated_at": get_utc_now_iso()
    }
