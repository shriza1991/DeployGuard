from fastapi import APIRouter

# NOTE: These gateway-level stubs exist only so the gateway router includes this
# file without crashing. The real /deployments and /deployments/metrics endpoints
# are served by the Aggregator (port 8002), not the Gateway (port 8000).
# The frontend proxies /api/aggregator/* → aggregator:8002.

router = APIRouter(prefix="/deployments", tags=["Deployments"])


@router.get("/")
def get_deployments():
    """Stub — real data is served by the Aggregator at GET /deployments."""
    return []


@router.get("/metrics")
def get_metrics():
    """Stub — real data is served by the Aggregator at GET /deployments/metrics."""
    return {
        "total": 0,
        "safe": 0,
        "review": 0,
        "blocked": 0,
        "avgRisk": 0,
        "avgConfidence": 0.0,
    }
