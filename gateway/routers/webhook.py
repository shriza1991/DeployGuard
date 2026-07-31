
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import redis
import requests
from fastapi import APIRouter, Header

from kafka import KafkaProducer
from pydantic import BaseModel

router = APIRouter(
    prefix="/webhook",
    tags=["GitHub Webhook"]
)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOPIC = "deployment-events"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
META_TTL_SECONDS = 7200  # 2 hours — longer than the 1-hour decision TTL

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
)

# Lazy Redis client — connect once at first use so the gateway can start even
# if Redis is momentarily unavailable during container startup.
_redis_client: redis.Redis | None = None

def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _redis_client

logging.basicConfig(level=logging.INFO)


class GitHubWebhookPayload(BaseModel):
    repository: dict | None = None
    action: str | None = None
    sender: dict | None = None
    head_commit: dict | None = None
    pull_request: dict | None = None
    changed_files: list[dict] | None = None
    number: int | None = None
    commit_message: str | None = None
    files: list[dict] | None = None
    deterministic_findings: list[dict] | None = None
    repository_context: list[dict] | None = None
    repository_evidence: list[dict] | None = None


def _fetch_pull_request_files(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch PR file patches once before publishing the event to Kafka."""
    existing_files = payload.get("changed_files")
    if isinstance(existing_files, list) and any(
        isinstance(item, dict) and item.get("patch") for item in existing_files
    ):
        return existing_files

    repository = payload.get("repository") or {}
    pull_request = payload.get("pull_request") or {}
    full_name = str(repository.get("full_name") or "")
    owner, _, repo = full_name.partition("/")
    if not repo:
        repo = str(repository.get("name") or "")
        repo_owner = repository.get("owner") or {}
        owner = str(repo_owner.get("login") or repo_owner.get("name") or "") if isinstance(repo_owner, dict) else ""

    pr_number = pull_request.get("number") or payload.get("number")
    if not owner or not repo or not pr_number:
        return existing_files if isinstance(existing_files, list) else []

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "DeployGuard-Gateway/1.0"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    files: list[dict[str, Any]] = []
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    page = 1
    try:
        while True:
            response = requests.get(url, headers=headers, params={"per_page": 100, "page": page}, timeout=10)
            response.raise_for_status()
            batch = response.json()
            if not isinstance(batch, list):
                break
            files.extend(item for item in batch if isinstance(item, dict))
            if len(batch) < 100:
                break
            page += 1
    except requests.RequestException as exc:
        logging.warning("Unable to enrich PR #%s with changed-file patches: %s", pr_number, exc)
        return existing_files if isinstance(existing_files, list) else []
    return files


def _enrich_deployment_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Populate the shared deployment-event contract for every agent."""
    head_commit = payload.get("head_commit") or {}
    if not payload.get("commit_message") and isinstance(head_commit, dict):
        payload["commit_message"] = head_commit.get("message") or ""

    files = _fetch_pull_request_files(payload)
    if files:
        payload["changed_files"] = files

    pull_request = payload.get("pull_request") or {}
    changed_files = payload.get("changed_files") or []
    logging.info(
        "Deployment payload enriched: pr_title=%s pr_body=%s commit_message=%s changed_files=%d patches=%d",
        bool(isinstance(pull_request, dict) and pull_request.get("title")),
        bool(isinstance(pull_request, dict) and pull_request.get("body")),
        bool(payload.get("commit_message")),
        len(changed_files),
        sum(1 for item in changed_files if isinstance(item, dict) and item.get("patch")),
    )
    return payload


@router.post("/github")
async def github_webhook(
    payload: GitHubWebhookPayload,
    x_github_event: str | None = Header(None, alias="X-GitHub-Event")
):
    # 1. Determine event type (header preferred, fallback to payload structure)
    if x_github_event is not None:
        event_type = x_github_event.strip().lower()
    else:
        if payload.pull_request is not None:
            event_type = "pull_request"
        else:
            event_type = "push"

    if event_type != "pull_request":
        reason = f"Ignored GitHub webhook event type '{event_type}' (DeployGuard only processes 'pull_request' events)"
        logging.info(f"Webhook ignored: {reason}")
        return {
            "status": "ignored",
            "reason": reason,
        }

    # 2. Filter actions for pull_request events (only opened, reopened, synchronize)
    raw_action = payload.action
    action = raw_action.strip().lower() if raw_action else "opened"
    allowed_actions = {"opened", "reopened", "synchronize"}

    if action not in allowed_actions:
        reason = f"Ignored pull_request event with action '{raw_action or action}' (only opened, reopened, and synchronize actions are processed)"
        logging.info(f"Webhook ignored: {reason}")
        return {
            "status": "ignored",
            "reason": reason,
        }

    # Normalize action on payload for metadata persistence
    payload.action = action

    t_webhook_start = time.perf_counter()
    webhook_received_at = datetime.now(timezone.utc).isoformat()
    correlation_id = str(uuid.uuid4())

    deployment_payload = _enrich_deployment_payload(payload.model_dump())
    event = {
        "correlation_id": correlation_id,
        "webhook_received_at": webhook_received_at,
        "payload": deployment_payload,
    }

    logging.info("Publishing deployment event:")
    logging.info(json.dumps(event, indent=2))

    producer.send(TOPIC, event)
    producer.flush()

    webhook_ms = round((time.perf_counter() - t_webhook_start) * 1000.0, 2)
    logging.info("Successfully published to Kafka in %.2f ms", webhook_ms)

    # --- Persist webhook metadata to Redis so the REST API can enrich responses ---
    try:
        repo = payload.repository or {}
        head_commit = payload.head_commit or {}
        pull_request = payload.pull_request or {}
        sender = payload.sender or {}

        # Derive author: prefer head_commit.author.name, fall back to sender.login
        commit_author_obj = head_commit.get("author") or {}
        author = (
            commit_author_obj.get("name")
            or commit_author_obj.get("login")
            or sender.get("login")
            or "unknown"
        )

        # Derive PR user login
        pr_user = pull_request.get("user") or {}

        meta = {
            "correlation_id": correlation_id,
            "repository": repo.get("full_name") or repo.get("name") or "unknown",
            "branch": pull_request.get("head", {}).get("ref") if pull_request.get("head") else None,
            "commit_sha": head_commit.get("id", ""),
            "commit_message": head_commit.get("message", ""),
            "author": author,
            "pull_request_title": pull_request.get("title", ""),
            "pull_request_body": pull_request.get("body", ""),
            "pr_user_login": pr_user.get("login", ""),
            "action": payload.action or "",
            "webhook_received_at": webhook_received_at,
            "webhook_ms": webhook_ms,
        }


        # branch fallback: if no PR head ref, use ref from sender or leave as ""
        if not meta["branch"]:
            meta["branch"] = ""

        redis_client = _get_redis()
        redis_client.set(
            f"meta:{correlation_id}",
            json.dumps(meta),
            ex=META_TTL_SECONDS,
        )
        logging.info(f"Saved deployment meta for correlation_id {correlation_id}")
    except Exception as exc:
        # Metadata write failure must never block the main pipeline
        logging.warning(f"Failed to save deployment meta to Redis for {correlation_id}: {exc}")

    return {
        "status": "sent",
        "correlation_id": correlation_id,
        "topic": TOPIC,
    }
