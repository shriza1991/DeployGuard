import os
import time
import logging
import requests
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("code-risk-agent")

REPOSITORY_CONTEXT_URL = os.getenv("REPOSITORY_CONTEXT_URL", "http://repository-context-service:8003").rstrip("/")
REPOSITORY_CONTEXT_TIMEOUT = float(os.getenv("REPOSITORY_CONTEXT_TIMEOUT", "10.0"))

class RepositoryEvidenceProvider:
    @staticmethod
    def get_repository_evidence(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Retrieves repository source evidence from the Repository Context Service.
        Returns a tuple of (evidence_list, metrics).
        Does not raise exceptions; returns empty evidence list on failure or timeout.
        """
        metrics = {
            "retrieval_latency_ms": 0.0,
            "retrieved_chunks": 0,
            "total_characters": 0,
            "context_truncated": False,
            "repository_context_available": False
        }

        # 1. Parse repository name
        repo_obj = payload.get("repository") or {}
        repo_full_name = repo_obj.get("name") or repo_obj.get("full_name") or ""
        
        # If no repository info exists, try to extract from pull_request URL
        pull_request = payload.get("pull_request") or {}
        if not repo_full_name and pull_request.get("url"):
            # e.g., "https://example.test/pr/1"
            parts = pull_request["url"].rstrip("/").split("/")
            if len(parts) >= 3:
                repo_full_name = parts[-2]

        if not repo_full_name:
            logger.info("Repository context skipped: repository name not found in payload")
            logger.info("Metrics before return: %s", metrics)
            logger.info("retrieved_chunks: %s", metrics.get("retrieved_chunks"))
            logger.info("repository_context_available: %s", metrics.get("repository_context_available"))
            logger.info("total_characters: %s", metrics.get("total_characters"))
            return [], metrics

        # Get base repo name (e.g. "shriza1991/DeployGuard" -> "DeployGuard")
        repo_name = repo_full_name.split("/")[-1]

        # 2. Parse branch name
        branch = pull_request.get("head", {}).get("ref") or "main"

        # 3. Parse changed files list
        files = (
            payload.get("changed_files")
            or payload.get("files")
            or []
        )
        changed_files = [
            f.get("filename") for f in files 
            if isinstance(f, dict) and f.get("filename")
        ]

        if not changed_files:
            logger.info("Repository context skipped: no changed files in payload")
            logger.info("Metrics before return: %s", metrics)
            logger.info("retrieved_chunks: %s", metrics.get("retrieved_chunks"))
            logger.info("repository_context_available: %s", metrics.get("repository_context_available"))
            logger.info("total_characters: %s", metrics.get("total_characters"))
            return [], metrics

        # 4. Compile git diff from file patches
        diff_parts = []
        for f in files:
            if isinstance(f, dict):
                filename = f.get("filename", "")
                patch = f.get("patch", "")
                if filename and patch:
                    diff_parts.append(f"--- a/{filename}\n+++ b/{filename}\n{patch}")
        diff_str = "\n".join(diff_parts)

        # 5. Extract additional PR context
        pr_title = pull_request.get("title") or ""
        pr_description = pull_request.get("body") or ""
        
        head_commit = payload.get("head_commit") or {}
        commit_message = head_commit.get("message") or ""

        # Prepare HTTP request payload (includes full metadata)
        request_body = {
            "repository": repo_name,
            "branch": branch,
            "changed_files": changed_files,
            "diff": diff_str,
            "pr_title": pr_title,
            "pr_description": pr_description,
            "commit_message": commit_message
        }

        # 6. Execute request with strict timeout
        url = f"{REPOSITORY_CONTEXT_URL}/repository/context"
        logger.info("Repository context request started: URL=%s, Repository=%s, Branch=%s", url, repo_name, branch)
        
        start_time = time.perf_counter()
        try:
            response = requests.post(
                url,
                json=request_body,
                timeout=REPOSITORY_CONTEXT_TIMEOUT
            )
            logger.info("HTTP Status: %s", response.status_code)
            logger.info("Response Body: %s", response.text)
            logger.info("Response Headers: %s", response.headers)

            logger.info(
                "Repository context request: url=%s",
                url,
            )
            logger.info(
                "Repository context body:=%s",
                request_body,
            )
            latency = (time.perf_counter() - start_time) * 1000
            metrics["retrieval_latency_ms"] = round(latency, 2)

            if response.status_code != 200:
                logger.warning(
                    "Repository context unavailable (HTTP Status %s). Latency: %s ms",
                    response.status_code,
                    metrics["retrieval_latency_ms"]
                )
                logger.info("Metrics before return: %s", metrics)
                logger.info("retrieved_chunks: %s", metrics.get("retrieved_chunks"))
                logger.info("repository_context_available: %s", metrics.get("repository_context_available"))
                logger.info("total_characters: %s", metrics.get("total_characters"))
                return [], metrics

            # Parse results
            result_json = response.json()
            logger.info("Parsed JSON keys: %s", list(result_json.keys()))
            evidence_list = result_json.get("results")
            logger.info("Length of results: %s", len(evidence_list) if isinstance(evidence_list, list) else 0)
            if isinstance(evidence_list, list) and len(evidence_list) > 0:
                logger.info("First result: %s", evidence_list[0])

            if not isinstance(evidence_list, list):
                logger.warning("Repository context unavailable: malformed response JSON (results is not a list)")
                logger.info("Metrics before return: %s", metrics)
                logger.info("retrieved_chunks: %s", metrics.get("retrieved_chunks"))
                logger.info("repository_context_available: %s", metrics.get("repository_context_available"))
                logger.info("total_characters: %s", metrics.get("total_characters"))
                return [], metrics

            metrics["retrieved_chunks"] = len(evidence_list)
            metrics["repository_context_available"] = True
            
            logger.info(
                "Repository context retrieved. Chunks returned: %s. Latency: %s ms",
                len(evidence_list),
                metrics["retrieval_latency_ms"]
            )
            logger.info("Metrics before return: %s", metrics)
            logger.info("retrieved_chunks: %s", metrics.get("retrieved_chunks"))
            logger.info("repository_context_available: %s", metrics.get("repository_context_available"))
            logger.info("total_characters: %s", metrics.get("total_characters"))
            return evidence_list, metrics

        except requests.Timeout:
            latency = (time.perf_counter() - start_time) * 1000
            metrics["retrieval_latency_ms"] = round(latency, 2)
            logger.warning("Repository context timeout after %s ms", metrics["retrieval_latency_ms"])
            logger.info("Metrics before return: %s", metrics)
            logger.info("retrieved_chunks: %s", metrics.get("retrieved_chunks"))
            logger.info("repository_context_available: %s", metrics.get("repository_context_available"))
            logger.info("total_characters: %s", metrics.get("total_characters"))
            return [], metrics
        except Exception as exc:
            latency = (time.perf_counter() - start_time) * 1000
            metrics["retrieval_latency_ms"] = round(latency, 2)
            logger.warning("Repository context unavailable: error requesting context service: %s", exc)
            logger.info("Metrics before return: %s", metrics)
            logger.info("retrieved_chunks: %s", metrics.get("retrieved_chunks"))
            logger.info("repository_context_available: %s", metrics.get("repository_context_available"))
            logger.info("total_characters: %s", metrics.get("total_characters"))
            return [], metrics
