from fastapi import APIRouter

router = APIRouter(prefix="/deployments", tags=["Deployments"])

@router.get("/")
def get_deployments():
    return [
        {
            "id": "DEP-101",
            "repository": "DeployGuard",
            "branch": "main",
            "decision": "SAFE",
            "risk_score": 12,
            "confidence": 98.5,
            "timestamp": "2026-07-13T10:30:00Z"
        },
        {
            "id": "DEP-102",
            "repository": "DeployGuard",
            "branch": "feature/auth",
            "decision": "REVIEW",
            "risk_score": 48,
            "confidence": 91.2,
            "timestamp": "2026-07-13T09:45:00Z"
        }
    ]

    @router.get("/metrics")
    def get_metrics():
        return {
            "total": 150,
            "safe": 100,
            "review": 20,
            "blocked": 4,
            "avgRisk": 38,
            "avgConfidence": 94.2,
        }
