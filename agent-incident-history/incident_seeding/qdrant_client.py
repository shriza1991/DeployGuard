from __future__ import annotations

import logging
import time
from typing import Any

import requests

from incident_history.utils import stable_int_id

from incident_seeding.models import SeedIncident

logger = logging.getLogger("incident-history-seed")


class SeedQdrantClient:
    def __init__(
        self,
        url: str,
        collection: str,
        vector_size: int,
        timeout_seconds: float = 10.0,
        retries: int = 3,
    ):
        self.url = url.rstrip("/")
        self.collection = collection
        self.vector_size = vector_size
        self.timeout_seconds = timeout_seconds
        self.retries = max(0, retries)

    def collection_exists(self) -> bool:
        response = self._request("get", f"/collections/{self.collection}")
        return response is not None and response.status_code == 200

    def recreate_collection(self) -> None:
        logger.info("Recreating collection %s...", self.collection)
        if self.collection_exists():
            delete_response = self._request("delete", f"/collections/{self.collection}")
            if delete_response is None or delete_response.status_code not in {200, 202}:
                raise RuntimeError(f"Failed to delete collection {self.collection}")
        self.create_collection()

    def create_collection(self) -> None:
        logger.info("Creating collection %s...", self.collection)
        payload = {"vectors": {"size": self.vector_size, "distance": "Cosine"}}
        response = self._request("put", f"/collections/{self.collection}", json=payload)
        if response is None or response.status_code not in {200, 201}:
            raise RuntimeError(f"Failed to create collection {self.collection}")

    def ensure_collection(self, reset: bool) -> None:
        if reset:
            self.recreate_collection()
            return
        if not self.collection_exists():
            self.create_collection()
            return
        logger.info("Reusing existing collection %s...", self.collection)

    def existing_incident_ids(self) -> set[str]:
        incident_ids: set[str] = set[str]()
        offset: Any | None = None
        while True:
            payload: dict[str, Any] = {
                "limit": 256,
                "with_payload": ["incident_id"],
                "with_vector": False,
            }
            if offset is not None:
                payload["offset"] = offset
            response = self._request(
                "post",
                f"/collections/{self.collection}/points/scroll",
                json=payload,
            )
            if response is None or response.status_code != 200:
                break
            data = response.json().get("result") or {}
            points = data.get("points") or []
            for point in points:
                point_payload = point.get("payload") or {}
                incident_id = point_payload.get("incident_id")
                if incident_id:
                    incident_ids.add(str(incident_id))
            offset = data.get("next_page_offset")
            if offset is None:
                break
        return incident_ids

    def upsert_incident(self, incident: SeedIncident, vector: list[float]) -> None:
        point_id = stable_int_id(incident.incident_id)
        payload = {
            "points": [
                {
                    "id": point_id,
                    "vector": vector,
                    "payload": incident.payload(),
                }
            ]
        }
        response = self._request("put", f"/collections/{self.collection}/points", json=payload)
        if response is None or response.status_code not in {200, 201}:
            raise RuntimeError(f"Failed to upsert incident {incident.incident_id}")

    def search(self, vector: list[float], top_k: int) -> list[dict[str, Any]]:
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
        if response is None or response.status_code != 200:
            return []
        return response.json().get("result") or []

    def upload_incidents(
        self,
        incidents: list[SeedIncident],
        vectors: dict[str, list[float]],
        skip_existing: bool,
    ) -> tuple[int, int]:
        existing_ids = self.existing_incident_ids() if skip_existing else set()
        inserted = 0
        skipped = 0
        total = len(incidents)

        for index, incident in enumerate(incidents, start=1):
            if skip_existing and incident.incident_id in existing_ids:
                skipped += 1
                logger.info(
                    "Skipping incident %s/%s (%s already exists)...",
                    index,
                    total,
                    incident.incident_id,
                )
                continue
            logger.info("Uploading incident %s/%s...", index, total)
            vector = vectors[incident.incident_id]
            self.upsert_incident(incident, vector)
            inserted += 1

        return inserted, skipped

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
                logger.warning(
                    "Qdrant request failed (attempt %s/%s): %s",
                    attempt + 1,
                    self.retries + 1,
                    exc,
                )
            if attempt < self.retries:
                time.sleep(0.2 * (attempt + 1))
        if last_error:
            raise last_error
        return None
