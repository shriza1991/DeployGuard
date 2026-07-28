from __future__ import annotations

from incident_history.models import SimilarIncident

SEVERITY_WEIGHT = {
    "critical": 0.08,
    "high": 0.04,
    "medium": 0.02,
    "low": 0.0,
}


def rank_incidents(incidents: list[SimilarIncident], query_text: str = "") -> list[SimilarIncident]:
    """
    Simplified 3-signal explainable ranking:
    1. Semantic similarity (primary weight)
    2. Category / tag overlap (contextual alignment boost)
    3. Severity weighting (prioritizing critical/high events)
    """
    query_lower = query_text.lower() if query_text else ""
    for incident in incidents:
        incident.rank_score = _rank_score(incident, query_lower)

    return sorted(incidents, key=lambda item: item.rank_score, reverse=True)


def _rank_score(incident: SimilarIncident, query_lower: str) -> float:
    # Signal 1: Semantic similarity (primary)
    score = incident.similarity

    # Signal 2: Category / tag overlap boost
    if query_lower and incident.tags:
        matching_tags = sum(1 for tag in incident.tags if tag.lower() in query_lower)
        if matching_tags > 0:
            score += min(0.10, matching_tags * 0.03)

    # Signal 3: Severity weighting
    score += SEVERITY_WEIGHT.get(incident.severity.lower(), 0.0)

    return round(score, 4)
