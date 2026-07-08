import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from incident_history.llm.reasoner import IncidentLLMReasoner
from incident_history.models import SimilarIncident


class FailingProvider:
    name = "gemini"

    def analyze(self, prompt):
        raise RuntimeError("gemini down")


def test_llm_reasoner_falls_back_after_provider_failure():
    reasoner = IncidentLLMReasoner(FailingProvider())
    result = reasoner.analyze(
        "deploy auth change",
        {"score": 55},
        [SimilarIncident("INC-1", 0.91, "critical", "rollback", "Authentication removed")],
    )

    assert result.provider == "gemini"
    assert result.available is False
    assert result.summary

