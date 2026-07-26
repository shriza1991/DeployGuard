import logging
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, Query
from models import IndexRequest, RepoStatus, RepoManifest, RepoStats

logger = logging.getLogger("repository-context-service")
router = APIRouter()

@router.post("/repository/index", status_code=202)
async def index_repository(request: Request, body: IndexRequest, background_tasks: BackgroundTasks):
    """
    Kicks off cloning, parsing, chunking, and embedding a repository in the background.

    For webhook-driven calls, pass ``repository_full_name`` (the GitHub
    ``repository.full_name`` field, e.g. ``"acme/my-service"``) and
    ``clone_url`` (``repository.clone_url``) to ensure the correct
    clone URL and identifier are used instead of the defaults derived
    from ``repository_url``.
    """
    indexer = request.app.state.indexer
    # Prefer clone_url when explicitly supplied; fall back to repository_url
    effective_url = body.clone_url or body.repository_url
    background_tasks.add_task(
        indexer.index_repository,
        repository_url=effective_url,
        branch=body.branch,
        repository_full_name=body.repository_full_name,
    )
    return {"status": "started"}


@router.get("/repository/status/{repository:path}", response_model=RepoStatus)
async def get_repository_status(request: Request, repository: str, branch: str = Query("main")):
    """
    Checks the indexing status of a repository in Redis.
    """
    redis_service = request.app.state.redis_service
    status = redis_service.get_status(repository, branch)
    if not status:
        return RepoStatus(status="not_indexed", branch=branch)
    return status

@router.get("/repository/manifest/{repository:path}", response_model=RepoManifest)
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

@router.delete("/repository/index/{repository:path}")
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

@router.get("/repository/stats/{repository:path}", response_model=RepoStats)
async def get_repository_stats(
    request: Request,
    repository: str,
    branch: str = Query("main")
):
    redis_service = request.app.state.redis_service

    manifest = redis_service.get_manifest(repository, branch)

    if not manifest:
        raise HTTPException(
            status_code=404,
            detail=f"Repository stats not found for '{repository}' on branch '{branch}'."
        )

    return RepoStats(
        repository=repository,
        branch=branch,
        number_of_files=manifest.number_of_files,
        number_of_chunks=manifest.number_of_chunks,
        lines_of_code=manifest.lines_of_code,
        detected_languages=manifest.detected_languages,
        test_count=manifest.test_count,
        configuration_count=manifest.configuration_count,
        number_of_services=manifest.number_of_services,
        repository_size_bytes=manifest.repository_size_bytes,
        docker_images=manifest.docker_images,
        terraform_modules=manifest.terraform_modules,
        helm_charts=manifest.helm_charts,
    )
