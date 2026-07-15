import logging
from fastapi import APIRouter, Request, HTTPException
from models import SearchRequest, ContextRequest

logger = logging.getLogger("repository-context-service")
router = APIRouter()

@router.post("/repository/search")
async def search_repository(request: Request, body: SearchRequest):
    """
    Performs semantic search on repository code chunks in Qdrant.
    """
    embedding_service = request.app.state.embedding_service
    qdrant_service = request.app.state.qdrant_service

    if not body.query.strip():
        return {"results": []}

    try:
        # Generate query embedding vector
        vector = embedding_service.embed_text(body.query)
        # Search Qdrant
        hits = qdrant_service.search(
            vector=vector,
            repository=body.repository,
            branch=body.branch,
            top_k=body.top_k
        )
        
        # Format response hits
        results = []
        for hit in hits:
            payload = hit.get("payload") or {}
            results.append({
                "score": hit.get("score", 0.0),
                "text": payload.get("text", ""),
                "metadata": {
                    "repository": payload.get("repository", ""),
                    "branch": payload.get("branch", ""),
                    "commit": payload.get("commit", ""),
                    "language": payload.get("language", ""),
                    "relative_path": payload.get("relative_path", ""),
                    "filename": payload.get("filename", ""),
                    "directory": payload.get("directory", ""),
                    "chunk_index": payload.get("chunk_index", 0),
                    "chunk_count": payload.get("chunk_count", 0),
                    "start_line": payload.get("start_line", 0),
                    "end_line": payload.get("end_line", 0),
                    "kind": payload.get("kind", ""),
                    "last_indexed": payload.get("last_indexed", "")
                }
            })
        return {"results": results}
    except Exception as e:
        logger.error(f"Search request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/repository/context")
async def get_repository_context(request: Request, body: ContextRequest):
    """
    Primary endpoint for AI agents. Semantically retrieves relevant code/doc chunks
    based on a list of changed files and a git diff.
    """
    embedding_service = request.app.state.embedding_service
    qdrant_service = request.app.state.qdrant_service

    # Build prompt/query by combining files and git diff
    query_parts = []
    if body.changed_files:
        query_parts.append("Changed files:\n" + "\n".join(body.changed_files))
    if body.diff:
        query_parts.append("Git diff:\n" + body.diff)

    query_str = "\n\n".join(query_parts)
    if not query_str.strip():
        return {"results": []}

    try:
        # Embed concatenated query string
        vector = embedding_service.embed_text(query_str)
        # Search Qdrant
        hits = qdrant_service.search(
            vector=vector,
            repository=body.repository,
            branch=body.branch,
            top_k=10 # return top 10 relevant context blocks
        )
        
        results = []
        for hit in hits:
            payload = hit.get("payload") or {}
            results.append({
                "score": hit.get("score", 0.0),
                "text": payload.get("text", ""),
                "metadata": {
                    "repository": payload.get("repository", ""),
                    "branch": payload.get("branch", ""),
                    "commit": payload.get("commit", ""),
                    "language": payload.get("language", ""),
                    "relative_path": payload.get("relative_path", ""),
                    "filename": payload.get("filename", ""),
                    "directory": payload.get("directory", ""),
                    "chunk_index": payload.get("chunk_index", 0),
                    "chunk_count": payload.get("chunk_count", 0),
                    "start_line": payload.get("start_line", 0),
                    "end_line": payload.get("end_line", 0),
                    "kind": payload.get("kind", ""),
                    "last_indexed": payload.get("last_indexed", "")
                }
            })
        return {"results": results}
    except Exception as e:
        logger.error(f"Context retrieval request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
