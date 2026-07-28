from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SeedIncident:
    incident_id: str
    title: str
    description: str
    severity: str
    outcome: str
    rollback: bool
    duration_minutes: int
    environment: str
    service: str
    root_cause: str
    tags: list[str]
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    impact: str = ""
    resolution: str = ""
    affected_services: list[str] = field(default_factory=list)
    timeline: str = ""
    lessons_learned: str = ""
    preventive_controls: list[str] = field(default_factory=list)

    def search_text(self) -> str:
        parts = [
            self.title,
            self.summary or self.description,
            self.description,
            self.root_cause,
            self.impact,
            self.resolution,
            self.lessons_learned,
            " ".join(self.preventive_controls),
            " ".join(self.tags),
            " ".join(self.affected_services),
        ]
        return " ".join(part for part in parts if part).lower()

    def payload(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "summary": self.summary or self.description,
            "description": self.description,
            "severity": self.severity,
            "outcome": self.outcome,
            "rollback": self.rollback,
            "duration_minutes": self.duration_minutes,
            "environment": self.environment,
            "service": self.service,
            "root_cause": self.root_cause,
            "impact": self.impact,
            "resolution": self.resolution,
            "affected_services": self.affected_services or [self.service],
            "timeline": self.timeline,
            "lessons_learned": self.lessons_learned,
            "preventive_controls": self.preventive_controls,
            "tags": self.tags,
            "created_at": self.created_at,
            "timestamp": self.created_at,
            "metadata": self.metadata,
        }
