"""
infra_risk.analyzers.base
~~~~~~~~~~~~~~~~~~~~~~~~~
Core primitives shared by all infrastructure security analyzers.

Changes vs. original:
  - Finding gains four rich-context fields:
      what_changed, why_dangerous, attack_path, blast_radius
  - to_dict() surfaces all new fields so the aggregator receives them.
  - RichRule replaces DetectionRule for rules that embed contextual prose
    inline (no separate JSON corpus needed).
  - dedupe key now considers (rule_id, file_path) so the same rule can fire
    once per file in a multi-file PR.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Pattern


SEVERITY_WEIGHTS = {
    "critical": 35,
    "high": 20,
    "medium": 8,
    "low": 3,
    "CRITICAL": 35,
    "HIGH": 20,
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

    # Rich contextual fields (empty string = not applicable)
    what_changed: str = ""
    why_dangerous: str = ""
    attack_path: str = ""
    blast_radius: str = ""

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
            # Rich fields
            "what_changed": self.what_changed,
            "why_dangerous": self.why_dangerous,
            "attack_path": self.attack_path,
            "blast_radius": self.blast_radius,
        }


@dataclass(frozen=True)
class RichRule:
    """
    A detection rule that carries full contextual prose in addition to the
    regex pattern.  Every field is embedded in the rule definition so that
    findings never need an external corpus.
    """
    pattern: Pattern[str]
    severity: str
    rule_id: str
    category: str
    subcategory: str
    policy_action: str
    confidence: float

    # Human-readable finding text
    reason: str
    recommendation: str

    # Rich contextual fields
    what_changed: str = ""
    why_dangerous: str = ""
    attack_path: str = ""
    blast_radius: str = ""

    def match(self, text: str) -> re.Match[str] | None:
        return self.pattern.search(text)

    def to_finding(
        self,
        matched_text: str = "",
        file_path: str = "",
        line_num: int | None = None,
    ) -> Finding:
        ev: dict[str, Any] = {}
        if file_path:
            ev["file"] = file_path
        if line_num is not None:
            ev["line"] = line_num
        if matched_text:
            ev["matched"] = matched_text[:200]

        return Finding(
            severity=self.severity,
            weight=SEVERITY_WEIGHTS.get(self.severity.lower(), 5),
            reason=self.reason,
            recommendation=self.recommendation,
            rule_id=self.rule_id,
            category=self.category,
            subcategory=self.subcategory,
            policy_action=self.policy_action,
            confidence=self.confidence,
            evidence=ev,
            what_changed=self.what_changed,
            why_dangerous=self.why_dangerous,
            attack_path=self.attack_path,
            blast_radius=self.blast_radius,
        )


# ---------------------------------------------------------------------------
# Legacy DetectionRule kept for backward-compatibility with any caller that
# still uses it.  New rules should use RichRule.
# ---------------------------------------------------------------------------

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
        ev: dict[str, Any] = {}
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


def rich_rule(
    pattern: str,
    severity: str,
    rule_id: str,
    category: str,
    subcategory: str,
    policy_action: str,
    confidence: float,
    reason: str,
    recommendation: str,
    what_changed: str = "",
    why_dangerous: str = "",
    attack_path: str = "",
    blast_radius: str = "",
) -> RichRule:
    return RichRule(
        pattern=re.compile(pattern, re.IGNORECASE | re.MULTILINE),
        severity=severity,
        rule_id=rule_id,
        category=category,
        subcategory=subcategory,
        policy_action=policy_action,
        confidence=confidence,
        reason=reason,
        recommendation=recommendation,
        what_changed=what_changed,
        why_dangerous=why_dangerous,
        attack_path=attack_path,
        blast_radius=blast_radius,
    )


# ---------------------------------------------------------------------------
# Legacy rule() factory kept for backward-compatibility.
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Base analyzer mixin used by all per-category analyzers.
# ---------------------------------------------------------------------------

class TextAnalyzer:
    """
    Base mixin.  Subclasses populate ``rich_rules`` (preferred) and/or
    the legacy ``rules`` tuple.  ``analyze()`` runs both sets.
    """
    name = "base"
    rich_rules: tuple[RichRule, ...] = ()
    rules: tuple[DetectionRule, ...] = ()

    def analyze(self, text: str, file_path: str = "") -> list[Finding]:
        findings: list[Finding] = []
        lines = text.splitlines()

        for rr in self.rich_rules:
            match = rr.match(text)
            if match:
                matched_str = match.group(0).strip()
                matched_line: int | None = None
                for idx, line in enumerate(lines, 1):
                    if matched_str and matched_str in line:
                        matched_line = idx
                        break
                findings.append(rr.to_finding(matched_text=matched_str, file_path=file_path, line_num=matched_line))

        for rule_obj in self.rules:
            match = rule_obj.pattern.search(text)
            if match:
                matched_str = match.group(0).strip()
                matched_line = None
                for idx, line in enumerate(lines, 1):
                    if matched_str and (matched_str in line or rule_obj.pattern.search(line)):
                        matched_line = idx
                        break
                findings.append(rule_obj.to_finding(matched_text=matched_str, file_path=file_path, line_num=matched_line))

        return findings


def dedupe_findings(findings: Iterable[Finding]) -> list[Finding]:
    """De-duplicate findings.  Same rule may fire once per unique file."""
    seen: set[tuple[str, str]] = set()
    unique: list[Finding] = []
    for finding in findings:
        file_path = str(finding.evidence.get("file", ""))
        key = (finding.rule_id, file_path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique
