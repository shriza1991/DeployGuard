from fastapi import APIRouter

router = APIRouter(prefix="/incidents", tags=["Incidents"])

@router.get("/")
def get_incidents():
    return [
        {
            "id": "INC-101",
            "title": "Authentication middleware removed",
            "severity": "CRITICAL",
            "similarity": 94
        }
    ]
