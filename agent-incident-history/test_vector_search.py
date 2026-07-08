import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from incident_history.retrieval.search import IncidentRetriever


class FakeVectorStore:
    def search_incidents(self, vector, top_k):
        return [
            {"score": 0.6, "payload": {"incident_id": "LOW", "title": "Low"}},
            {
                "score": 0.92,
                "payload": {
                    "incident_id": "HIGH",
                    "title": "Critical rollback",
                    "severity": "critical",
                    "outcome": "rollback",
                    "rollback": True,
                    "environment": "production",
                    "tags": ["security"],
                },
            },
        ]


def test_vector_search_filters_and_ranks_incidents():
    retriever = IncidentRetriever(FakeVectorStore(), top_k=5, similarity_threshold=0.75)

    incidents, metadata = retriever.search([1.0, 0.0])

    assert metadata["raw_hits"] == 2
    assert len(incidents) == 1
    assert incidents[0].incident_id == "HIGH"

