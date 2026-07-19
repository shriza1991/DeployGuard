
import json
import logging
import os
import uuid

import redis
from fastapi import APIRouter
from kafka import KafkaProducer
from pydantic import BaseModel

router = APIRouter(
    prefix="/webhook",
    tags=["GitHub Webhook"]
)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOPIC = "deployment-events"
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


@router.post("/github")
async def github_webhook(payload: GitHubWebhookPayload):
    correlation_id = str(uuid.uuid4())

    event = {
        "correlation_id": correlation_id,
        "payload": payload.model_dump(),
    }

    logging.info("Publishing deployment event:")
    logging.info(json.dumps(event, indent=2))

    producer.send(TOPIC, event)
    producer.flush()

    logging.info("Successfully published to Kafka")

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