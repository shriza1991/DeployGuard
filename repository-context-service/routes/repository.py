import logging
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, Query
from models import IndexRequest, RepoStatus, RepoManifest

logger = logging.getLogger("repository-context-service")
router = APIRouter()

@router.post("/repository/index", status_code=202)
async def index_repository(request: Request, body: IndexRequest, background_tasks: BackgroundTasks):
    """
    Kicks off cloning, parsing, chunking, and embedding a repository in the background.
    """
    indexer = request.app.state.indexer
    background_tasks.add_task(
        indexer.index_repository,
        repository_url=body.repository_url,
        branch=body.branch
    )
    return {"status": "started"}

@router.get("/repository/status/{repository}", response_model=RepoStatus)
async def get_repository_status(request: Request, repository: str, branch: str = Query("main")):
    """
    Checks the indexing status of a repository in Redis.
    """
    redis_service = request.app.state.redis_service
    status = redis_service.get_status(repository, branch)
    if not status:
        return RepoStatus(status="not_indexed", branch=branch)
    return status

@router.get("/repository/manifest/{repository}", response_model=RepoManifest)
async def get_repository_manifest(request: Request, repository: str, branch: str = Query("main")):
    """
    Retrieves the detected technology manifest for a repository.
    """
    redis_service = request.app.state.redis_service
    manifest = redis_service.get_manifest(repository, branch)
    if not manifest:
        raise HTTPException(
            status_code=404, 
            detail=f"Manifest not found for repository '{repository}' on branch '{branch}'."
        )
    return manifest

@router.delete("/repository/index/{repository}")
async def delete_repository_index(request: Request, repository: str, branch: str = Query("main")):
    """
    Purges all repository points from Qdrant and clears status/manifest details from Redis.
    """
    qdrant_service = request.app.state.qdrant_service
    redis_service = request.app.state.redis_service

    logger.info(f"Received request to delete repository index: {repository} (branch: {branch})")
    
    try:
        # Delete from Qdrant
        qdrant_service.delete_by_repository(repository, branch)
        # Delete from Redis
        redis_service.delete_repository_data(repository, branch)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Error purging repository data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
