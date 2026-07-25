import datetime
import os
import time
import logging
import requests
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("code-risk-agent")

REPOSITORY_CONTEXT_URL = os.getenv("REPOSITORY_CONTEXT_URL", "http://repository-context-service:8003").rstrip("/")
REPOSITORY_CONTEXT_TIMEOUT = float(os.getenv("REPOSITORY_CONTEXT_TIMEOUT", "10.0"))
MAX_READINESS_WAIT_SECONDS = float(os.getenv("MAX_READINESS_WAIT_SECONDS", "90.0"))


def wait_for_readiness(max_wait_seconds: float = MAX_READINESS_WAIT_SECONDS, initial_backoff: float = 1.0) -> bool:
    """
    Polls Repository Context Service /readiness endpoint with exponential backoff.
    Returns True if service is READY, False if timeout expired.
    """
    readiness_url = f"{REPOSITORY_CONTEXT_URL}/readiness"
    start_time = time.perf_counter()
    current_backoff = initial_backoff
    max_backoff = 10.0

    while True:
        elapsed = time.perf_counter() - start_time
        if elapsed >= max_wait_seconds:
            logger.warning(
                "[code-risk] Timed out waiting for Repository Context Service readiness after %.1f seconds",
                elapsed
            )
            return False

        try:
            res = requests.get(readiness_url, timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                state = data.get("state", "UNKNOWN")
                if state == "READY" or data.get("ready") is True:
                    logger.info("[code-risk] Repository Context Service is READY! (elapsed: %.1fs)", elapsed)
                    return True
                logger.info(
                    "[code-risk] Waiting for Repository Context Service readiness (current state: WAITING_FOR_DEPENDENCY [%s])... retrying in %.1fs (elapsed: %.1fs)",
                    state, current_backoff, elapsed
                )
            else:
                logger.info(
                    "[code-risk] Waiting for Repository Context Service readiness (HTTP Status %s)... retrying in %.1fs (elapsed: %.1fs)",
                    res.status_code, current_backoff, elapsed
                )
        except Exception as exc:
            logger.info(
                "[code-risk] Waiting for Repository Context Service connection (%s)... retrying in %.1fs (elapsed: %.1fs)",
                exc, current_backoff, elapsed
            )

        time.sleep(current_backoff)
        current_backoff = min(current_backoff * 2.0, max_backoff)


def _extract_webhook_repo_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts and normalises the repository-related fields from a GitHub webhook
    payload (as published on the Kafka ``deployment-events`` topic by the gateway).

    Returns a dict with keys:
        full_name       – e.g. "acme/my-service" (canonical identifier)
        clone_url       – HTTPS clone URL from repository.clone_url
        default_branch  – repository.default_branch (falls back to "main")
        branch          – the PR head ref (falls back to default_branch)
        commit_sha      – head_commit.id (the triggering commit)
        changed_files   – list of file path strings
        diff            – concatenated unified diff from file patches
    """
    repo_obj = payload.get("repository") or {}
    pull_request = payload.get("pull_request") or {}
    head_commit = payload.get("head_commit") or {}

    # ── Repository identity ────────────────────────────────────────────────
    # Prefer full_name (e.g. "acme/my-service") over the short "name" field.
    # Both may be present; full_name is always unambiguous across organisations.
    full_name = (
        repo_obj.get("full_name")
        or repo_obj.get("name")
        or ""
    )

    # Derive full_name from the PR URL as a last resort
    if not full_name and pull_request.get("url"):
        parts = pull_request["url"].rstrip("/").split("/")
        # GitHub PR URLs: https://api.github.com/repos/owner/repo/pulls/1
        # or:             https://github.com/owner/repo/pull/1
        try:
            if "repos" in parts:
                idx = parts.index("repos")
                full_name = f"{parts[idx + 1]}/{parts[idx + 2]}"
            elif "pull" in parts:
                idx = parts.index("pull")
                full_name = f"{parts[idx - 2]}/{parts[idx - 1]}"
        except (IndexError, ValueError):
            pass

    clone_url = repo_obj.get("clone_url") or ""
    default_branch = repo_obj.get("default_branch") or "main"

    # ── Branch ────────────────────────────────────────────────────────────
    # For pull_request events the head ref is the feature branch.
    branch = (
        (pull_request.get("head") or {}).get("ref")
        or default_branch
    )

    # ── Commit SHA ────────────────────────────────────────────────────────
    commit_sha = head_commit.get("id") or head_commit.get("sha") or ""

    # ── Changed files ─────────────────────────────────────────────────────
    # The gateway may inject a ``changed_files`` list; otherwise fall back to
    # the ``files`` field used by some webhook simulators.
    raw_files = (
        payload.get("changed_files")
        or payload.get("files")
        or []
    )
    changed_files = [
        f.get("filename")
        for f in raw_files
        if isinstance(f, dict) and f.get("filename")
    ]

    # ── Diff ──────────────────────────────────────────────────────────────
    # Build a unified diff string from per-file patches so the embedding
    # model receives the actual code changes, not just filenames.
    diff_parts = []
    for f in raw_files:
        if not isinstance(f, dict):
            continue
        filename = f.get("filename", "")
        patch = f.get("patch", "")
        if filename and patch:
            diff_parts.append(f"--- a/{filename}\n+++ b/{filename}\n{patch}")
    diff_str = "\n".join(diff_parts)

    return {
        "full_name": full_name,
        "clone_url": clone_url,
        "default_branch": default_branch,
        "branch": branch,
        "commit_sha": commit_sha,
        "changed_files": changed_files,
        "diff": diff_str,
    }


def _check_and_trigger_indexing(
    full_name: str,
    clone_url: str,
    branch: str,
    default_branch: str,
) -> str:
    """
    Checks the indexing status for *full_name* in the Repository Context
    Service and, when the repository has never been indexed, triggers
    background indexing via the existing ``POST /repository/index`` endpoint.

    Returns one of:
        "ready"               – indexed and completed, safe to search
        "indexing_in_progress" – indexing is currently running (or was just triggered)
        "index_check_failed"  – could not reach the status endpoint
    """
    # URL-encode the full_name so slashes don't break the path segment
    import urllib.parse
    encoded_name = urllib.parse.quote(full_name, safe="")
    status_url = f"{REPOSITORY_CONTEXT_URL}/repository/status/{encoded_name}"

    try:
        res = requests.get(status_url, params={"branch": branch}, timeout=5.0)
        if res.status_code != 200:
            logger.warning(
                "[code-risk] Could not retrieve index status for %s (HTTP %s)",
                full_name, res.status_code
            )
            return "index_check_failed"

        data = res.json()
        status = data.get("status", "not_indexed")

    except Exception as exc:
        logger.warning("[code-risk] Failed to check index status for %s: %s", full_name, exc)
        return "index_check_failed"

    if status == "completed":
        logger.info("[code-risk] Repository %s (branch: %s) is indexed and ready.", full_name, branch)
        return "ready"

    if status == "indexing":
        logger.info(
            "[code-risk] Repository %s (branch: %s) is currently being indexed.",
            full_name, branch
        )
        return "indexing_in_progress"

    # status == "not_indexed" or anything unexpected — trigger indexing
    logger.info(
        "[code-risk] Repository %s (branch: %s) not yet indexed (status=%r). "
        "Triggering background indexing now.",
        full_name, branch, status
    )

    # Use clone_url when available; derive a best-effort HTTPS URL from full_name otherwise.
    effective_clone_url = clone_url or f"https://github.com/{full_name}.git"

    index_body = {
        "repository_url": effective_clone_url,
        "clone_url": effective_clone_url,
        "branch": default_branch,          # index the default branch
        "repository_full_name": full_name,  # authoritative identifier
    }

    try:
        idx_res = requests.post(
            f"{REPOSITORY_CONTEXT_URL}/repository/index",
            json=index_body,
            timeout=5.0,
        )
        if idx_res.status_code == 202:
            logger.info(
                "[code-risk] Indexing triggered for %s (branch: %s).",
                full_name, default_branch
            )
        else:
            logger.warning(
                "[code-risk] Index trigger returned unexpected status %s for %s.",
                idx_res.status_code, full_name
            )
    except Exception as exc:
        logger.warning("[code-risk] Failed to trigger indexing for %s: %s", full_name, exc)

    return "indexing_in_progress"


class RepositoryEvidenceProvider:
    @staticmethod
    def get_repository_evidence(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Retrieves repository source evidence from the Repository Context Service.

        Behaviour
        ---------
        1. Extracts ``repository.full_name``, ``repository.clone_url``,
           ``repository.default_branch``, ``head_commit.id``, and changed-file
           paths from the GitHub webhook payload.
        2. Uses ``full_name`` (e.g. ``"acme/my-service"``) as the canonical
           repository identifier — never strips the owner prefix.
        3. Checks Redis/Qdrant index status via the context service before
           searching:
               - ``completed``  → proceed with the semantic context call.
               - ``indexing``   → returns an explicit ``indexing_in_progress``
                                  status immediately; does **not** search an
                                  empty collection.
               - ``not_indexed``→ triggers background indexing and returns
                                  ``indexing_in_progress``.
        4. Passes the full unified diff (assembled from per-file patches) to
           the ``/repository/context`` endpoint so the embedding captures the
           actual code changes rather than just filenames.
        5. Returns repository metadata (full_name, branch, commit) in every
           returned snippet and in the top-level metrics dict.

        Returns a tuple of ``(evidence_list, metrics)``.
        Does not raise exceptions; returns empty evidence on failure.
        """
        metrics = {
            "retrieval_latency_ms": 0.0,
            "retrieved_chunks": 0,
            "total_characters": 0,
            "context_truncated": False,
            "repository_context_available": False,
            "branch_filter_used": False,
            "fallback_used": False,
            "top_similarity": 0.0,
            "average_similarity": 0.0,
            "unique_files": 0,
            "retrieved_paths": [],
            "ranking_strategy": "unknown",
            "embedding_latency_ms": 0.0,
            "search_latency_ms": 0.0,
            "index_status": "unknown",
        }

        # ── 1. Extract webhook fields ──────────────────────────────────────
        fields = _extract_webhook_repo_fields(payload)
        full_name = fields["full_name"]
        clone_url = fields["clone_url"]
        default_branch = fields["default_branch"]
        branch = fields["branch"]
        commit_sha = fields["commit_sha"]
        changed_files = fields["changed_files"]
        diff_str = fields["diff"]

        # Enrich metrics with repository identity for observability
        metrics["repository"] = full_name
        metrics["branch"] = branch
        metrics["commit"] = commit_sha
        metrics["clone_url"] = clone_url
        metrics["default_branch"] = default_branch

        if not full_name:
            logger.info("Repository context skipped: repository full_name not found in payload")
            _log_metrics(metrics)
            return [], metrics

        if not changed_files:
            logger.info("Repository context skipped: no changed files in payload")
            _log_metrics(metrics)
            return [], metrics

        # ── 2. Check index status and auto-trigger if needed ───────────────
        repo_context_started = time.time()
        repo_context_started_iso = datetime.datetime.fromtimestamp(
            repo_context_started, datetime.timezone.utc
        ).isoformat()
        metrics["repository_context_started_at"] = repo_context_started_iso

        index_status = _check_and_trigger_indexing(full_name, clone_url, branch, default_branch)
        metrics["index_status"] = index_status

        if index_status == "indexing_in_progress":
            logger.info(
                "[code-risk] Skipping context retrieval for %s: indexing in progress. "
                "Evidence will be available on the next webhook event.",
                full_name
            )
            metrics["repository_context_available"] = False
            _log_metrics(metrics)
            return [], metrics

        # index_check_failed: fall through and attempt the search anyway —
        # the service may still have stale but useful vectors.
        if index_status == "index_check_failed":
            logger.warning(
                "[code-risk] Index status check failed for %s; attempting context retrieval anyway.",
                full_name
            )

        # ── 3. Wait for embedding model readiness ──────────────────────────
        ready = wait_for_readiness()
        if not ready:
            logger.warning("[code-risk] Skipping repository context request: service is not ready")
            metrics["repository_context_available"] = False
            _log_metrics(metrics)
            return [], metrics

        repo_context_ready_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        metrics["repository_context_ready_at"] = repo_context_ready_iso

        # ── 4. Build and send context request ─────────────────────────────
        # Collect additional PR context for richer semantic queries
        pull_request = payload.get("pull_request") or {}
        head_commit = payload.get("head_commit") or {}
        pr_title = pull_request.get("title") or ""
        pr_description = pull_request.get("body") or ""
        commit_message = head_commit.get("message") or ""

        request_body = {
            "repository": full_name,       # always the full owner/repo identifier
            "branch": branch,
            "commit": commit_sha,          # for traceability in returned metadata
            "clone_url": clone_url,
            "default_branch": default_branch,
            "changed_files": changed_files,
            "diff": diff_str,              # actual unified diff for semantic retrieval
            "pr_title": pr_title,
            "pr_description": pr_description,
            "commit_message": commit_message,
        }

        url = f"{REPOSITORY_CONTEXT_URL}/repository/context"
        logger.info(
            "Repository context request started: URL=%s, Repository=%s, Branch=%s, Commit=%s, Files=%d",
            url, full_name, branch, commit_sha or "N/A", len(changed_files)
        )
        logger.info("Diff length: %d characters", len(diff_str))

        start_time = time.perf_counter()
        try:
            response = requests.post(
                url,
                json=request_body,
                timeout=REPOSITORY_CONTEXT_TIMEOUT
            )

            logger.info("HTTP Status: %s", response.status_code)
            logger.info("Response Body: %s", response.text[:2000])  # truncate for log safety
            logger.info("Response Headers: %s", response.headers)

            latency = (time.perf_counter() - start_time) * 1000
            metrics["retrieval_latency_ms"] = round(latency, 2)

            if response.status_code != 200:
                logger.warning(
                    "Repository context unavailable (HTTP Status %s). Latency: %s ms",
                    response.status_code,
                    metrics["retrieval_latency_ms"]
                )
                _log_metrics(metrics)
                return [], metrics

            # ── 5. Parse response ──────────────────────────────────────────
            result_json = response.json()
            logger.info("Parsed JSON keys: %s", list(result_json.keys()))
            evidence_list = result_json.get("results")

            res_metrics = result_json.get("metrics") or {}
            # Preserve client-side roundtrip latency; merge service-side metrics
            client_latency = metrics["retrieval_latency_ms"]
            metrics.update(res_metrics)
            metrics["retrieval_latency_ms"] = client_latency
            # Re-apply identity fields in case the service overrode them
            metrics["repository"] = full_name
            metrics["branch"] = branch
            metrics["commit"] = commit_sha
            metrics["index_status"] = index_status

            logger.info(
                "Length of results: %s",
                len(evidence_list) if isinstance(evidence_list, list) else 0
            )
            if isinstance(evidence_list, list) and len(evidence_list) > 0:
                logger.info("First result: %s", evidence_list[0])

            if not isinstance(evidence_list, list):
                logger.warning("Repository context unavailable: malformed response JSON (results is not a list)")
                _log_metrics(metrics)
                return [], metrics

            metrics["retrieved_chunks"] = len(evidence_list)
            metrics["repository_context_available"] = len(evidence_list) > 0

            logger.info(
                "Repository context retrieved. Repository=%s, Chunks=%d, Latency=%.1f ms",
                full_name, len(evidence_list), metrics["retrieval_latency_ms"]
            )
            _log_metrics(metrics)
            return evidence_list, metrics

        except requests.Timeout:
            latency = (time.perf_counter() - start_time) * 1000
            metrics["retrieval_latency_ms"] = round(latency, 2)
            logger.warning("Repository context timeout after %s ms", metrics["retrieval_latency_ms"])
            _log_metrics(metrics)
            return [], metrics
        except Exception as exc:
            latency = (time.perf_counter() - start_time) * 1000
            metrics["retrieval_latency_ms"] = round(latency, 2)
            logger.warning("Repository context unavailable: error requesting context service: %s", exc)
            _log_metrics(metrics)
            return [], metrics


def _log_metrics(metrics: Dict[str, Any]) -> None:
    """Emits a concise structured log line summarising context retrieval metrics."""
    logger.info(
        "[code-risk] context metrics | repo=%s branch=%s commit=%s "
        "index_status=%s available=%s chunks=%d latency=%.1fms",
        metrics.get("repository", ""),
        metrics.get("branch", ""),
        metrics.get("commit", ""),
        metrics.get("index_status", "unknown"),
        metrics.get("repository_context_available", False),
        metrics.get("retrieved_chunks", 0),
        metrics.get("retrieval_latency_ms", 0.0),
    )
