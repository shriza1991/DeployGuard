"""
analysis/models.py — Typed data contracts for the two-phase pipeline.

Phase 1 populates these models.
Phase 2 (LLM reviewer) consumes them.
Nothing in this module performs I/O or calls an LLM.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Phase 1 output models
# ---------------------------------------------------------------------------

class DiffFile(BaseModel):
    """Represents one file in the unified diff."""

    filename: str
    status: Literal["added", "modified", "deleted", "renamed", "unknown"] = "unknown"
    language: str = "generic"          # set by language_classifier
    additions: int = 0
    deletions: int = 0
    changes: int = 0
    patch: str = ""
    functions_modified: List[str] = Field(default_factory=list)
    imports_added: List[str] = Field(default_factory=list)

    @property
    def added_lines(self) -> int:
        return self.additions

    @property
    def removed_lines(self) -> int:
        return self.deletions

    @property
    def changed_lines(self) -> int:
        return self.changes or (self.additions + self.deletions)

    @property
    def modified_functions(self) -> List[str]:
        return self.functions_modified

    @property
    def imports(self) -> List[str]:
        return self.imports_added



class SecurityFinding(BaseModel):
    """
    One concrete security issue found by a deterministic detector.
    Contains only objective facts — no recommendations or prose.
    """

    rule_id: str
    detector: str                      # "python", "docker", "terraform", …
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    category: str                      # "injection", "secrets", "privilege", …
    file: str
    line_number: Optional[int] = None
    matched_text: str = ""             # the actual line/pattern that matched (≤200 chars)
    confidence: float = 0.9


class RepositoryContextChunk(BaseModel):
    """One semantic-search result from the Repository Context Service."""

    file: str
    lines: str = ""                    # e.g. "12-34"
    similarity: float = 0.0
    reason: str = ""                   # "Exact changed file", "Directory boost", …
    text: str = ""                     # code snippet


class AnalysisReport(BaseModel):
    """
    The complete, structured output of Phase 1.

    Phase 2 receives this object and nothing else.  It never sees the raw
    webhook payload — only the facts extracted here.
    """

    # Repository identity
    repository: str = ""
    branch: str = "main"
    commit: str = ""
    clone_url: str = ""

    # Diff summary
    files_added: List[str] = Field(default_factory=list)
    files_modified: List[str] = Field(default_factory=list)
    files_deleted: List[str] = Field(default_factory=list)

    # Per-file structured detail
    diff_files: List[DiffFile] = Field(default_factory=list)

    # Deterministic findings (from all detectors + existing risk_analyzers)
    findings: List[SecurityFinding] = Field(default_factory=list)

    # Repository semantic context
    repository_context: List[RepositoryContextChunk] = Field(default_factory=list)

    # Aggregated score from existing risk_analyzers (preserves backward compat)
    score: int = 0
    severity: str = "low"
    confidence: float = 0.0

    # Raw legacy output from risk_analyzers (for aggregator compat)
    legacy_reasons: List[str] = Field(default_factory=list)
    legacy_recommendations: List[str] = Field(default_factory=list)
    legacy_deterministic_findings: List[Dict[str, Any]] = Field(default_factory=list)

    # Metrics and summary
    metrics: Dict[str, Any] = Field(default_factory=dict)
    summary: Dict[str, Any] = Field(default_factory=dict)

    # PR / commit metadata (read-only, for context only — never used as a primary risk signal)
    pr_title: str = ""
    pr_description: str = ""
    commit_message: str = ""


# ---------------------------------------------------------------------------
# Phase 2 output models
# ---------------------------------------------------------------------------

class FindingAnalysis(BaseModel):
    """
    Gemini's expert analysis of one SecurityFinding.
    All six questions must be answered — no field may be omitted.
    """

    rule_id: str
    severity: str
    why_dangerous: str          # Q1: practical security implication
    exploitability: str         # Q2: realistic attack scenario
    blast_radius: str           # Q3: systems / services affected
    false_positive_likelihood: str  # Q4: reasoning on FP probability
    block_recommendation: bool  # Q5: should this block deployment?
    remediation: str            # Q6: specific implementation guidance


class ReviewResult(BaseModel):
    """
    The complete output of Phase 2 (LLM review).
    Maps to the existing aggregator-compatible output shape via _to_aggregator_payload().
    """

    executive_summary: str = ""
    deployment_decision: Literal["SAFE", "REVIEW", "BLOCK"] = "REVIEW"

    # One entry per SecurityFinding in the AnalysisReport
    finding_analyses: List[FindingAnalysis] = Field(default_factory=list)

    # Architectural / design observations — clearly distinct from verified findings
    ai_observations: List[str] = Field(default_factory=list)

    # Ordered risk list (most severe first)
    prioritized_risks: List[str] = Field(default_factory=list)

    # Concrete, actionable remediation steps
    remediation_plan: List[str] = Field(default_factory=list)

    # Gemini's self-reported confidence
    confidence: float = 0.0

    # Plain-language explanation of why this confidence level was chosen
    confidence_rationale: str = ""

    # LLM provider metadata
    provider: str = "unavailable"
    available: bool = False
