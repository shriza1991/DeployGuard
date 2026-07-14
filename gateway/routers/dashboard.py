from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary")
def get_summary():
    return {
        "total_deployments": 124,
        "safe": 100,
        "review": 20,
        "blocked": 4,
        "avg_risk": 38,
        "avg_confidence": 94.2,
    }