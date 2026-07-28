from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class IncidentDocument:
    incident_id: str
    title: str
    description: str
    severity: str = "medium"
    outcome: str = ""
    service: str = ""
    root_cause: str = ""
    environment: str = ""
    duration_minutes: int | None = None
    rollback: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)

    def payload(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "outcome": self.outcome,
            "service": self.service,
            "root_cause": self.root_cause,
            "environment": self.environment,
            "duration_minutes": self.duration_minutes,
            "rollback": self.rollback,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class SimilarIncident:
    incident_id: str
    similarity: float
    severity: str
    outcome: str
    title: str
    description: str = ""
    service: str = ""
    environment: str = ""
    rollback: bool = False
    root_cause: str = ""
    timestamp: str = ""
    summary: str = ""
    impact: str = ""
    resolution: str = ""
    lessons_learned: str = ""
    preventive_controls: list[str] = field(default_factory=list)
    affected_services: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    rank_score: float = 0.0

    @classmethod
    def from_qdrant_hit(cls, hit: dict[str, Any]) -> "SimilarIncident":
        payload = hit.get("payload") or {}
        return cls(
            incident_id=str(payload.get("incident_id") or hit.get("id") or ""),
            similarity=float(hit.get("score", 0.0) or 0.0),
            severity=str(payload.get("severity") or "unknown").lower(),
            outcome=str(payload.get("outcome") or "").lower(),
            title=str(payload.get("title") or ""),
            description=str(payload.get("description") or ""),
            service=str(payload.get("service") or ""),
            environment=str(payload.get("environment") or "").lower(),
            rollback=bool(payload.get("rollback", False)),
            root_cause=str(payload.get("root_cause") or ""),
            timestamp=str(payload.get("timestamp") or ""),
            summary=str(payload.get("summary") or payload.get("description") or ""),
            impact=str(payload.get("impact") or ""),
            resolution=str(payload.get("resolution") or ""),
            lessons_learned=str(payload.get("lessons_learned") or ""),
            preventive_controls=[str(c) for c in payload.get("preventive_controls", [])] if isinstance(payload.get("preventive_controls"), list) else [],
            affected_services=[str(s) for s in payload.get("affected_services", [])] if isinstance(payload.get("affected_services"), list) else [],
            tags=[str(tag).lower() for tag in payload.get("tags", []) if str(tag).strip()],
            metadata=payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        )

    def output(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "similarity": round(self.similarity, 3),
            "severity": self.severity,
            "outcome": self.outcome,
            "title": self.title,
            "root_cause": self.root_cause,
            "impact": self.impact,
            "resolution": self.resolution,
        }


@dataclass
class LLMResult:
    provider: str
    available: bool
    summary: str
    risk_reasoning: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    executive_summary: str = ""
    common_failure_pattern: str = ""
    risk_comparison: str = ""
    historical_recommendations: list[str] = field(default_factory=list)

    def output(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "available": self.available,
            "summary": self.summary,
            "risk_reasoning": self.risk_reasoning,
            "recommendations": self.recommendations,
            "confidence": max(0.0, min(1.0, float(self.confidence))),
            "executive_summary": self.executive_summary or self.summary,
            "common_failure_pattern": self.common_failure_pattern,
            "risk_comparison": self.risk_comparison,
            "historical_recommendations": self.historical_recommendations or self.recommendations,
        }
