import logging
import os
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

# Initialize FastAPI App
app = FastAPI(
    title="DeployGuard Repository Context Service",
    description="Stand-alone microservice providing semantic context to DeployGuard AI agents.",
    version="1.0.0"
)

# Load settings
settings = get_settings()

# Ensure local data directory exists
os.makedirs(settings.data_dir, exist_ok=True)

# Initialize service instances
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

# Bind state to FastAPI application
app.state.settings = settings
app.state.clone_service = clone_service
app.state.redis_service = redis_service
app.state.qdrant_service = qdrant_service
app.state.chunker = chunker
app.state.embedding_service = embedding_service
app.state.indexer = indexer

# Include routers
app.include_router(repository_router, tags=["Repository Management"])
app.include_router(search_router, tags=["Semantic Retrieval"])

@app.get("/health")
def health_check():
    """Service health and connection diagnostic check."""
    qdrant_ok = qdrant_service.health_check()
    redis_ok = False
    try:
        redis_ok = redis_service.client.ping()
    except Exception:
        pass

    return {
        "status": "healthy" if (qdrant_ok and redis_ok) else "degraded",
        "connections": {
            "qdrant": "connected" if qdrant_ok else "failed",
            "redis": "connected" if redis_ok else "failed"
        }
    }
