from fastapi import APIRouter

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"]
)

@router.get("/")
def get_analytics():
    return {
        "deployment_trend": [
            {"date": "2026-07-10", "count": 12},
            {"date": "2026-07-11", "count": 18},
            {"date": "2026-07-12", "count": 15},
        ],
        "risk_distribution": {
            "safe": 100,
            "review": 20,
            "blocked": 4,
        },
        "average_risk": 38,
        "average_confidence": 94.2,
    }