from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Pattern


SEVERITY_WEIGHTS = {
    "critical": 25,
    "high": 15,
    "medium": 8,
    "low": 3,
}


@dataclass(frozen=True)
class Finding:
    severity: str
    reason: str
    recommendation: str
    weight: int
    confidence: int = 90
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DetectionRule:
    pattern: Pattern[str]
    severity: str
    reason: str
    recommendation: str
    confidence: int = 90

    def to_finding(self) -> Finding:
        return Finding(
            severity=self.severity,
            weight=SEVERITY_WEIGHTS[self.severity],
            reason=self.reason,
            recommendation=self.recommendation,
            confidence=self.confidence,
        )


class TextAnalyzer:
    name = "base"
    rules: tuple[DetectionRule, ...] = ()

    def analyze(self, text: str) -> list[Finding]:
        findings: list[Finding] = []
        for rule in self.rules:
            if rule.pattern.search(text):
                findings.append(rule.to_finding())
        return findings


def rule(
    pattern: str,
    severity: str,
    reason: str,
    recommendation: str,
    confidence: int = 90,
) -> DetectionRule:
    return DetectionRule(
        pattern=re.compile(pattern, re.IGNORECASE | re.MULTILINE),
        severity=severity,
        reason=reason,
        recommendation=recommendation,
        confidence=confidence,
    )


def dedupe_findings(findings: Iterable[Finding]) -> list[Finding]:
    seen: set[tuple[str, str]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.reason, finding.recommendation)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique
