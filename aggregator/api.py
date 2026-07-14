from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse
from redis_store import RedisStore
from config import get_settings
from typing import Optional, List, Dict
from models import (
    CreateIncidentRequest,
    SimilaritySearchRequest,
    LLMResult,
    AgentResult,
    FinalDecision,
)

router = APIRouter()
@router.get("/test123")
def test123():
    return {"ok": True}
redis_store = RedisStore(get_settings())

# Health endpoint
@router.get("/health")
def health_check():
    return {"status": "healthy"}

# Decision endpoint
@router.get("/decision/{correlation_id}")
def get_decision(correlation_id: str):
    if correlation_id == "blk001":
        return {
            "correlation_id": correlation_id,
            "overall_score": 85,
            "overall_confidence": 92.5,
            "decision": "BLOCK",
            "severity": "HIGH",
            "summary": "High risk detected in payments-api",
            "reasons": [
                "Potential security vulnerability found"
            ],
            "recommendations": [
                "Conduct a thorough security review"
            ],
            "generated_at": "2026-07-13T11:20:00Z",
            "agents": {
                "code_risk": {
                    "agent": "code_risk",
                    "correlation_id": correlation_id,
                    "score": 85,
                    "severity": "HIGH",
                    "confidence": 93.4,
                    "reasons": [
                        "Authentication middleware removed"
                    ],
                    "recommendations": [
                        "Restore authentication checks"
                    ],
                    "metadata": {},
                    "similar_incidents": [],
                    "llm": None
                },
                "infra_risk": {
                    "agent": "infra_risk",
                    "correlation_id": correlation_id,
                    "score": 78,
                    "severity": "MEDIUM",
                    "confidence": 89.1,
                    "reasons": [
                        "Security group allows broad ingress"
                    ],
                    "recommendations": [
                        "Restrict inbound access"
                    ],
                    "metadata": {},
                    "similar_incidents": [],
                    "llm": None
                }
            }
        }

    ...
    raise HTTPException(
        status_code=404,
        detail=f"No deployment found or decision expired for correlation_id: {correlation_id}",
    )

# Deployments list
@router.get("/deployments")
def list_deployments(
    project: Optional[str] = None,
    since: Optional[str] = None,
    decision: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    # Dummy static data matching frontend contract
    items = [
        {
            "correlation_id": "abc123",
            "repository": "DeployGuard",
            "branch": "main",
            "decision": "SAFE",
            "overall_score": 18,
            "overall_confidence": 96.4,
            "severity": "LOW",
            "generated_at": "2026-07-13T10:30:00Z",
            "status": "complete",
        },
        {
            "correlation_id": "xyz789",
            "repository": "auth-service",
            "branch": "feature/login",
            "decision": "REVIEW",
            "overall_score": 57,
            "overall_confidence": 89.1,
            "severity": "MEDIUM",
            "generated_at": "2026-07-13T09:45:00Z",
            "status": "pending",
        },
        {
            "correlation_id": "blk001",
            "repository": "payments-api",
            "branch": "release/v1",
            "decision": "BLOCK",
            "overall_score": 85,
            "overall_confidence": 92.5,
            "severity": "HIGH",
            "generated_at": "2026-07-13T11:20:00Z",
            "status": "complete",
        },
    ]
    # Apply optional filters (simple stub)
    filtered = items
    if decision:
        filtered = [d for d in filtered if d["decision"] == decision]
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": filtered[start:end],
        "page": page,
        "page_size": page_size,
        "total": total,
    }
    
    
@router.get("/deployments/metrics")
def get_deployment_metrics(
    project: str | None = None,
    period: str | None = "24h"
):
    return {
        "total": 42,
        "safe": 28,
        "review": 8,
        "blocked": 6,
        "avgRisk": 54,
        "avgConfidence": 91,
        "safePercentage": 66.7,
        "blockedPercentage": 14.3,
        "totalProgress": 18,
        "totalTrend": "up",
        "riskLevel": "MEDIUM"
    }



# Single deployment detail
@router.get("/deployments/{correlation_id}")
def get_deployment(correlation_id: str):
    # Reuse static data from list_deployments for consistency
    deployment_map = {
       "abc123": {
    "correlation_id": "abc123",
    "repository": "DeployGuard",
    "branch": "main",

    "commit_message": "Refactor deployment metrics aggregation and improve API response caching",
    "author": "Sarah Williams",
    "pull_request_title": "Optimize deployment metrics pipeline",
    "pull_request_body": "Improves dashboard performance by optimizing metrics aggregation and introducing response caching. No security-sensitive changes detected.",

    "decision": "SAFE",
    "overall_score": 18,
    "overall_confidence": 96.4,
    "severity": "LOW",
    "generated_at": "2026-07-13T10:30:00Z",
    "status": "complete",

    "summary": "Deployment approved. All AI agents reported low deployment risk with no significant security concerns.",

    "reasons": [
        "No high-risk code modifications detected.",
        "Infrastructure configuration remained unchanged.",
        "No similar historical incidents found."
    ],

    "recommendations": [
        "Deployment can proceed.",
        "Continue standard post-deployment monitoring."
    ],

    "agents": {
        "code-risk": {
            "score": 12,
            "confidence": 0.98,
            "reasons": [
                "Static analysis found no critical vulnerabilities.",
                "Code quality checks passed successfully."
            ],
            "recommendations": [
                "No action required."
            ]
        },
        "infra-risk": {
            "score": 20,
            "confidence": 0.95,
            "reasons": [
                "Infrastructure configuration is secure.",
                "No risky Terraform or Docker changes detected."
            ],
            "recommendations": [
                "No action required."
            ]
        },
        "incident-history": {
            "score": 15,
            "confidence": 0.97,
            "reasons": [
                "No historical incidents closely match this deployment."
            ],
            "recommendations": [
                "Proceed with deployment."
            ]
        }
    }
},
        "blk001": {
    "correlation_id": "blk001",
    "repository": "payments-api",
    "branch": "release/v1",

    "commit_message": "Fix payment authorization race condition",
    "author": "Jane Doe",
    "pull_request_title": "Harden payment authorization flow",
    "pull_request_body": "Adds retry logic and validation improvements.",

    "decision": "BLOCK",
    "overall_score": 85,
    "overall_confidence": 92.5,
    "severity": "HIGH",
    "generated_at": "2026-07-13T11:20:00Z",
    "status": "complete",

    "summary": "Deployment blocked due to multiple high-risk findings from AI agents.",

    "reasons": [
        "Authentication validation removed.",
        "Critical IAM permission changes detected."
    ],

    "recommendations": [
        "Restore authentication middleware.",
        "Review IAM policy before deployment."
    ],

    "agents": {
        "code-risk": {
            "score": 82,
            "confidence": 0.94,
            "reasons": [
                "Authentication logic removed."
            ],
            "recommendations": [
                "Restore authentication middleware."
            ]
        },
        "infra-risk": {
            "score": 88,
            "confidence": 0.91,
            "reasons": [
                "Terraform exposes privileged resource."
            ],
            "recommendations": [
                "Restrict infrastructure permissions."
            ]
        },
        "incident-history": {
            "score": 76,
            "confidence": 0.89,
            "reasons": [
                "Similar deployment previously caused outage."
            ],
            "recommendations": [
                "Review incident INC-104 before deployment."
            ]
        }
    }
}
    ,
    "xyz789": {
    "correlation_id": "xyz789",
    "repository": "auth-service",
    "branch": "feature/login",

    "commit_message": "Temporarily disable MFA validation for login flow debugging",
    "author": "Alex Johnson",
    "pull_request_title": "Improve login authentication diagnostics",
    "pull_request_body": "Adds additional authentication logging and temporarily bypasses MFA validation for debugging in the staging environment.",

    "decision": "REVIEW",
    "overall_score": 57,
    "overall_confidence": 89.1,
    "severity": "MEDIUM",
    "generated_at": "2026-07-13T09:45:00Z",
    "status": "pending",

    "summary": "Deployment requires manual review due to authentication changes and elevated infrastructure risk.",

    "reasons": [
        "Authentication validation logic modified.",
        "Infrastructure configuration changed.",
        "Historical incidents indicate similar deployments required rollback."
    ],

    "recommendations": [
        "Perform manual security review before deployment.",
        "Validate authentication flow in staging.",
        "Review infrastructure configuration changes."
    ],

    "agents": {
        "code-risk": {
            "score": 61,
            "confidence": 0.91,
            "reasons": [
                "Authentication validation logic was modified.",
                "Login flow security checks require verification."
            ],
            "recommendations": [
                "Restore production authentication safeguards.",
                "Increase unit test coverage for authentication."
            ]
        },
        "infra-risk": {
            "score": 53,
            "confidence": 0.87,
            "reasons": [
                "Infrastructure configuration changes detected.",
                "Deployment modifies ingress rules."
            ],
            "recommendations": [
                "Review Terraform changes before deployment.",
                "Verify network policies."
            ]
        },
        "incident-history": {
            "score": 58,
            "confidence": 0.89,
            "reasons": [
                "Similar authentication deployments previously caused production instability."
            ],
            "recommendations": [
                "Review incident INC-104 before deployment.",
                "Run additional regression tests."
            ]
        }
    }
},
    }
    if correlation_id in deployment_map:
        return deployment_map[correlation_id]
    raise HTTPException(status_code=404, detail="Deployment not found")

# Deployment timeline
@router.get("/deployments/{correlation_id}/timeline")
def get_deployment_timeline(correlation_id: str):
    # Static timeline for demo purposes
    return {
        "correlation_id": correlation_id,
        "stages": [
            {"id": "trigger", "label": "Trigger", "status": "completed", "timestamp": "2026-07-13T10:30:00Z", "details": "Webhook received"},
            {"id": "code-analysis", "label": "Code Analysis", "status": "completed", "timestamp": "2026-07-13T10:30:05Z", "details": "Static analysis completed"},
            {"id": "infra-scan", "label": "Infra Scan", "status": "pending", "timestamp": None, "details": "Waiting for infra agent"},
            {"id": "incident-check", "label": "Incident Check", "status": "pending", "timestamp": None, "details": "Waiting for history agent"},
            {"id": "decision", "label": "Decision", "status": "pending", "timestamp": None, "details": "Aggregating results"},
        ],
    }
    
# Agent status
@router.get("/agents/status")
def get_agent_status():
    return {
        "agents": [
            {"name": "Code Risk Agent", "status": "online", "latency_ms": 120, "region": "local"},
            {"name": "Infra Risk Agent", "status": "online", "latency_ms": 98, "region": "local"},
            {"name": "Incident History Agent", "status": "online", "latency_ms": 145, "region": "local"},
        ]
    }

# Incidents list (paginated) – matches frontend PaginatedResponse<IncidentRecord>
@router.get("/incidents")
def list_incidents(
    service: Optional[str] = None,
    severity: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    items = [
        {
            "incident_id": "INC-104",
            "title": "Database connection timeout",
            "description": "Customers reported 502 errors after deployment.",
            "severity": "high",
            "outcome": "Rollback completed successfully",
            "service": "inventory-service",
            "environment": "production",
            "root_cause": "Database connection pool exhaustion",
            "rollback": True,
            "timestamp": "2026-07-12T16:00:00Z",
            "tags": ["database", "rollback"],
            "metadata": {},
        }
    ]
    filtered = items
    if service:
        filtered = [i for i in filtered if i["service"] == service]
    if severity:
        filtered = [i for i in filtered if i["severity"] == severity]
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    return {"items": filtered[start:end], "page": page, "page_size": page_size, "total": total}

# Single incident detail
@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    # Return static incident matching the ID if known
    if incident_id == "INC-104":
        return {
            "incident_id": "INC-104",
            "title": "Database connection timeout",
            "description": "Customers reported 502 errors after deployment.",
            "severity": "high",
            "outcome": "Rollback completed successfully",
            "service": "inventory-service",
            "environment": "production",
            "root_cause": "Database connection pool exhaustion",
            "rollback": True,
            "timestamp": "2026-07-12T16:00:00Z",
            "tags": ["database", "rollback"],
            "metadata": {},
        }
    raise HTTPException(status_code=404, detail="Incident not found")

# Create incident (POST)
@router.post("/incidents")
def create_incident(request: CreateIncidentRequest):
    incident = {
        "incident_id": "INC-105",
        "title": request.title,
        "description": request.description,
        "severity": request.severity,
        "outcome": request.outcome,
        "service": request.service,
        "environment": request.environment,
        "root_cause": request.root_cause,
        "rollback": request.rollback,
        "timestamp": "2026-07-13T12:30:00Z",
        "tags": request.tags or [],
        "metadata": {},
    }
    return {"incident": incident}

# Similarity search (POST)
@router.post("/incidents/similarity")
def similarity_search(request: SimilaritySearchRequest):
    matches = [
        {
            "incident_id": "INC-104",
            "title": "Database connection timeout",
            "description": "Customers reported 502 errors after the recent deployment",
            "severity": "high",
            "outcome": "Rollback completed",
            "service": "inventory-service",
            "environment": "production",
            "similarity": 0.92,
            "timestamp": "2026-07-12T16:00:00Z",
            "root_cause": "Connection pool exhausted",
            "rollback": True,
        },
        {
            "incident_id": "INC-105",
            "title": "Authentication service failing",
            "description": "Users unable to login, 401 errors in logs",
            "severity": "critical",
            "outcome": "Rollback completed",
            "service": "auth-service",
            "environment": "production",
            "similarity": 0.88,
            "timestamp": "2026-07-13T09:30:00Z",
            "root_cause": "Token validation service down",
            "rollback": False,
        },
    ]
    return {"query": request.text, "matches": matches}

# Analytics summary – return numeric values
@router.get("/analytics/summary")
def get_analytics_summary():
    return {
        "totalAnalyzed": 43,
        "avgRiskScore": 55,
        "avgConfidence": 75,
        "totalBlocked": 10,
        "trends": {
            "totalAnalyzed": {"value": 44, "trend": "up"},
            "avgRiskScore": {"value": 55, "trend": "down"},
            "avgConfidence": {"value": 75, "trend": "up"},
            "totalBlocked": {"value": 10, "trend": "down"},
        },
    }

# Analytics volume
@router.get("/analytics/volume")
def get_analytics_volume():
    return {
        "range": "7d",
        "data": [
            {"date": "2026-07-07", "safe": 120, "review": 20, "blocked": 10},
            {"date": "2026-07-08", "safe": 130, "review": 15, "blocked": 5},
        ],
    }

# Analytics decisions distribution
@router.get("/analytics/decisions")
def get_analytics_decisions():
    return {
        "range": "7d",
        "distribution": {"SAFE": 120, "REVIEW": 20, "BLOCK": 10},
    }

# Analytics blocks – recent high‑risk blocked deployments
@router.get("/analytics/blocks")
def get_analytics_blocks(
    range: Optional[str] = None,
    severity: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
):
    # Dummy block records aligned with the deployment data above
    all_items = [
        {
            "correlation_id": "blk001",
            "time": "2026-07-13T11:20:00Z",
            "repository": "payments-api",
            "risk_score": 85,
            "primary_threat": "HIGH",
            "decision": "BLOCK",
            "agent_scores": {"code_risk": 85, "infra_risk": 78, "incident_risk": 82},
            "details": "Deployment blocked due to high overall risk identified across multiple AI agents.",
            "recommendations": [
                "Fix authentication logic.",
                "Harden infrastructure configuration.",
                "Review similar incidents before redeployment.",
            ],
        }
    ]
    # Apply simple filters (stub)
    filtered = all_items
    if severity:
        filtered = [i for i in filtered if i["primary_threat"] == severity]
    if search:
        filtered = [i for i in filtered if search.lower() in i["repository"].lower()]
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": filtered[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

# Analytics export — CSV download
@router.get("/analytics/export")
def export_analytics(format: str = "csv", range: Optional[str] = None):
    """Return analytics data as CSV. Currently returns a simple static CSV matching summary metrics."""
    import io
    csv_header = "totalAnalyzed,avgRiskScore,avgConfidence,totalBlocked\n"
    csv_data = f"{44},{55},{75},{10}\n"
    csv_content = csv_header + csv_data
    return StreamingResponse(io.StringIO(csv_content), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=analytics.csv"})


