from __future__ import annotations

import logging
import time
from typing import Any

from incident_history.config import Settings
from incident_history.embeddings import get_embedding_provider
from incident_history.llm import IncidentLLMReasoner, get_llm_provider
from incident_history.models import SimilarIncident
from incident_history.retrieval import IncidentRetriever
from incident_history.utils import build_deployment_document, clamp
from incident_history.vectorstore import QdrantVectorStore

logger = logging.getLogger("incident-history-agent")


class IncidentHistoryService:
    def __init__(self, embedding_provider, vector_store, retriever, llm_reasoner):
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.retriever = retriever
        self.llm_reasoner = llm_reasoner
        self.start_time = time.time()
        self.analysis_count = 0
        self.last_run_timestamp = None
        self.total_latency_ms = 0.0
        self.total_confidence = 0.0
        self.version = "1.0.0"

    def analyze_event(self, payload: dict[str, Any], correlation_id: str | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        confidence_val = 0.0
        try:
            result = self._analyze_event_internal(payload, correlation_id, started)
            confidence_val = result.get("confidence", 0.0)
            return result
        except Exception as exc:
            fallback = self._fallback_output(
                correlation_id=correlation_id,
                reason=f"Unexpected error: {exc}",
                recommendation="Check the service logs.",
                metadata={"error": str(exc)},
            )
            confidence_val = fallback.get("confidence", 0.0)
            return fallback
        finally:
            import datetime
            total_latency_ms = (time.perf_counter() - started) * 1000.0
            self.analysis_count += 1
            self.last_run_timestamp = datetime.datetime.utcnow().isoformat() + "Z"
            self.total_latency_ms += total_latency_ms
            self.total_confidence += confidence_val

    def _analyze_event_internal(self, payload: dict[str, Any], correlation_id: str | None, started: float) -> dict[str, Any]:
        deployment_document = build_deployment_document(payload)
        if not deployment_document:
            deployment_document = "empty deployment event"

        incidents: list[SimilarIncident] = []
        retrieval_metadata: dict[str, Any] = {"latency_ms": 0, "raw_hits": 0}
        qdrant_available = False
        embedding_quality = "unavailable"

        try:
            embed_started = time.perf_counter()
            logger.info("Embedding generation started")
            query_vector = self.embedding_provider.embed(deployment_document)
            embedding_latency_ms = round((time.perf_counter() - embed_started) * 1000, 2)
            embedding_quality = "ok" if any(query_vector) else "empty"
            logger.info(
                "Embedding generation completed latency=%sms dimension=%s quality=%s",
                embedding_latency_ms, len(query_vector), embedding_quality,
            )
        except Exception as exc:
            logger.warning("Embedding fallback activated: %s", exc)
            return self._fallback_output(
                correlation_id=correlation_id,
                reason="Embedding generation failed.",
                recommendation="Retry historical analysis after the embedding provider is healthy.",
                metadata={
                    "error": str(exc),
                    "embedding_provider": getattr(self.embedding_provider, "name", "unknown"),
                    "query_text": deployment_document,
                    "qdrant_available": False,
                    "embedding_quality": "failed",
                },
            )

        try:
            qdrant_available = self.vector_store.health_check()
            if not qdrant_available:
                raise RuntimeError("Qdrant health check failed")
            incidents, retrieval_metadata = self.retriever.search(query_vector)
        except Exception as exc:
            logger.warning("Qdrant fallback activated: %s", exc)
            qdrant_available = False

        deterministic = self._deterministic_result(
            incidents=incidents,
            qdrant_available=qdrant_available,
            embedding_quality=embedding_quality,
            retrieval_metadata=retrieval_metadata,
            query_text=deployment_document,
        )

        llm_result = self.llm_reasoner.analyze(deployment_document, deterministic, incidents)
        total_latency_ms = round((time.perf_counter() - started) * 1000, 2)
        deterministic["metadata"]["total_latency_ms"] = total_latency_ms
        logger.info("Incident history processing completed latency=%sms", total_latency_ms)

        return {
            "agent": "incident-history",
            "correlation_id": correlation_id,
            "score": deterministic["score"],
            "severity": deterministic["severity"],
            "confidence": deterministic["confidence"],
            "reasons": deterministic["reasons"],
            "recommendations": _merge_recommendations(
                deterministic["recommendations"],
                llm_result.recommendations,
            ),
            "metadata": deterministic["metadata"],
            "similar_incidents": [incident.output() for incident in incidents],
            "llm": llm_result.output(),
        }

    def _deterministic_result(
        self,
        incidents: list[SimilarIncident],
        qdrant_available: bool,
        embedding_quality: str,
        retrieval_metadata: dict[str, Any],
        query_text: str,
    ) -> dict[str, Any]:
        score = _score_incidents(incidents, qdrant_available)
        severity = _severity(score)
        confidence = _confidence(incidents, qdrant_available, embedding_quality)
        reasons = _reasons(incidents, qdrant_available)
        recommendations = _recommendations(score, incidents, qdrant_available)
        return {
            "score": score,
            "severity": severity,
            "confidence": confidence,
            "reasons": reasons,
            "recommendations": recommendations,
            "metadata": {
                "embedding_provider": getattr(self.embedding_provider, "name", "unknown"),
                "embedding_model": getattr(self.embedding_provider, "model_name", getattr(self.embedding_provider, "name", "unknown")),
                "embedding_quality": embedding_quality,
                "matched_incidents": len(incidents),
                "top_similarity": round(incidents[0].similarity, 3) if incidents else 0.0,
                "similarity_scores": [round(item.similarity, 3) for item in incidents],
                "qdrant_available": qdrant_available,
                "qdrant_collection": getattr(self.vector_store, "collection", ""),
                "retrieval": retrieval_metadata,
                "query_text": query_text[:2000],
            },
        }

    def _fallback_output(
        self,
        correlation_id: str | None,
        reason: str,
        recommendation: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "agent": "incident-history",
            "correlation_id": correlation_id,
            "score": 10,
            "severity": "low",
            "confidence": 0.1,
            "reasons": [reason, "No historical incidents available."],
            "recommendations": [recommendation],
            "metadata": metadata,
            "similar_incidents": [],
            "llm": {
                "provider": "unavailable",
                "available": False,
                "summary": "Historical incident analysis is running in fallback mode.",
                "risk_reasoning": [],
                "recommendations": [],
                "confidence": 0.0,
            },
        }


def create_service(settings: Settings) -> IncidentHistoryService:
    embedding_provider = get_embedding_provider(
        settings.embedding_provider,
        settings.embedding_model,
        settings.embedding_dimension,
        settings.embedding_cache_size,
    )
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        collection=settings.qdrant_collection,
        timeout_seconds=settings.qdrant_timeout_seconds,
        retries=settings.qdrant_retries,
    )
    retriever = IncidentRetriever(
        vector_store=vector_store,
        top_k=settings.top_k_results,
        similarity_threshold=settings.similarity_threshold,
    )
    llm_reasoner = IncidentLLMReasoner(get_llm_provider(settings))
    return IncidentHistoryService(embedding_provider, vector_store, retriever, llm_reasoner)


def _score_incidents(incidents: list[SimilarIncident], qdrant_available: bool) -> int:
    if not qdrant_available or not incidents:
        return 10

    # Require similarity >= 0.70 for incident matches to boost score
    high_similarity = [item for item in incidents if item.similarity >= 0.70]
    if not high_similarity:
        return 10

    critical_rollbacks = [
        item for item in high_similarity
        if item.severity == "critical" and (item.rollback or "rollback" in item.outcome)
    ]
    production_failures = [
        item for item in high_similarity
        if item.environment == "production" and item.severity in {"high", "critical"}
    ]

    if len(production_failures) >= 2:
        return 80
    if critical_rollbacks:
        return 70
    if len(high_similarity) >= 2:
        return 50
    if high_similarity:
        return 35
    return 10


def _confidence(incidents: list[SimilarIncident], qdrant_available: bool, embedding_quality: str) -> float:
    if not qdrant_available or embedding_quality == "failed":
        return 0.1
    if not incidents:
        return 0.35
    top_similarity = max(item.similarity for item in incidents)
    metadata_quality = sum(
        1 for item in incidents
        if item.severity and item.environment and item.outcome and item.root_cause
    ) / max(1, len(incidents))
    confidence = 0.35 + min(0.35, top_similarity * 0.35) + min(0.2, len(incidents) * 0.05) + (metadata_quality * 0.1)
    return round(max(0.0, min(1.0, confidence)), 2)


def _severity(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _reasons(incidents: list[SimilarIncident], qdrant_available: bool) -> list[str]:
    if not qdrant_available:
        return ["No historical incidents available."]
    if not incidents:
        return ["No similar historical incidents were found above the configured threshold."]
    reasons = [f"{len(incidents)} similar historical incident(s) matched this deployment."]
    top = incidents[0]
    reasons.append(f"Top incident {top.incident_id} matched with similarity {top.similarity:.2f}.")
    if any(item.severity == "critical" for item in incidents):
        reasons.append("Critical incidents are present in the matching history.")
    if any(item.rollback or "rollback" in item.outcome for item in incidents):
        reasons.append("Matching history includes rollback incidents.")
    if any(item.environment == "production" for item in incidents):
        reasons.append("Matching history includes production incidents.")
    return reasons


def _recommendations(score: int, incidents: list[SimilarIncident], qdrant_available: bool) -> list[str]:
    if not qdrant_available:
        return ["Proceed with deterministic checks; historical incident retrieval is unavailable."]
    recommendations = ["Review similar incidents before approving this deployment."]
    if score >= 60:
        recommendations.append("Prepare rollback criteria and increase monitoring during rollout.")
    if any(item.severity == "critical" for item in incidents):
        recommendations.append("Require senior engineering review for the historically critical failure mode.")
    if any(item.rollback or "rollback" in item.outcome for item in incidents):
        recommendations.append("Validate rollback automation and owner availability before release.")
    return recommendations


def _merge_recommendations(deterministic: list[str], llm: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in deterministic + llm:
        normalized = item.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            merged.append(item)
    return merged

