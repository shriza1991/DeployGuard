import json
import logging
import redis
from typing import Optional, Dict, Any
from models import RepoStatus, RepoManifest

logger = logging.getLogger("repository-context-service")

class RedisService:
    def __init__(self, redis_url: str):
        self.client = redis.Redis.from_url(redis_url)
        logger.info(f"Initialized Redis connection to: {redis_url}")

    def save_status(self, repository: str, branch: str, status: RepoStatus) -> None:
        """Saves repository indexing status to Redis."""
        key = f"repo_status:{repository}:{branch}"
        try:
            self.client.set(key, status.model_dump_json())
            logger.info(f"Saved repository status in Redis under key: {key}")
        except Exception as e:
            logger.error(f"Failed to save status to Redis: {e}")

    def get_status(self, repository: str, branch: str) -> Optional[RepoStatus]:
        """Retrieves repository indexing status from Redis."""
        key = f"repo_status:{repository}:{branch}"
        try:
            data = self.client.get(key)
            if data:
                return RepoStatus.model_validate_json(data.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to read status from Redis: {e}")
        return None

    def save_manifest(self, repository: str, branch: str, manifest: RepoManifest) -> None:
        """Saves repository manifest metadata to Redis."""
        key = f"repo_manifest:{repository}:{branch}"
        try:
            self.client.set(key, manifest.model_dump_json())
            logger.info(f"Saved repository manifest in Redis under key: {key}")
        except Exception as e:
            logger.error(f"Failed to save manifest to Redis: {e}")

    def get_manifest(self, repository: str, branch: str) -> Optional[RepoManifest]:
        """Retrieves repository manifest metadata from Redis."""
        key = f"repo_manifest:{repository}:{branch}"
        try:
            data = self.client.get(key)
            if data:
                return RepoManifest.model_validate_json(data.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to read manifest from Redis: {e}")
        return None

    def delete_repository_data(self, repository: str, branch: str) -> None:
        """Deletes status and manifest keys for the given repository and branch."""
        status_key = f"repo_status:{repository}:{branch}"
        manifest_key = f"repo_manifest:{repository}:{branch}"
        try:
            deleted_count = self.client.delete(status_key, manifest_key)
            logger.info(f"Deleted {deleted_count} Redis keys for repo {repository} (branch: {branch})")
        except Exception as e:
            logger.error(f"Failed to delete repository data from Redis: {e}")
            raise e
