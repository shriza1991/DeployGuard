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

    def search_text(self) -> str:
        parts = [
            self.title,
            self.description,
            self.root_cause,
            " ".join(self.tags),
        ]
        return " ".join(part for part in parts if part).lower()

    def payload(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "outcome": self.outcome,
            "rollback": self.rollback,
            "duration_minutes": self.duration_minutes,
            "environment": self.environment,
            "service": self.service,
            "root_cause": self.root_cause,
            "tags": self.tags,
            "created_at": self.created_at,
            "timestamp": self.created_at,
            "metadata": self.metadata,
        }
