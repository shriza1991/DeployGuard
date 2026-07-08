from __future__ import annotations

import logging
import threading

from fastapi import FastAPI

from incident_history.service import IncidentHistoryService

logger = logging.getLogger("incident-history-agent")


def create_health_app(service: IncidentHistoryService) -> FastAPI:
    app = FastAPI(title="DeployGuard Incident History Agent")

    @app.get("/health")
    def health() -> dict[str, object]:
        qdrant_available = False
        try:
            qdrant_available = service.vector_store.health_check()
        except Exception:
            qdrant_available = False
        return {
            "status": "ok",
            "agent": "incident-history",
            "qdrant_available": qdrant_available,
            "embedding_provider": getattr(service.embedding_provider, "name", "unknown"),
            "llm_provider": getattr(service.llm_reasoner.provider, "name", "unknown"),
        }

    return app


def start_health_server(service: IncidentHistoryService, host: str, port: int) -> None:
    try:
        import uvicorn
    except ImportError:
        logger.warning("uvicorn is unavailable; health endpoint disabled")
        return

    app = create_health_app(service)

    def _run() -> None:
        uvicorn.run(app, host=host, port=port, log_level="warning")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

