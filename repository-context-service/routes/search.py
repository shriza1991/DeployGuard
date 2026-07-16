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
        
        branch_filter_enabled = bool(body.branch)
        logger.info("Searching repository context")
        logger.info(f"Repository: {body.repository}")
        logger.info(f"Branch: {body.branch}")
        logger.info(f"Branch filter enabled: {branch_filter_enabled}")
        logger.info("Top K: 10")
        
        fallback_triggered = False
        hits = []
        if branch_filter_enabled:
            hits = qdrant_service.search(
                vector=vector,
                repository=body.repository,
                branch=body.branch,
                top_k=10
            )

        if len(hits) == 0:
            if branch_filter_enabled:
                logger.info("No branch-specific matches found.")
                logger.info(f"No branch-specific context found for '{body.repository}'. Falling back to repository-wide search.")
                logger.info("Retrying repository-wide search...")
                fallback_triggered = True
            
            hits = qdrant_service.search(
                vector=vector,
                repository=body.repository,
                branch=None,
                top_k=10
            )
            
            # When repository-wide retrieval succeeds, prioritize chunks whose relative_path or filename matches the changed_files list
            if hits and body.changed_files:
                changed_files_set = set(body.changed_files)
                matched_hits = []
                other_hits = []
                for hit in hits:
                    payload = hit.get("payload") or {}
                    rel_path = payload.get("relative_path")
                    filename = payload.get("filename")
                    if rel_path in changed_files_set or filename in changed_files_set:
                        matched_hits.append(hit)
                    else:
                        other_hits.append(hit)
                hits = matched_hits + other_hits

        # Deduplicate results using relative_path + chunk_index or Qdrant point ID
        seen = set()
        deduped_hits = []
        for hit in hits:
            point_id = hit.get("id")
            payload = hit.get("payload") or {}
            rel_path = payload.get("relative_path", "")
            chunk_idx = payload.get("chunk_index", 0)
            
            dup_key = point_id if point_id else (rel_path, chunk_idx)
            if dup_key not in seen:
                seen.add(dup_key)
                deduped_hits.append(hit)
        hits = deduped_hits

        retrieved_chunk_count = len(hits)
        top_score = hits[0].get("score", 0.0) if hits else 0.0

        if fallback_triggered:
            logger.info(f"Repository-wide search returned {retrieved_chunk_count} chunks.")
        else:
            logger.info(f"Search returned {retrieved_chunk_count} chunks.")

        logger.info(f"Fallback triggered: {fallback_triggered}")
        logger.info(f"Retrieved chunk count: {retrieved_chunk_count}")
        logger.info(f"Top similarity score: {top_score}")

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
