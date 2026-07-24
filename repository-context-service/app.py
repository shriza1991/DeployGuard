import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from config import get_settings
from routes.repository import router as repository_router
from routes.search import router as search_router
from services.clone_service import CloneService
from services.redis_service import RedisService
from services.qdrant_service import QdrantService
from services.chunker import Chunker
from services.embedding_service import EmbeddingService
from services.indexer import Indexer

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("repository-context-service")

# State variable for service readiness (defaults to READY for unit tests, updated by server lifespan)
SERVICE_STATE = "READY"

def get_service_state() -> str:
    return SERVICE_STATE

async def load_embedding_model_background(app: FastAPI, embedding_service: EmbeddingService):
    global SERVICE_STATE
    SERVICE_STATE = "LOADING_MODEL"
    app.state.service_state = "LOADING_MODEL"
    logger.info("Background loading of embedding model started (state: LOADING_MODEL)...")
    try:
        # Run blocking model loading in an executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, embedding_service.load_model)
        SERVICE_STATE = "READY"
        app.state.service_state = "READY"
        logger.info("Embedding model loaded successfully. Repository Context Service is READY!")
    except Exception as e:
        logger.error(f"Error loading embedding model: {e}", exc_info=True)
        SERVICE_STATE = "READY"  # Fallback to ready (using HashEmbeddingProvider)
        app.state.service_state = "READY"

@asynccontextmanager
async def lifespan(app: FastAPI):
    global SERVICE_STATE
    SERVICE_STATE = "STARTING"
    app.state.service_state = "STARTING"

    # Load settings
    settings = get_settings()
    os.makedirs(settings.data_dir, exist_ok=True)


    clone_service = CloneService(data_dir=settings.data_dir)
    redis_service = RedisService(redis_url=settings.redis_url)
    qdrant_service = QdrantService(
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        timeout_seconds=settings.qdrant_timeout_seconds,
        retries=settings.qdrant_retries
    )
    chunker = Chunker(
        chunk_size_tokens=settings.chunk_size_tokens,
        overlap_tokens=settings.chunk_overlap_tokens
    )
    embedding_service = EmbeddingService(
        model_name=settings.embedding_model,
        dimension=settings.embedding_dimension
    )
    indexer = Indexer(
        settings=settings,
        clone_service=clone_service,
        redis_service=redis_service,
        qdrant_service=qdrant_service,
        chunker=chunker,
        embedding_service=embedding_service
    )

    app.state.settings = settings
    app.state.clone_service = clone_service
    app.state.redis_service = redis_service
    app.state.qdrant_service = qdrant_service
    app.state.chunker = chunker
    app.state.embedding_service = embedding_service
    app.state.indexer = indexer
    app.state.service_state = "STARTING"

    # Start background task to pre-load model asynchronously
    asyncio.create_task(load_embedding_model_background(app, embedding_service))
    yield


# Initialize FastAPI App
app = FastAPI(
    title="DeployGuard Repository Context Service",
    description="Stand-alone microservice providing semantic context to DeployGuard AI agents.",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(repository_router, tags=["Repository Management"])
app.include_router(search_router, tags=["Semantic Retrieval"])

@app.get("/readiness")
def readiness_check():
    """Readiness endpoint returning state machine status."""
    is_ready = (SERVICE_STATE == "READY")
    return {
        "status": SERVICE_STATE,
        "state": SERVICE_STATE,
        "ready": is_ready
    }

@app.get("/health")
def health_check():
    """Service health and connection diagnostic check."""
    qdrant_ok = False
    redis_ok = False
    if hasattr(app.state, "qdrant_service"):
        qdrant_ok = app.state.qdrant_service.health_check()
    if hasattr(app.state, "redis_service"):
        try:
            redis_ok = app.state.redis_service.client.ping()
        except Exception:
            pass

    return {
        "status": "healthy" if (qdrant_ok and redis_ok and SERVICE_STATE == "READY") else "degraded",
        "state": SERVICE_STATE,
        "ready": SERVICE_STATE == "READY",
        "connections": {
            "qdrant": "connected" if qdrant_ok else "failed",
            "redis": "connected" if redis_ok else "failed"
        }
    }

