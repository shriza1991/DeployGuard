from fastapi import FastAPI

from routers import dashboard,deployments,analytics,incidents,webhook

app = FastAPI(title="DeployGuard Gateway")

app.include_router(webhook.router)
app.include_router(dashboard.router)
app.include_router(deployments.router)
app.include_router(analytics.router)
app.include_router(incidents.router)


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "service": "gateway",
    }