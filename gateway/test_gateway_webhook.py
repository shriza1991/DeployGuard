"""
Unit & Integration Tests for Gateway Webhook Event Filtering
Verifies filtering of GitHub pull_request events vs push and unrelated event types.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure gateway directory is on sys.path
GATEWAY_DIR = os.path.dirname(os.path.abspath(__file__))
if GATEWAY_DIR not in sys.path:
    sys.path.insert(0, GATEWAY_DIR)

# Mock KafkaProducer and redis before importing app/webhook router to prevent connection attempts during test setup
with patch("kafka.KafkaProducer") as mock_kafka_cls, patch("redis.Redis.from_url") as mock_redis_cls:
    from app import app
    from routers import webhook

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_external_dependencies():
    """Mock Kafka producer and Redis client for isolated unit testing."""
    mock_producer = MagicMock()
    mock_redis = MagicMock()
    
    with patch.object(webhook, "producer", mock_producer), \
         patch.object(webhook, "_get_redis", return_value=mock_redis), \
         patch("logging.info") as mock_log_info:
        yield {
            "producer": mock_producer,
            "redis": mock_redis,
            "log": mock_log_info,
        }


def test_pr_opened_event_triggers_analysis(mock_external_dependencies):
    """PR opened event should publish to Kafka and return status: sent."""
    payload = {
        "action": "opened",
        "repository": {"full_name": "shriza1991/DeployGuard"},
        "pull_request": {
            "title": "feat: new feature",
            "body": "adding security scanner",
            "head": {"ref": "feature/sec-scan"}
        },
        "head_commit": {"id": "sha12345", "message": "feat: new feature"}
    }
    headers = {"X-GitHub-Event": "pull_request"}

    response = client.post("/webhook/github", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "sent"
    assert "correlation_id" in data
    assert data["topic"] == "deployment-events"

    # Verify 1 Kafka event published
    producer = mock_external_dependencies["producer"]
    assert producer.send.call_count == 1
    assert producer.flush.call_count == 1


def test_pr_synchronize_event_triggers_new_analysis(mock_external_dependencies):
    """
    Subsequent commits to an existing PR (synchronize) should trigger a NEW analysis
    with a distinct correlation_id.
    """
    producer = mock_external_dependencies["producer"]

    # 1. First payload: PR Creation (opened)
    opened_payload = {
        "action": "opened",
        "repository": {"full_name": "shriza1991/DeployGuard"},
        "pull_request": {"title": "feat: PR initial commit", "head": {"ref": "feature/branch-1"}},
        "head_commit": {"id": "commit1", "message": "initial commit"}
    }
    headers = {"X-GitHub-Event": "pull_request"}
    resp1 = client.post("/webhook/github", json=opened_payload, headers=headers)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["status"] == "sent"
    corr_id_1 = data1["correlation_id"]

    # 2. Second payload: New commit pushed to same PR (synchronize)
    sync_payload = {
        "action": "synchronize",
        "repository": {"full_name": "shriza1991/DeployGuard"},
        "pull_request": {"title": "feat: PR initial commit", "head": {"ref": "feature/branch-1"}},
        "head_commit": {"id": "commit2", "message": "subsequent commit"}
    }
    resp2 = client.post("/webhook/github", json=sync_payload, headers=headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["status"] == "sent"
    corr_id_2 = data2["correlation_id"]

    # Verify both resulted in deployment analyses with distinct correlation IDs
    assert corr_id_1 != corr_id_2
    assert producer.send.call_count == 2


def test_pr_reopened_event_triggers_analysis(mock_external_dependencies):
    """PR reopened event should be processed and published to Kafka."""
    payload = {
        "action": "reopened",
        "repository": {"full_name": "shriza1991/DeployGuard"},
        "pull_request": {"title": "reopen PR"}
    }
    headers = {"X-GitHub-Event": "pull_request"}
    response = client.post("/webhook/github", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"
    assert mock_external_dependencies["producer"].send.call_count == 1


def test_push_event_ignored(mock_external_dependencies):
    """GitHub push events must be ignored without publishing to Kafka."""
    payload = {
        "ref": "refs/heads/main",
        "head_commit": {"id": "sha999", "message": "direct push to main"}
    }
    headers = {"X-GitHub-Event": "push"}

    response = client.post("/webhook/github", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ignored"
    assert "push" in data["reason"].lower()

    # Kafka send MUST NOT be called
    assert mock_external_dependencies["producer"].send.call_count == 0


def test_unrelated_event_type_ignored(mock_external_dependencies):
    """Unrelated GitHub event types (ping, issues, etc.) must be ignored."""
    payload = {"zen": "Non-blocking is better than blocking."}
    headers = {"X-GitHub-Event": "ping"}

    response = client.post("/webhook/github", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ignored"
    assert "ping" in data["reason"].lower()
    assert mock_external_dependencies["producer"].send.call_count == 0


def test_unsupported_pr_action_ignored(mock_external_dependencies):
    """Pull request events with unsupported actions (closed, labeled, edited) must be ignored."""
    for unsupported_action in ["closed", "labeled", "unlabeled", "edited", "assigned"]:
        payload = {
            "action": unsupported_action,
            "pull_request": {"title": "some pr"}
        }
        headers = {"X-GitHub-Event": "pull_request"}

        response = client.post("/webhook/github", json=payload, headers=headers)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ignored"
        assert unsupported_action in data["reason"]

    assert mock_external_dependencies["producer"].send.call_count == 0


def test_missing_header_fallback_pr(mock_external_dependencies):
    """If X-GitHub-Event header is missing but pull_request object is present, treat as PR event."""
    payload = {
        "action": "opened",
        "pull_request": {"title": "fallback pr"}
    }
    response = client.post("/webhook/github", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"
    assert mock_external_dependencies["producer"].send.call_count == 1


def test_missing_header_fallback_push(mock_external_dependencies):
    """If X-GitHub-Event header is missing and pull_request object is missing, ignore as push/other."""
    payload = {
        "head_commit": {"id": "123"}
    }
    response = client.post("/webhook/github", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ignored"
    assert mock_external_dependencies["producer"].send.call_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
