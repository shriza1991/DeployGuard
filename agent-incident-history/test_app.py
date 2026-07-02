import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app


def test_analyze_incident_history_uses_similarity_and_history_signals(monkeypatch):
    monkeypatch.setattr(
        app,
        "query_qdrant",
        lambda vector: {
            "result": [
                {
                    "score": 0.91,
                    "payload": {
                        "previous_incidents": 2,
                        "rollbacks": 1,
                        "outages": 1,
                        "failed_deployments": 1,
                    },
                }
            ]
        },
    )

    analysis = app.analyze_incident_history(
        {
            "description": "Deploying the payment service after a recent outage",
            "pull_request": {"body": "Please review this rollout carefully"},
        }
    )

    assert analysis["score"] >= 70
    assert analysis["severity"] in {"high", "critical"}
    assert analysis["confidence"] >= 0.5
    assert any("similar" in reason.lower() for reason in analysis["reasons"])
    assert any("rollback" in recommendation.lower() for recommendation in analysis["recommendations"])


def test_analyze_incident_history_handles_missing_history(monkeypatch):
    monkeypatch.setattr(app, "query_qdrant", lambda vector: {"result": []})

    analysis = app.analyze_incident_history({"description": "Routine database migration"})

    assert analysis["score"] <= 60
    assert analysis["severity"] in {"low", "medium"}
    assert analysis["metadata"]["qdrant_available"] is True
    assert analysis["metadata"]["matched_incidents"] == 0
