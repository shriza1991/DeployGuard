import json
import logging
import os
import uuid

from fastapi import APIRouter
from kafka import KafkaProducer
from pydantic import BaseModel

router = APIRouter(
    prefix="/webhook",
    tags=["GitHub Webhook"]
)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
TOPIC = "deployment-events"

producer = KafkaProducer(
    bootstrap_servers=[KAFKA_BROKER],
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
)

logging.basicConfig(level=logging.INFO)


class GitHubWebhookPayload(BaseModel):
    repository: dict | None = None
    action: str |None = None
    sender: dict | None = None
    head_commit: dict | None = None
    pull_request: dict | None = None


@router.post("/github")
async def github_webhook(payload: GitHubWebhookPayload):
    correlation_id = str(uuid.uuid4())

    event = {
        "correlation_id": correlation_id,
        "payload": payload.model_dump(),   # use .dict() if you're on Pydantic v1
    }

    logging.info(f"Publishing event: {event}")

    producer.send(TOPIC, event)
    producer.flush()

    logging.info("Successfully published to Kafka")

    return {
        "status": "sent",
        "correlation_id": correlation_id,
        "topic": TOPIC,
    }