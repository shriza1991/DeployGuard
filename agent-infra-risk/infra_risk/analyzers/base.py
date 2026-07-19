from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Pattern


SEVERITY_WEIGHTS = {
    "critical": 25,
    "high": 15,
    "medium": 8,
    "low": 3,
    "CRITICAL": 25,
    "HIGH": 15,
    "MEDIUM": 8,
    "LOW": 3,
}


@dataclass(frozen=True)
class Finding:
    severity: str
    reason: str
    recommendation: str
    weight: int
    rule_id: str = "GENERIC_RULE"
    category: str = "general"
    subcategory: str = "uncategorized"
    policy_action: str = "SAFE"
    confidence: float = 0.90
    evidence: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "rule_id": self.rule_id,
            "severity": self.severity.upper(),
            "policy_action": self.policy_action,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "description": self.reason,
            "recommendation": self.recommendation,
            "reason": self.reason,
            "weight": self.weight,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class DetectionRule:
    pattern: Pattern[str]
    severity: str
    reason: str
    recommendation: str
    rule_id: str = "GENERIC_RULE"
    category: str = "general"
    subcategory: str = "uncategorized"
    policy_action: str = "SAFE"
    confidence: float = 0.90

    def to_finding(self, matched_text: str = "", file_path: str = "", line_num: int | None = None) -> Finding:
        ev = {}
        if file_path:
            ev["file"] = file_path
        if line_num is not None:
            ev["line"] = line_num
        if matched_text:
            ev["matched"] = matched_text[:200]

        return Finding(
            severity=self.severity,
            weight=SEVERITY_WEIGHTS.get(self.severity, 5),
            reason=self.reason,
            recommendation=self.recommendation,
            rule_id=self.rule_id,
            category=self.category,
            subcategory=self.subcategory,
            policy_action=self.policy_action,
            confidence=self.confidence,
            evidence=ev,
        )


class TextAnalyzer:
    name = "base"
    rules: tuple[DetectionRule, ...] = ()

    def analyze(self, text: str, file_path: str = "") -> list[Finding]:
        findings: list[Finding] = []
        lines = text.splitlines()
        for rule_obj in self.rules:
            match = rule_obj.pattern.search(text)
            if match:
                matched_str = match.group(0).strip()
                matched_line = None
                for idx, line in enumerate(lines, 1):
                    if matched_str in line or rule_obj.pattern.search(line):
                        matched_line = idx
                        break
                findings.append(rule_obj.to_finding(matched_text=matched_str, file_path=file_path, line_num=matched_line))
        return findings


def rule(
    pattern: str,
    severity: str,
    reason: str,
    recommendation: str,
    rule_id: str = "GENERIC_RULE",
    category: str = "general",
    subcategory: str = "uncategorized",
    policy_action: str = "SAFE",
    confidence: float = 0.90,
) -> DetectionRule:
    return DetectionRule(
        pattern=re.compile(pattern, re.IGNORECASE | re.MULTILINE),
        severity=severity,
        reason=reason,
        recommendation=recommendation,
        rule_id=rule_id,
        category=category,
        subcategory=subcategory,
        policy_action=policy_action,
        confidence=confidence,
    )


def dedupe_findings(findings: Iterable[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.rule_id, finding.reason, finding.recommendation)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique

