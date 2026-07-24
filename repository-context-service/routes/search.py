import logging
import time
import os
from typing import List, Dict, Any
from fastapi import APIRouter, Request, HTTPException
from models import SearchRequest, ContextRequest

logger = logging.getLogger("repository-context-service")
router = APIRouter()

@router.post("/repository/search")
async def search_repository(request: Request, body: SearchRequest):
    """
    Performs semantic search on repository code chunks in Qdrant.
    """
    try:
        state = getattr(request.app.state, "service_state", None)
        if state is None:
            from app import get_service_state
            state = get_service_state()
        if state not in ("READY", None):
            raise HTTPException(
                status_code=503,
                detail={"state": state, "message": "Repository Context Service embedding model is loading"}
            )
    except HTTPException:
        raise
    except Exception:
        pass

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

def get_priority_rank(hit: Dict[str, Any], changed_files: List[str]) -> int:
    """
    Returns the prioritization priority rank of the chunk:
    1. Exact changed filename or relative path match.
    2. Same directory.
    3. Same module/package (shares top-level parent folder).
    4. Highest semantic similarity.
    """
    payload = hit.get("payload") or {}
    rel_path = payload.get("relative_path", "")
    filename = payload.get("filename", "")
    directory = payload.get("directory", "")

    if not changed_files:
        return 4

    # 1. Exact relative path or filename match
    for f in changed_files:
        if rel_path == f or filename == os.path.basename(f):
            return 1

    # 2. Same directory
    for f in changed_files:
        changed_dir = os.path.dirname(f)
        norm_dir = directory.replace("\\", "/")
        norm_changed_dir = changed_dir.replace("\\", "/")
        if norm_dir == norm_changed_dir:
            return 2

    # 3. Same module/package (shares the top-level parent folder)
    for f in changed_files:
        changed_parts = f.replace("\\", "/").split("/")
        chunk_parts = rel_path.replace("\\", "/").split("/")
        if len(changed_parts) > 1 and len(chunk_parts) > 1:
            if changed_parts[0] == chunk_parts[0]:
                return 3

    return 4

def deduplicate_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicates hits using Qdrant point id or (relative_path, chunk_index).
    """
    seen_ids = set()
    seen_paths = set()
    deduped = []
    for hit in hits:
        point_id = hit.get("id")
        payload = hit.get("payload") or {}
        rel_path = payload.get("relative_path", "")
        chunk_idx = payload.get("chunk_index", 0)

        path_key = (rel_path, chunk_idx)
        if point_id:
            if point_id in seen_ids:
                continue
        if rel_path and chunk_idx is not None:
            if path_key in seen_paths:
                continue

        if point_id:
            seen_ids.add(point_id)
        if rel_path and chunk_idx is not None:
            seen_paths.add(path_key)

        deduped.append(hit)
    return deduped

def compute_ranking_score_and_reason(
    hit: Dict[str, Any],
    changed_files: List[str],
    dependency_graph: Dict[str, List[str]],
    settings: Any
) -> tuple[float, str]:
    payload = hit.get("payload") or {}
    rel_path = payload.get("relative_path", "")
    filename = payload.get("filename", "")
    directory = payload.get("directory", "")
    kind = payload.get("kind", "")
    text = payload.get("text", "")
    semantic_similarity = hit.get("score", 0.0)

    # 1. Exact match
    exact_match = 0.0
    if changed_files:
        for f in changed_files:
            if rel_path == f or filename == os.path.basename(f):
                exact_match = 1.0
                break

    # 2. Same dir
    same_dir = 0.0
    if changed_files:
        for f in changed_files:
            changed_dir = os.path.dirname(f)
            if directory.replace("\\", "/") == changed_dir.replace("\\", "/"):
                same_dir = 1.0
                break

    # 3. Same module or dependency link
    same_module = 0.0
    if changed_files:
        for f in changed_files:
            changed_parts = f.replace("\\", "/").split("/")
            chunk_parts = rel_path.replace("\\", "/").split("/")
            if len(changed_parts) > 1 and len(chunk_parts) > 1 and changed_parts[0] == chunk_parts[0]:
                same_module = 1.0
                break
            
            if dependency_graph:
                if f in dependency_graph and rel_path in dependency_graph[f]:
                    same_module = 1.0
                    break
                if rel_path in dependency_graph and f in dependency_graph[rel_path]:
                    same_module = 1.0
                    break

    # 4. Is config
    is_config = 1.0 if kind == "configuration" or filename.lower() == "dockerfile" or os.path.splitext(filename)[1].lower() in (".tf", ".tfvars", ".yml", ".yaml", ".json") else 0.0

    # 5. Is test
    is_test = 1.0 if kind == "test" or "test" in filename.lower() or "test" in rel_path.lower() else 0.0

    # 6. Is mock
    is_mock = 0.0
    for term in ("mock", "seed", "fixture", "generated", "sample", "example"):
        if term in filename.lower() or term in rel_path.lower():
            is_mock = 1.0
            break

    # 7. Tiny factor
    line_count = len(text.splitlines())
    if line_count < 5:
        tiny_factor = 1.0
    elif line_count < 10:
        tiny_factor = 0.5
    else:
        tiny_factor = 0.0

    final_score = (
        (settings.weight_semantic * semantic_similarity) +
        (settings.bonus_exact_file * exact_match) +
        (settings.bonus_same_dir * same_dir) +
        (settings.bonus_same_module * same_module) +
        (settings.bonus_config_file * is_config) -
        (settings.penalty_test_file * is_test) -
        (settings.penalty_mock_generated * is_mock) -
        (settings.penalty_tiny_chunk * tiny_factor)
    )
    ranking_score = max(0.0, min(1.0, final_score))

    # Determine reason
    if exact_match == 1.0:
        reason = "Exact changed file"
    elif same_dir == 1.0:
        reason = "Directory boost"
    elif same_module == 1.0:
        reason = "Module/Dependency boost"
    elif is_config == 1.0:
        reason = "Configuration boost"
    elif is_test == 1.0:
        reason = "Semantic similarity (Test file)"
    elif is_mock == 1.0:
        reason = "Semantic similarity (Mock file)"
    else:
        reason = "Semantic similarity"

    return ranking_score, reason

@router.post("/repository/context")
async def get_repository_context(request: Request, body: ContextRequest):
    """
    Primary endpoint for AI agents. Semantically retrieves relevant code/doc chunks
    based on a list of changed files and a git diff, applying quality scoring heuristics.
    """
    try:
        state = getattr(request.app.state, "service_state", None)
        if state is None:
            from app import get_service_state
            state = get_service_state()
        if state not in ("READY", None):
            raise HTTPException(
                status_code=503,
                detail={"state": state, "message": "Repository Context Service embedding model is loading"}
            )
    except HTTPException:
        raise
    except Exception:
        pass

    t_start = time.perf_counter()

    settings = request.app.state.settings
    embedding_service = request.app.state.embedding_service
    qdrant_service = request.app.state.qdrant_service

    metrics = {
        "repository_context_available": False,
        "branch_filter_used": bool(body.branch),
        "fallback_used": False,
        "top_similarity": 0.0,
        "average_similarity": 0.0,
        "unique_files": 0,
        "retrieved_paths": [],
        "ranking_strategy": "semantic_similarity",
        "query_construction_latency_ms": 0.0,
        "embedding_latency_ms": 0.0,
        "search_latency_ms": 0.0,
        "ranking_latency_ms": 0.0,
        "prompt_assembly_latency_ms": 0.0,
        "total_request_latency_ms": 0.0
    }

    try:
        t_query_start = time.perf_counter()
        query_parts = []
        if body.changed_files:
            query_parts.append("Changed files:\n" + "\n".join(body.changed_files))
        if body.diff:
            query_parts.append("Git diff:\n" + body.diff)

        query_str = "\n\n".join(query_parts)
        t_query_end = time.perf_counter()
        query_construction_ms = (t_query_end - t_query_start) * 1000
        metrics["query_construction_latency_ms"] = round(query_construction_ms, 2)

        if not query_str.strip():
            total_request_ms = (time.perf_counter() - t_start) * 1000
            metrics["total_request_latency_ms"] = round(total_request_ms, 2)
            logger.info("Repository Context: empty query, returning early.")
            return {"results": [], "metrics": metrics}

        t_embed_start = time.perf_counter()
        vector = embedding_service.embed_text(query_str)
        embedding_latency_ms = (time.perf_counter() - t_embed_start) * 1000
        metrics["embedding_latency_ms"] = round(embedding_latency_ms, 2)

        branch_filter_enabled = bool(body.branch)
        fallback_triggered = False
        hits = []
        t_branch_search_ms = 0.0
        t_fallback_search_ms = 0.0
        t_search_start = time.perf_counter()

        if branch_filter_enabled:
            t_branch_start = time.perf_counter()
            hits = qdrant_service.search(
                vector=vector,
                repository=body.repository,
                branch=body.branch,
                top_k=settings.top_k_max
            )
            t_branch_search_ms = (time.perf_counter() - t_branch_start) * 1000

        if len(hits) == 0:
            if branch_filter_enabled:
                fallback_triggered = True
            
            if settings.enable_fallback:
                t_fallback_start = time.perf_counter()
                hits = qdrant_service.search(
                    vector=vector,
                    repository=body.repository,
                    branch=None,
                    top_k=settings.top_k_max
                )
                t_fallback_search_ms = (time.perf_counter() - t_fallback_start) * 1000

        search_latency_ms = (time.perf_counter() - t_search_start) * 1000
        metrics["search_latency_ms"] = round(search_latency_ms, 2)
        metrics["fallback_used"] = fallback_triggered

        hits = [h for h in hits if h.get("score", 0.0) >= settings.min_similarity]

        if settings.enable_deduplication:
            hits = deduplicate_hits(hits)

        # 6. Quality scoring & ranking
        t_ranking_start = time.perf_counter()
        ranking_strategy = "semantic_similarity"
        
        # Read dependency graph from Redis
        manifest = request.app.state.redis_service.get_manifest(body.repository, body.branch or "main")
        dependency_graph = manifest.dependency_graph if manifest else {}

        for h in hits:
            if settings.enable_ranking:
                ranking_strategy = "heuristics"
                r_score, reason = compute_ranking_score_and_reason(
                    h, body.changed_files, dependency_graph, settings
                )
            else:
                r_score = h.get("score", 0.0)
                reason = "Semantic similarity"
            h["ranking_score"] = r_score
            h["retrieval_reason"] = reason

        if settings.enable_ranking:
            hits.sort(key=lambda h: h.get("ranking_score", 0.0), reverse=True)
            
        ranking_latency_ms = (time.perf_counter() - t_ranking_start) * 1000
        metrics["ranking_strategy"] = ranking_strategy
        metrics["ranking_latency_ms"] = round(ranking_latency_ms, 2)

        hits = hits[:settings.top_k_default]

        # 7. Prompt Assembly
        t_assembly_start = time.perf_counter()
        results = []
        for hit in hits:
            payload = hit.get("payload") or {}
            rel_path = payload.get("relative_path", "")
            chunk_index = payload.get("chunk_index", 0)
            evidence_id = f"{body.repository}:{rel_path}:{chunk_index}"
            
            results.append({
                "score": hit.get("score", 0.0),
                "ranking_score": hit.get("ranking_score", 0.0),
                "retrieval_reason": hit.get("retrieval_reason", "Semantic similarity"),
                "evidence_id": evidence_id,
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
                    "last_indexed": payload.get("last_indexed", ""),
                    "evidence_id": evidence_id,
                    "retrieval_reason": hit.get("retrieval_reason", "Semantic similarity")
                }
            })
        prompt_assembly_ms = (time.perf_counter() - t_assembly_start) * 1000
        metrics["prompt_assembly_latency_ms"] = round(prompt_assembly_ms, 2)

        scores = [hit.get("score", 0.0) for hit in hits]
        top_similarity = max(scores) if scores else 0.0
        average_similarity = sum(scores) / len(scores) if scores else 0.0
        retrieved_paths = [hit.get("payload", {}).get("relative_path", "") for hit in hits]
        unique_files = len(set(retrieved_paths))

        metrics["repository_context_available"] = True
        metrics["top_similarity"] = round(top_similarity, 4)
        metrics["average_similarity"] = round(average_similarity, 4)
        metrics["unique_files"] = unique_files
        metrics["retrieved_paths"] = retrieved_paths

        total_request_ms = (time.perf_counter() - t_start) * 1000
        metrics["total_request_latency_ms"] = round(total_request_ms, 2)

        logger.info("Repository Context Performance metrics:")
        logger.info(f"Query construction: {round(query_construction_ms, 2)} ms")
        logger.info(f"Embedding generation: {round(embedding_latency_ms, 2)} ms")
        logger.info(f"Branch search: {round(t_branch_search_ms, 2)} ms")
        logger.info(f"Fallback search: {round(t_fallback_search_ms, 2)} ms")
        logger.info(f"Ranking: {round(ranking_latency_ms, 2)} ms")
        logger.info(f"Prompt assembly: {round(prompt_assembly_ms, 2)} ms")
        logger.info(f"Total request: {round(total_request_ms, 2)} ms")

        # Rich logging
        evidence_lines = "\n".join(retrieved_paths) if retrieved_paths else "None"
        rich_log = (
            f"Repository Context retrieval summary:\n"
            f"Repository: {body.repository}\n"
            f"Branch: {body.branch or 'None'}\n"
            f"Fallback: {'Yes' if fallback_triggered else 'No'}\n"
            f"Chunks: {len(results)}\n"
            f"Top Similarity: {round(top_similarity, 2)}\n"
            f"Evidence paths:\n{evidence_lines}"
        )
        logger.info(rich_log)

        return {"results": results, "metrics": metrics}

    except Exception as e:
        logger.error(f"Context retrieval failed: {e}", exc_info=True)
        metrics["repository_context_available"] = False
        return {"results": [], "metrics": metrics}
