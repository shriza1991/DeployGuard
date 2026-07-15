import logging
import time
import requests
import uuid
import hashlib
from typing import Any, List, Dict
from models import CodeChunk

logger = logging.getLogger("repository-context-service")

def get_stable_uuid(value: str) -> str:
    """Generates a stable UUID based on a string value."""
    digest = hashlib.sha1(value.encode("utf-8")).digest()
    return str(uuid.UUID(bytes=digest[:16]))

class QdrantService:
    def __init__(self, url: str, collection: str, timeout_seconds: float = 10.0, retries: int = 3):
        self.url = url.rstrip("/")
        self.collection = collection
        self.timeout_seconds = timeout_seconds
        self.retries = max(0, retries)

    def health_check(self) -> bool:
        """Checks Qdrant connection health."""
        try:
            response = requests.get(f"{self.url}/health", timeout=self.timeout_seconds)
            return response.status_code < 500
        except requests.RequestException:
            return False

    def collection_exists(self) -> bool:
        """Checks if the configured collection exists."""
        try:
            response = requests.get(
                f"{self.url}/collections/{self.collection}",
                timeout=self.timeout_seconds,
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def create_collection(self, vector_size: int) -> bool:
        """Creates the collection with Cosine distance metric."""
        payload = {"vectors": {"size": vector_size, "distance": "Cosine"}}
        try:
            response = self._request("put", f"/collections/{self.collection}", json=payload)
            return response is not None and response.status_code in {200, 201}
        except requests.RequestException:
            logger.warning("Qdrant collection creation failed", exc_info=True)
            return False

    def ensure_collection(self, vector_size: int) -> bool:
        """Checks collection existence and creates if missing."""
        if self.collection_exists():
            return True
        logger.info(f"Creating collection '{self.collection}' in Qdrant (dimension: {vector_size})...")
        return self.create_collection(vector_size)

    def upsert_chunks(self, chunks: List[CodeChunk], embeddings: List[List[float]]) -> bool:
        """
        Upserts a batch of code chunks and their embeddings into Qdrant.
        Uses a stable UUID per chunk to avoid duplicates.
        """
        if not chunks:
            return True

        vector_size = len(embeddings[0])
        self.ensure_collection(vector_size)

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            meta = chunk.metadata
            # Uniquely identify the chunk via its repository, branch, relative file path, and chunk index
            unique_str = f"{meta.repository}:{meta.branch}:{meta.relative_path}:{meta.chunk_index}"
            point_id = get_stable_uuid(unique_str)

            # Build point record
            payload = meta.model_dump()
            payload["text"] = chunk.text

            points.append({
                "id": point_id,
                "vector": embedding,
                "payload": payload
            })

        # Upsert in batches of 100 to avoid huge HTTP requests
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            payload = {"points": batch}
            response = self._request(
                "put",
                f"/collections/{self.collection}/points?wait=true",
                json=payload
            )
            if response is None or response.status_code not in {200, 201}:
                logger.error(f"Failed to upsert points batch {i // batch_size}")
                return False

        logger.info(f"Successfully upserted {len(chunks)} chunks into Qdrant collection: {self.collection}")
        return True

    def delete_by_repository(self, repository: str, branch: str) -> bool:
        """
        Deletes all vector points associated with the given repository and branch.
        """
        payload = {
            "filter": {
                "must": [
                    {
                        "key": "repository",
                        "match": {"value": repository}
                    },
                    {
                        "key": "branch",
                        "match": {"value": branch}
                    }
                ]
            }
        }
        response = self._request(
            "post",
            f"/collections/{self.collection}/points/delete",
            json=payload
        )
        return response is not None and response.status_code in {200, 202}

    def search(self, vector: List[float], repository: str, branch: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Searches the collection for closest vectors matching the repository and branch filters.
        """
        payload = {
            "vector": vector,
            "limit": top_k,
            "filter": {
                "must": [
                    {
                        "key": "repository",
                        "match": {"value": repository}
                    },
                    {
                        "key": "branch",
                        "match": {"value": branch}
                    }
                ]
            },
            "with_payload": True,
            "with_vector": False
        }
        response = self._request(
            "post",
            f"/collections/{self.collection}/points/search",
            json=payload
        )
        if response is None or response.status_code != 200:
            logger.error("Failed to execute search query on Qdrant")
            return []

        try:
            return response.json().get("result") or []
        except Exception as e:
            logger.error(f"Error parsing search response: {e}")
            return []

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response | None:
        """Helper method with retries and exponential backoff."""
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
                logger.warning(f"Qdrant returned status {response.status_code} for {path}")
            except requests.RequestException as exc:
                last_error = exc
                logger.warning(f"Qdrant request failed (attempt {attempt + 1}/{self.retries + 1}): {exc}")
            
            if attempt < self.retries:
                time.sleep(0.5 * (attempt + 1))
        
        if last_error:
            raise last_error
        return None
