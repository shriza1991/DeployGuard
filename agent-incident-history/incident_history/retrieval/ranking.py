from __future__ import annotations

from datetime import datetime, timezone

from incident_history.models import SimilarIncident

SEVERITY_WEIGHT = {
    "critical": 0.22,
    "high": 0.14,
    "medium": 0.07,
    "low": 0.02,
}

SECURITY_TAGS = {"security", "secrets", "iam", "auth", "authentication", "s3", "container", "supply-chain"}


def rank_incidents(incidents: list[SimilarIncident]) -> list[SimilarIncident]:
    for incident in incidents:
        incident.rank_score = _rank_score(incident)
    return sorted(incidents, key=lambda item: item.rank_score, reverse=True)


def _rank_score(incident: SimilarIncident) -> float:
    score = incident.similarity
    score += SEVERITY_WEIGHT.get(incident.severity, 0.0)
    if incident.environment == "production":
        score += 0.12
    if incident.rollback or "rollback" in incident.outcome:
        score += 0.12
    if incident.severity == "critical":
        score += 0.08
    if SECURITY_TAGS.intersection(set(incident.tags)):
        score += 0.08
    score += _recency_boost(incident.timestamp)
    return score


def _recency_boost(timestamp: str) -> float:
    if not timestamp:
        return 0.0
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).days
    except ValueError:
        return 0.0
    if age_days <= 30:
        return 0.08
    if age_days <= 180:
        return 0.05
    if age_days <= 365:
        return 0.03
    return 0.0

