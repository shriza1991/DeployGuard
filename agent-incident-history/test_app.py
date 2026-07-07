import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from incident_history.llm.fallback import FallbackLLMProvider
from incident_history.llm.reasoner import IncidentLLMReasoner
from incident_history.models import SimilarIncident
from incident_history.retrieval.search import IncidentRetriever
from incident_history.service import IncidentHistoryService
from incident_history.utils import build_deployment_document


class FakeEmbeddingProvider:
    name = "fake"
    model_name = "fake"
    dimension = 3

    def embed(self, text):
        return [1.0, 0.0, 0.0]


class FailingEmbeddingProvider(FakeEmbeddingProvider):
    def embed(self, text):
        raise RuntimeError("embedding down")


class FakeVectorStore:
    collection = "incident_history"

    def __init__(self, hits=None, healthy=True):
        self.hits = hits or []
        self.healthy = healthy

    def health_check(self):
        return self.healthy

    def search_incidents(self, vector, top_k):
        return self.hits


def build_service(hits=None, healthy=True, embedding_provider=None):
    vector_store = FakeVectorStore(hits=hits, healthy=healthy)
    retriever = IncidentRetriever(vector_store, top_k=5, similarity_threshold=0.75)
    return IncidentHistoryService(
        embedding_provider or FakeEmbeddingProvider(),
        vector_store,
        retriever,
        IncidentLLMReasoner(FallbackLLMProvider()),
    )


def test_build_deployment_document_combines_searchable_fields():
    document = build_deployment_document(
        {
            "pull_request": {"title": "Remove auth", "body": "Risky rollout"},
            "commit_message": "Delete middleware",
            "changed_files": [{"filename": "auth.py", "patch": "- require_login()"}],
        }
    )

    assert "remove auth" in document
    assert "risky rollout" in document
    assert "delete middleware" in document
    assert "auth.py" in document
    assert "- require_login()" in document
    assert document == document.lower()


def test_service_scores_critical_rollback_history():
    service = build_service(
        hits=[
            {
                "score": 0.93,
                "payload": {
                    "incident_id": "INC-202",
                    "title": "Authentication removed",
                    "severity": "critical",
                    "outcome": "rollback",
                    "rollback": True,
                    "environment": "production",
                    "root_cause": "Auth guard removed",
                    "tags": ["authentication", "security"],
                },
            }
        ]
    )

    result = service.analyze_event({"description": "Remove authentication middleware"}, "corr-1")

    assert result["agent"] == "incident-history"
    assert result["score"] == 90
    assert result["severity"] == "critical"
    assert result["confidence"] >= 0.7
    assert result["similar_incidents"][0]["incident_id"] == "INC-202"
    assert result["llm"]["available"] is False


def test_service_handles_qdrant_unavailable():
    service = build_service(healthy=False)

    result = service.analyze_event({"description": "Routine database migration"}, "corr-2")

    assert result["score"] == 10
    assert result["severity"] == "low"
    assert result["metadata"]["qdrant_available"] is False
    assert result["similar_incidents"] == []
    assert "No historical incidents available." in result["reasons"]


def test_service_handles_embedding_failure():
    service = build_service(embedding_provider=FailingEmbeddingProvider())

    result = service.analyze_event({"description": "Deploy payment service"}, "corr-3")

    assert result["score"] == 10
    assert result["confidence"] == 0.1
    assert result["metadata"]["embedding_quality"] == "failed"
    assert result["similar_incidents"] == []

