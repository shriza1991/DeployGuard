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

def extract_symbols_and_imports(diff_str: str) -> tuple[List[str], List[str], List[str]]:
    """
    Extracts high-priority signals from diff text:
    1. Function and class names
    2. Import statements
    3. Added and removed code lines (concise)
    """
    import re
    funcs_classes: List[str] = []
    imports: List[str] = []
    code_changes: List[str] = []

    func_class_regex = re.compile(r'^\+?\s*(?:def|class|function|const|let|var|type|interface)\s+([A-Za-z0-9_]+)')
    import_regex = re.compile(r'^\+?\s*(?:from\s+[\w\.]+\s+import|import\s+[\w\.]+|const\s+.*=\s*require\([\'"][^\'"]+[\'"]\))')

    for line in diff_str.splitlines():
        line_strip = line.strip()
        if not line_strip or line_strip.startswith(('+++', '---', '@@')):
            continue

        # Extract function/class definitions
        m_fc = func_class_regex.search(line_strip)
        if m_fc:
            sym = m_fc.group(1)
            if sym not in funcs_classes and len(sym) > 1:
                funcs_classes.append(sym)

        # Extract imports
        if import_regex.search(line_strip):
            if line_strip not in imports:
                imports.append(line_strip[:120])

        # Extract added/removed lines
        if (line.startswith('+') or line.startswith('-')) and not line.startswith(('+++', '---')):
            if len(code_changes) < 20:  # keep concise
                code_changes.append(line[:120])

    return funcs_classes, imports, code_changes


def build_priority_semantic_query(body: ContextRequest) -> tuple[str, List[str]]:
    """
    Constructs a concise semantic query in strict priority order:
    1. Changed function and class names
    2. Changed imports
    3. Added and removed code snippets
    4. Changed file paths
    5. PR title
    6. PR description
    """
    funcs_classes, imports, code_changes = extract_symbols_and_imports(body.diff or "")

    query_parts: List[str] = []

    # Priority 1: Changed function and class names
    if funcs_classes:
        query_parts.append("Changed Symbols:\n" + ", ".join(funcs_classes))

    # Priority 2: Changed imports
    if imports:
        query_parts.append("Changed Imports:\n" + "\n".join(imports[:10]))

    # Priority 3: Added and removed code snippets
    if code_changes:
        query_parts.append("Code Diff Snippets:\n" + "\n".join(code_changes[:15]))

    # Priority 4: Changed file paths
    if body.changed_files:
        query_parts.append("Changed Files:\n" + "\n".join(body.changed_files[:15]))

    # Priority 5: PR title
    if body.pr_title:
        query_parts.append("PR Title: " + body.pr_title)

    # Priority 6: PR description
    if body.pr_description:
        query_parts.append("PR Description: " + body.pr_description[:300])

    query_str = "\n\n".join(query_parts).strip()
    return query_str, funcs_classes


def compute_ranking_score_and_reason(
    hit: Dict[str, Any],
    changed_files: List[str],
    dependency_graph: Dict[str, List[str]],
    settings: Any,
    extracted_symbols: List[str] | None = None
) -> tuple[float, str, str, str]:
    """
    Computes ranking score and extracts matched_symbol, matched_text, and reason_for_match.
    Returns: (ranking_score, reason_for_match, matched_symbol, matched_text)
    """
    extracted_symbols = extracted_symbols or []
    payload = hit.get("payload") or {}
    rel_path = payload.get("relative_path", "")
    filename = payload.get("filename", "")
    directory = payload.get("directory", "")
    kind = payload.get("kind", "")
    text = payload.get("text", "")
    semantic_similarity = float(hit.get("score", 0.0))

    # 1. Look for matched symbol & matched text inside chunk
    matched_symbol = ""
    matched_text = ""
    for sym in extracted_symbols:
        if sym in text:
            matched_symbol = sym
            # Find the line containing the symbol
            for line in text.splitlines():
                if sym in line:
                    matched_text = line.strip()[:100]
                    break
            break

    if not matched_symbol:
        # Fallback symbol lookup from chunk text (def or class)
        import re
        m = re.search(r'(?:def|class|function|const)\s+([A-Za-z0-9_]+)', text)
        if m:
            matched_symbol = m.group(1)
            for line in text.splitlines():
                if matched_symbol in line:
                    matched_text = line.strip()[:100]
                    break

    if not matched_text and text:
        matched_text = text.splitlines()[0].strip()[:100]

    # 2. Heuristics matching
    exact_match = 0.0
    if changed_files:
        for f in changed_files:
            if rel_path == f or filename == os.path.basename(f):
                exact_match = 1.0
                break

    same_dir = 0.0
    if changed_files:
        for f in changed_files:
            changed_dir = os.path.dirname(f)
            if directory.replace("\\", "/") == changed_dir.replace("\\", "/"):
                same_dir = 1.0
                break

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

    is_config = 1.0 if kind == "configuration" or filename.lower() == "dockerfile" or os.path.splitext(filename)[1].lower() in (".tf", ".tfvars", ".yml", ".yaml", ".json") else 0.0
    is_test = 1.0 if kind == "test" or "test" in filename.lower() or "test" in rel_path.lower() else 0.0

    is_mock = 0.0
    for term in ("mock", "seed", "fixture", "generated", "sample", "example"):
        if term in filename.lower() or term in rel_path.lower():
            is_mock = 1.0
            break

    line_count = len(text.splitlines())
    tiny_factor = 1.0 if line_count < 5 else (0.5 if line_count < 10 else 0.0)

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

    # Construct human-readable reason_for_match
    if matched_symbol and exact_match == 1.0:
        reason = f"Contains the '{matched_symbol}' implementation modified in this change."
    elif matched_symbol:
        reason = f"Defines or references the '{matched_symbol}' symbol referenced by the PR."
    elif exact_match == 1.0:
        reason = "Contains source code being modified in this pull request."
    elif same_module == 1.0:
        reason = "Imports or is imported by the modified code in this module."
    elif same_dir == 1.0:
        reason = "Defined in the same directory as the changed files."
    elif is_config == 1.0:
        reason = "Infrastructure or configuration file related to changed services."
    elif is_test == 1.0:
        reason = "Unit or integration test for the modified functionality."
    else:
        reason = "High semantic similarity to the modified code and PR context."

    return ranking_score, reason, matched_symbol, matched_text


@router.post("/repository/context")
async def get_repository_context(request: Request, body: ContextRequest):
    """
    Primary endpoint for AI agents. Semantically retrieves relevant code/doc chunks
    strictly from the repository triggering the webhook.
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

    # Strict repository isolation check
    if not body.repository or not body.repository.strip():
        logger.warning("[WARNING] Repository Context Pipeline: Search stage failed: Repository parameter is missing or empty")
        total_request_ms = (time.perf_counter() - t_start) * 1000
        metrics["total_request_latency_ms"] = round(total_request_ms, 2)
        metrics["repository_context_available"] = False
        return {"results": [], "metrics": metrics}

    try:
        t_query_start = time.perf_counter()
        query_str, extracted_symbols = build_priority_semantic_query(body)
        t_query_end = time.perf_counter()
        query_construction_ms = (t_query_end - t_query_start) * 1000
        metrics["query_construction_latency_ms"] = round(query_construction_ms, 2)

        if not query_str.strip():
            total_request_ms = (time.perf_counter() - t_start) * 1000
            metrics["total_request_latency_ms"] = round(total_request_ms, 2)
            logger.warning("[WARNING] Repository Context Pipeline: Search stage failed: Empty semantic query generated")
            logger.warning("[WARNING] Repository Context Retrieval Failed")
            logger.warning(f"Repository:\n{body.repository}")
            logger.warning("Chunks returned:\n0")
            logger.warning("Possible causes:")
            logger.warning("- weak semantic query")
            return {"results": [], "metrics": metrics}

        t_embed_start = time.perf_counter()
        vector = []
        try:
            vector = embedding_service.embed_text(query_str)
            embedding_ok = "YES" if vector else "NO"
        except Exception as embed_err:
            embedding_ok = "NO"
            logger.warning(f"[WARNING] Repository Context Pipeline: Search stage failed: Query embedding generation failed: {embed_err}")
            raise embed_err

        embedding_latency_ms = (time.perf_counter() - t_embed_start) * 1000
        metrics["embedding_latency_ms"] = round(embedding_latency_ms, 2)

        logger.info("Query embedding generated:")
        logger.info(embedding_ok)
        logger.info("Embedding dimensions:")
        logger.info(f"{len(vector) if vector else 0}")
        logger.info("Embedding generation time:")
        logger.info(f"{int(embedding_latency_ms)} ms")

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
            
            # Fallback relaxes only the branch constraint. The repository filter is strictly retained.
            t_fallback_start = time.perf_counter()
            hits = qdrant_service.search(
                vector=vector,
                repository=body.repository,   # MUST always include repository filter
                branch=None,
                top_k=settings.top_k_max
            )
            t_fallback_search_ms = (time.perf_counter() - t_fallback_start) * 1000

        search_latency_ms = (time.perf_counter() - t_search_start) * 1000
        metrics["search_latency_ms"] = round(search_latency_ms, 2)
        metrics["fallback_used"] = fallback_triggered

        hits = [h for h in hits if float(h.get("score", 0.0)) >= settings.min_similarity]

        if settings.enable_deduplication:
            hits = deduplicate_hits(hits)

        # 6. Quality scoring, symbol extraction & ranking
        t_ranking_start = time.perf_counter()
        ranking_strategy = "semantic_similarity"
        
        manifest = request.app.state.redis_service.get_manifest(body.repository, body.branch or "main")
        dependency_graph = manifest.dependency_graph if manifest else {}

        for h in hits:
            r_score, reason, symbol, snippet_line = compute_ranking_score_and_reason(
                h, body.changed_files or [], dependency_graph, settings, extracted_symbols
            )
            h["ranking_score"] = r_score
            h["retrieval_reason"] = reason
            h["matched_symbol"] = symbol
            h["matched_text"] = snippet_line

        # Sort by ranking score descending (which combines semantic similarity & exact file boost)
        hits.sort(key=lambda h: float(h.get("ranking_score", h.get("score", 0.0))), reverse=True)

        ranking_latency_ms = (time.perf_counter() - t_ranking_start) * 1000
        metrics["ranking_strategy"] = ranking_strategy
        metrics["ranking_latency_ms"] = round(ranking_latency_ms, 2)

        # Limit to top 5-10 highest-confidence chunks (default: 8)
        max_chunks = min(settings.top_k_default, 10)
        hits = hits[:max_chunks]

        # 7. Prompt Assembly & Payload formatting
        t_assembly_start = time.perf_counter()
        results = []
        for hit in hits:
            payload = hit.get("payload") or {}
            rel_path = payload.get("relative_path", "")
            chunk_index = payload.get("chunk_index", 0)
            stored_commit = payload.get("commit", "")
            request_commit = body.commit or stored_commit
            evidence_id = f"{body.repository}:{rel_path}:{chunk_index}"
            if request_commit:
                evidence_id = f"{body.repository}:{request_commit}:{rel_path}:{chunk_index}"
            
            start_line = payload.get("start_line", 0)
            end_line = payload.get("end_line", 0)
            matched_sym = hit.get("matched_symbol", "")
            matched_txt = hit.get("matched_text", "")
            reason_str = hit.get("retrieval_reason", "High semantic similarity to modified code.")

            results.append({
                "repository": payload.get("repository") or body.repository,
                "branch": payload.get("branch") or body.branch,
                "commit": payload.get("commit", "") or body.commit or "",
                "relative_path": rel_path,
                "filename": payload.get("filename", ""),
                "score": float(hit.get("score", 0.0)),
                "similarity": float(hit.get("score", 0.0)),
                "ranking_score": float(hit.get("ranking_score", 0.0)),
                "matched_symbol": matched_sym,
                "matched_text": matched_txt,
                "reason_for_match": reason_str,
                "retrieval_reason": reason_str,
                "snippet": payload.get("text", ""),
                "text": payload.get("text", ""),
                "start_line": start_line,
                "end_line": end_line,
                "line_start": start_line,
                "line_end": end_line,
                "evidence_id": evidence_id,
                "metadata": {
                    "repository": payload.get("repository") or body.repository,
                    "branch": payload.get("branch") or body.branch,
                    "commit": payload.get("commit", "") or body.commit or "",
                    "language": payload.get("language", ""),
                    "relative_path": rel_path,
                    "filename": payload.get("filename", ""),
                    "directory": payload.get("directory", ""),
                    "chunk_index": chunk_index,
                    "chunk_count": payload.get("chunk_count", 0),
                    "start_line": start_line,
                    "end_line": end_line,
                    "line_start": start_line,
                    "line_end": end_line,
                    "kind": payload.get("kind", ""),
                    "matched_symbol": matched_sym,
                    "matched_text": matched_txt,
                    "reason_for_match": reason_str,
                    "retrieval_reason": reason_str,
                    "evidence_id": evidence_id,
                }
            })
        prompt_assembly_ms = (time.perf_counter() - t_assembly_start) * 1000
        metrics["prompt_assembly_latency_ms"] = round(prompt_assembly_ms, 2)

        scores = [float(hit.get("score", 0.0)) for hit in hits]
        top_similarity = max(scores) if scores else 0.0
        average_similarity = sum(scores) / len(scores) if scores else 0.0
        retrieved_paths = [hit.get("payload", {}).get("relative_path", "") for hit in hits]
        unique_files = len(set(retrieved_paths))

        metrics["repository_context_available"] = len(results) > 0
        metrics["top_similarity"] = round(top_similarity, 4)
        metrics["average_similarity"] = round(average_similarity, 4)
        metrics["unique_files"] = unique_files
        metrics["retrieved_paths"] = retrieved_paths

        total_request_ms = (time.perf_counter() - t_start) * 1000
        metrics["total_request_latency_ms"] = round(total_request_ms, 2)

        # Retrieve Qdrant diagnostics safely
        try:
            qdrant_col_exists = qdrant_service.collection_exists()
            if not isinstance(qdrant_col_exists, bool):
                qdrant_col_exists = False
        except Exception:
            qdrant_col_exists = False

        try:
            qdrant_chunk_count = qdrant_service.count_total_points() if qdrant_col_exists else 0
            if not isinstance(qdrant_chunk_count, int):
                qdrant_chunk_count = 0
        except Exception:
            qdrant_chunk_count = 0

        try:
            repo_payload_count = qdrant_service.count_repository_points(body.repository) if qdrant_col_exists else 0
            if not isinstance(repo_payload_count, int):
                repo_payload_count = 0
        except Exception:
            repo_payload_count = 0

        try:
            qdrant_repos = qdrant_service.get_unique_repositories() if qdrant_col_exists else []
            if not isinstance(qdrant_repos, list):
                qdrant_repos = []
        except Exception:
            qdrant_repos = []

        redis_status = "not_indexed"
        try:
            redis_status_obj = request.app.state.redis_service.get_status(body.repository, body.branch or "main")
            if redis_status_obj and type(redis_status_obj).__name__ != "MagicMock":
                if hasattr(redis_status_obj, "status"):
                    redis_status = redis_status_obj.status
        except Exception:
            pass

        match_status = "PASSED" if body.repository in qdrant_repos else "FAILED"

        # Verification debug logging
        logger.info("=" * 70)
        logger.info("[search] REPOSITORY CONTEXT RETRIEVAL DEBUG LOG:")
        logger.info("  Repository          : %s", body.repository)
        logger.info("  Branch              : %s", body.branch or "None")
        logger.info("  Commit              : %s", body.commit or "not provided")
        logger.info("  Clone URL           : %s", body.clone_url or "not provided")
        logger.info("  Qdrant filter       : repository == %s", body.repository)
        logger.info("  Query symbols       : %s", extracted_symbols)
        logger.info("  Retrieved chunk count: %d", len(results))
        logger.info("  Top similarity      : %.4f", top_similarity)
        logger.info("  Returned file paths : %s", retrieved_paths)
        
        logger.info("Redis Status:")
        logger.info(f"{redis_status}")
        logger.info("Qdrant Collection Exists:")
        logger.info("YES" if qdrant_col_exists else "NO")
        logger.info("Qdrant Chunk Count:")
        logger.info(f"{qdrant_chunk_count}")
        logger.info("Repository Payload Count:")
        logger.info(f"{repo_payload_count}")
        logger.info("Log the actual repository values stored in Qdrant:")
        logger.info("Repository requested:")
        logger.info(f"{body.repository}")
        logger.info("Repositories found in Qdrant:")
        for r_val in qdrant_repos:
            logger.info(f"- {r_val}")
        logger.info("Repository match:")
        logger.info(f"{match_status}")
        logger.info("=" * 70)

        # Actionable failure warn report if zero chunks returned
        if len(results) == 0:
            logger.warning("[WARNING] Repository Context Pipeline: Retrieval stage failed: Zero matching chunks found")
            logger.warning("[WARNING] Repository Context Retrieval Failed")
            logger.warning(f"Repository:\n{body.repository}")
            logger.warning(f"Repository exists:\n{'YES' if repo_payload_count > 0 else 'NO'}")
            logger.warning(f"Repository indexed:\n{'YES' if redis_status == 'completed' or repo_payload_count > 0 else 'NO'}")
            logger.warning(f"Chunks stored:\n{repo_payload_count}")
            logger.warning(f"Branch searched:\n{body.branch or 'None'}")
            logger.warning("Fallback branch:\nrepository only")
            logger.warning("Chunks returned:\n0")
            logger.warning("Possible causes:")
            logger.warning("- repository identifier mismatch")
            logger.warning("- incorrect payload metadata")
            logger.warning("- weak semantic query")
            logger.warning("- missing embeddings")

        return {"results": results, "metrics": metrics}

    except Exception as e:
        logger.error(f"[WARNING] Repository Context Pipeline: Search stage failed: Qdrant search execution failed: {e}", exc_info=True)
        # Attempt to get values for diagnostics even on exception
        qdrant_col_exists = False
        repo_payload_count = 0
        redis_status = "error"
        try:
            qdrant_col_exists = qdrant_service.collection_exists()
            if not isinstance(qdrant_col_exists, bool):
                qdrant_col_exists = False
        except Exception:
            pass
            
        try:
            if qdrant_col_exists:
                repo_payload_count = qdrant_service.count_repository_points(body.repository)
                if not isinstance(repo_payload_count, int):
                    repo_payload_count = 0
        except Exception:
            pass
            
        try:
            redis_status_obj = request.app.state.redis_service.get_status(body.repository, body.branch or "main")
            if redis_status_obj and type(redis_status_obj).__name__ != "MagicMock":
                if hasattr(redis_status_obj, "status"):
                    redis_status = redis_status_obj.status
        except Exception:
            pass

        logger.warning("[WARNING] Repository Context Retrieval Failed (Exception Encountered)")
        logger.warning(f"Repository:\n{body.repository}")
        logger.warning(f"Repository exists:\n{'YES' if repo_payload_count > 0 else 'NO'}")
        logger.warning(f"Repository indexed:\n{'YES' if redis_status == 'completed' or repo_payload_count > 0 else 'NO'}")
        logger.warning(f"Chunks stored:\n{repo_payload_count}")
        logger.warning(f"Branch searched:\n{body.branch or 'None'}")
        logger.warning("Fallback branch:\nrepository only")
        logger.warning("Chunks returned:\n0")
        logger.warning("Possible causes:")
        logger.warning("- repository identifier mismatch")
        logger.warning("- incorrect payload metadata")
        logger.warning("- weak semantic query")
        logger.warning("- missing embeddings")

        metrics["repository_context_available"] = False
        return {"results": [], "metrics": metrics}

