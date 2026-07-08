from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from redis_store import RedisStore
from config import get_settings

router = APIRouter()
redis_store = RedisStore(get_settings())

@router.get("/health")
def health_check():
    return {"status": "healthy"}

@router.get("/decision/{correlation_id}")
def get_decision(correlation_id: str):
    # Check if final decision is available
    decision = redis_store.get_final_decision(correlation_id)
    if decision:
        return decision

    # Check if there are partial results
    results = redis_store.get_agent_results(correlation_id)
    if results:
        return JSONResponse(
            status_code=202,
            content={
                "status": "pending",
                "correlation_id": correlation_id,
                "collected_agents": list(results.keys()),
                "message": "Deployment risk aggregation is in progress."
            }
        )

    raise HTTPException(
        status_code=404,
        detail=f"No deployment found or decision expired for correlation_id: {correlation_id}"
    )
