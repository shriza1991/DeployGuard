from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class LLMResult(BaseModel):
    provider: Optional[str] = "unavailable"
    available: Optional[bool] = False
    summary: Optional[str] = ""
    risk_reasoning: Optional[List[str]] = Field(default_factory=list)
    recommendations: Optional[List[str]] = Field(default_factory=list)
    confidence: Optional[float] = 0.0

class AgentResult(BaseModel):
    agent: str
    correlation_id: str
    score: int
    severity: str
    confidence: float
    reasons: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    similar_incidents: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    llm: Optional[LLMResult] = None

class FinalDecision(BaseModel):
    correlation_id: str
    overall_score: int
    overall_confidence: float
    decision: str
    severity: str
    agents: Dict[str, Dict[str, Any]]
    summary: str
    reasons: List[str]
    recommendations: List[str]
    generated_at: str
