"""
analysis/repository_correlator.py — Phase 1 wrapper around the Repository Context Service.

Converts raw evidence chunks (from repository_context_client) into typed
RepositoryContextChunk objects so Phase 2 never needs to touch the raw response.
No LLM, no blocking waits beyond what the HTTP client already provides.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from analysis.models import RepositoryContextChunk

logger = logging.getLogger("code-risk-phase1")


def fetch(payload: Dict[str, Any]) -> Tuple[List[RepositoryContextChunk], Dict[str, Any]]:
    """
    Fetch repository semantic context for the changed files in *payload*.

    Delegates to :func:`repository_context_client.RepositoryEvidenceProvider.get_repository_evidence`,
    which handles auto-indexing, status checks, and HTTP retries.

    Returns
    -------
    chunks:
        List of :class:`RepositoryContextChunk` objects, each with a
        ``reason`` field explaining why the chunk was returned.
    metrics:
        Raw metrics dict from the context service (retrieval latency, chunk
        count, index status, etc.).
    """
    try:
        from repository_context_client import RepositoryEvidenceProvider
        raw_evidence, metrics = RepositoryEvidenceProvider.get_repository_evidence(payload)
    except Exception as exc:
        logger.warning("Repository context fetch failed: %s", exc)
        return [], {}

    chunks: List[RepositoryContextChunk] = []
    for item in raw_evidence or []:
        if not isinstance(item, dict):
            continue
        meta = item.get("metadata") or {}
        chunk = RepositoryContextChunk(
            file=meta.get("relative_path") or meta.get("filename") or "unknown",
            lines=f"{meta.get('start_line', 0)}-{meta.get('end_line', 0)}",
            similarity=float(item.get("score") or 0.0),
            reason=_resolve_reason(item, meta),
            text=str(item.get("text") or "")[:2000],  # cap per chunk
        )
        chunks.append(chunk)

    return chunks, metrics or {}


def _resolve_reason(item: Dict[str, Any], meta: Dict[str, Any]) -> str:
    """
    Produce a human-readable reason explaining why this chunk was returned.

    Priority:
    1. ``retrieval_reason`` from the context service (most authoritative)
    2. Score band heuristic
    3. Generic fallback
    """
    service_reason = (
        item.get("retrieval_reason")
        or item.get("ranking_reason")
        or meta.get("retrieval_reason")
        or ""
    ).strip()

    if service_reason:
        return service_reason

    score = float(item.get("score") or 0.0)
    if score >= 0.95:
        return "Exact or near-exact match with changed file"
    if score >= 0.85:
        return "High semantic similarity to changed code"
    if score >= 0.70:
        return "Moderate semantic similarity — related module"
    return "Low similarity — included as supporting context"
