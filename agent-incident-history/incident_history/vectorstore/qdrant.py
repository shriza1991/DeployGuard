from __future__ import annotations

import logging
import time
from typing import Any

import requests

from incident_history.models import IncidentDocument
from incident_history.utils import stable_int_id

logger = logging.getLogger("incident-history-agent")


class QdrantVectorStore:
    def __init__(self, url: str, collection: str, timeout_seconds: float = 3.0, retries: int = 2):
        self.url = url.rstrip("/")
        self.collection = collection
        self.timeout_seconds = timeout_seconds
        self.retries = max(0, retries)

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.url}/health", timeout=self.timeout_seconds)
            return response.status_code < 500
        except requests.RequestException:
            return False

    def collection_exists(self) -> bool:
        try:
            response = requests.get(
                f"{self.url}/collections/{self.collection}",
                timeout=self.timeout_seconds,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def create_collection(self, vector_size: int) -> bool:
        payload = {"vectors": {"size": vector_size, "distance": "Cosine"}}
        try:
            response = self._request("put", f"/collections/{self.collection}", json=payload)
            return response is not None and response.status_code in {200, 201}
        except requests.RequestException:
            logger.warning("Qdrant collection creation failed", exc_info=True)
            return False

    def ensure_collection(self, vector_size: int) -> bool:
        if self.collection_exists():
            return True
        return self.create_collection(vector_size)

    def insert_incident(self, incident: IncidentDocument) -> bool:
        if not incident.embedding:
            raise ValueError("incident embedding is required")
        self.ensure_collection(len(incident.embedding))
        point_id = stable_int_id(incident.incident_id)
        payload = {
            "points": [
                {
                    "id": point_id,
                    "vector": incident.embedding,
                    "payload": incident.payload(),
                }
            ]
        }
        response = self._request("put", f"/collections/{self.collection}/points", json=payload)
        return response is not None and response.status_code in {200, 201}

    def delete_incident(self, incident_id: str) -> bool:
        payload = {"points": [stable_int_id(incident_id)]}
        response = self._request("post", f"/collections/{self.collection}/points/delete", json=payload)
        return response is not None and response.status_code in {200, 202}

    def search_incidents(self, vector: list[float], top_k: int) -> list[dict[str, Any]]:
        payload = {
            "vector": vector,
            "limit": top_k,
            "with_payload": True,
            "with_vector": False,
        }

        response = self._request(
            "post",
            f"/collections/{self.collection}/points/search",
            json=payload,
        )

        if response is None:
            logger.error("No response from Qdrant")
            return []

        logger.info("Qdrant Status: %s", response.status_code)

        data = response.json()

        logger.info("Raw Qdrant Response:\n%s", data)

        return data.get("result") or []

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response | None:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = requests.request(
                    method,
                    f"{self.url}{path}",
                    timeout=self.timeout_seconds,
                    **kwargs,
                )
                if response.status_code < 500:
                    return response
                logger.warning("Qdrant returned status %s for %s", response.status_code, path)
            except requests.RequestException as exc:
                last_error = exc
                logger.warning("Qdrant request failed (attempt %s/%s): %s", attempt + 1, self.retries + 1, exc)
            if attempt < self.retries:
                time.sleep(0.2 * (attempt + 1))
        if last_error:
            raise last_error
        return None

