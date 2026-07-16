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
        import time
        qdrant_available = False
        try:
            qdrant_available = service.vector_store.health_check()
        except Exception:
            qdrant_available = False
            
        uptime = time.time() - service.start_time
        avg_latency = (service.total_latency_ms / service.analysis_count) if service.analysis_count > 0 else 0.0
        avg_confidence = (service.total_confidence / service.analysis_count) if service.analysis_count > 0 else 0.0

        mem_mb = None
        try:
            import resource
            mem_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        except Exception:
            pass

        return {
            "status": "ok",
            "agent": "incident-history",
            "qdrant_available": qdrant_available,
            "embedding_provider": getattr(service.embedding_provider, "name", "unknown"),
            "llm_provider": getattr(service.llm_reasoner.provider, "name", "unknown"),
            "version": service.version,
            "uptime": uptime,
            "analysis_count": service.analysis_count,
            "last_run_timestamp": service.last_run_timestamp,
            "average_latency_ms": avg_latency,
            "average_confidence": avg_confidence,
            "cpu_usage": None,
            "memory_usage": mem_mb
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

