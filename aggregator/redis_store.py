import json
import redis
from typing import Any, Dict, List, Optional
from config import Settings
from logger import logger

class RedisStore:
    def __init__(self, settings: Settings):
        self.client = redis.Redis.from_url(settings.redis_url)
        self.timeout_seconds = settings.timeout_seconds

    def save_agent_result(self, correlation_id: str, agent_name: str, result: Dict[str, Any]) -> None:
        key = f"deployment:{correlation_id}"
        self.client.hset(key, agent_name, json.dumps(result))
        # Keep keys alive slightly longer than the aggregation timeout itself
        self.client.expire(key, self.timeout_seconds * 3)
        logger.info(f"Saved result for agent {agent_name} and correlation_id {correlation_id} to Redis")

    def get_agent_results(self, correlation_id: str) -> Dict[str, Dict[str, Any]]:
        key = f"deployment:{correlation_id}"
        raw_results = self.client.hgetall(key)
        results = {}
        for k, v in raw_results.items():
            results[k.decode("utf-8")] = json.loads(v.decode("utf-8"))
        return results

    def set_timeout_marker(self, correlation_id: str, start_time: float) -> bool:
        """Sets the timeout timestamp marker. Returns True if this was the first set (key did not exist)."""
        key = f"timeout:{correlation_id}"
        # setnx to ensure we only set it on the first agent message arrival
        is_new = self.client.set(key, str(start_time), nx=True, ex=self.timeout_seconds * 3)
        if is_new:
            logger.info(f"Created timeout marker for correlation_id {correlation_id}")
            return True
        return False

    def delete_timeout_marker(self, correlation_id: str) -> bool:
        """Atomically delete the timeout marker. Returns True if it was deleted, acting as a lock."""
        key = f"timeout:{correlation_id}"
        deleted_count = self.client.delete(key)
        return deleted_count > 0

    def save_final_decision(self, correlation_id: str, decision: Dict[str, Any]) -> None:
        key = f"decision:{correlation_id}"
        # Store final decision with 1-hour expiration so the API can query it
        self.client.set(key, json.dumps(decision), ex=3600)
        logger.info(f"Saved final decision for correlation_id {correlation_id} to Redis")

    def get_final_decision(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        key = f"decision:{correlation_id}"
        raw = self.client.get(key)
        if raw:
            return json.loads(raw.decode("utf-8"))
        return None

    def delete_deployment_data(self, correlation_id: str) -> None:
        self.client.delete(f"deployment:{correlation_id}")
        self.client.delete(f"timeout:{correlation_id}")
        logger.info(f"Cleared deployment temp data for correlation_id {correlation_id}")

    def list_final_decisions(self) -> List[Dict[str, Any]]:
        """Scan Redis for all stored final decisions, sorted newest first."""
        decisions = []
        for key in self.client.scan_iter("decision:*"):
            raw = self.client.get(key)
            if raw:
                try:
                    decisions.append(json.loads(raw))
                except Exception:
                    pass
        decisions.sort(
            key=lambda d: d.get("generated_at", ""),
            reverse=True
        )
        return decisions

    # --- Webhook metadata helpers ---

    def save_deployment_meta(self, correlation_id: str, meta: Dict[str, Any]) -> None:
        """Store webhook-originated metadata (repo, author, PR title, etc.) alongside a correlation_id.
        TTL is set to 7200s (2 hours) — longer than the decision TTL of 3600s.
        """
        key = f"meta:{correlation_id}"
        self.client.set(key, json.dumps(meta), ex=7200)
        logger.info(f"Saved deployment meta for correlation_id {correlation_id}")

    def get_deployment_meta(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve webhook metadata for a correlation_id. Returns None if not found."""
        key = f"meta:{correlation_id}"
        raw = self.client.get(key)
        if raw:
            return json.loads(raw.decode("utf-8"))
        return None
