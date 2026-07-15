import os
import shutil
import stat
import logging
import uuid
import urllib.parse
import git

logger = logging.getLogger("repository-context-service")

def get_repo_name(url: str) -> str:
    """Extracts the repository name from a URL or path."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path if parsed.path else url
    base = os.path.basename(path.rstrip("/\\"))
    if base.endswith(".git"):
        base = base[:-4]
    return base or "unknown_repo"

def force_rmtree(path: str) -> None:
    """
    Robust directory removal. Clears read-only attributes on Windows files
    to prevent PermissionError when deleting Git directories.
    """
    def remove_readonly(func, file_path, excinfo):
        try:
            os.chmod(file_path, stat.S_IWRITE)
            func(file_path)
        except Exception as e:
            logger.warning(f"Failed to remove read-only file {file_path}: {e}")

    if os.path.exists(path):
        try:
            shutil.rmtree(path, onerror=remove_readonly)
            logger.info(f"Successfully cleaned up directory: {path}")
        except Exception as e:
            logger.error(f"Error executing force_rmtree on {path}: {e}")

class CloneService:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = os.path.abspath(data_dir)
        self.clones_dir = os.path.join(self.data_dir, "cloned_repos")
        os.makedirs(self.clones_dir, exist_ok=True)

    def clone_repository(self, repository_url: str, branch: str = "main") -> tuple[str, str]:
        """
        Clones a repository to a unique local path.
        Returns: (clone_path, head_commit_sha)
        """
        repo_name = get_repo_name(repository_url)
        unique_id = uuid.uuid4().hex[:8]
        clone_path = os.path.join(self.clones_dir, f"{repo_name}_{branch}_{unique_id}")
        
        logger.info(f"Cloning {repository_url} (branch: {branch}) into {clone_path}...")
        
        try:
            repo = git.Repo.clone_from(
                repository_url,
                clone_path,
                branch=branch,
                depth=1  # Shallow clone is faster and sufficient for context indexing
            )
            head_commit = repo.head.commit.hexsha
            logger.info(f"Cloned successfully. HEAD commit: {head_commit}")
            return clone_path, head_commit
        except Exception as e:
            logger.error(f"Failed to clone repository {repository_url}: {e}")
            # Try to clean up path if it was partially created
            force_rmtree(clone_path)
            raise e

    def cleanup(self, path: str) -> None:
        """Cleans up the cloned repository folder."""
        force_rmtree(path)
