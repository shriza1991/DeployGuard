from __future__ import annotations

import logging
import time

from incident_history.models import SimilarIncident
from incident_history.retrieval.ranking import rank_incidents

logger = logging.getLogger("incident-history-agent")


class IncidentRetriever:
    def __init__(self, vector_store, top_k: int = 5, similarity_threshold: float = 0.75):
        self.vector_store = vector_store
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    def search(self, query_vector: list[float]) -> tuple[list[SimilarIncident], dict[str, object]]:
        started = time.perf_counter()
        logger.info(
            "Qdrant search started query_vector_dimension=%s top_k=%s threshold=%s",
            len(query_vector), self.top_k, self.similarity_threshold,
        )
        hits = self.vector_store.search_incidents(query_vector, self.top_k)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        all_scores = [round(float(hit.get("score", 0.0) or 0.0), 4) for hit in hits]
        incidents = [
            SimilarIncident.from_qdrant_hit(hit)
            for hit in hits
            if float(hit.get("score", 0.0) or 0.0) >= self.similarity_threshold
        ]
        ranked = rank_incidents(incidents)
        logger.info(
            "Qdrant search completed latency=%sms raw_hits=%s retrieved=%s threshold=%s scores=%s",
            latency_ms, len(hits), len(ranked), self.similarity_threshold, all_scores,
        )
        return ranked, {"latency_ms": latency_ms, "raw_hits": len(hits)}

