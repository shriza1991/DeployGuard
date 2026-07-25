import os
import shutil
import stat
import logging
import uuid
import urllib.parse
import git

logger = logging.getLogger("repository-context-service")

def get_repo_name(url: str) -> str:
    """Extracts the short repository name from a URL or path (e.g. 'my-service')."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path if parsed.path else url
    base = os.path.basename(path.rstrip("/\\"))
    if base.endswith(".git"):
        base = base[:-4]
    return base or "unknown_repo"


def get_repo_full_name(url: str) -> str:
    """
    Extracts the owner/repo full name from a GitHub-style clone URL.

    Examples
    --------
    - https://github.com/acme/my-service.git  →  "acme/my-service"
    - git@github.com:acme/my-service.git      →  "acme/my-service"
    - /local/path/my-service                  →  "my-service"  (fallback)

    Falls back to the short repo name when the URL has no recognisable
    owner segment (e.g. bare file paths or single-component paths).
    """
    # Normalise SSH-style URLs (git@github.com:owner/repo.git) to a path
    url_clean = url.strip()
    if url_clean.startswith("git@"):
        # git@github.com:owner/repo.git  →  owner/repo.git
        url_clean = url_clean.split(":", 1)[-1]

    parsed = urllib.parse.urlparse(url_clean)
    path = parsed.path if parsed.path else url_clean
    # Strip leading slash and trailing .git
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]

    parts = path.split("/")
    # Need at least two non-empty parts to form owner/repo
    parts = [p for p in parts if p]
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"

    # Fallback: just the repository short name
    return parts[-1] if parts else "unknown_repo"

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
        Clones a repository to a cached path, or updates an existing clone.
        Returns: (clone_path, head_commit_sha)
        """
        repo_name = get_repo_name(repository_url)
        clone_path = os.path.join(self.clones_dir, f"{repo_name}_{branch}")
        
        if os.path.exists(clone_path) and os.path.isdir(os.path.join(clone_path, ".git")):
            logger.info(f"Reusing cached repository clone at {clone_path}...")
            try:
                repo = git.Repo(clone_path)
                repo.remotes.origin.fetch()
                repo.git.checkout(branch)
                repo.git.reset('--hard', f'origin/{branch}')
                head_commit = repo.head.commit.hexsha
                logger.info(f"Updated cached clone successfully. HEAD commit: {head_commit}")
                return clone_path, head_commit
            except Exception as e:
                logger.warning(f"Failed to update cached repository: {e}. Clearing and re-cloning...")
                force_rmtree(clone_path)

        # Clone from scratch
        logger.info(f"Cloning {repository_url} (branch: {branch}) into {clone_path}...")
        try:
            repo = git.Repo.clone_from(
                repository_url,
                clone_path,
                branch=branch
            )
            head_commit = repo.head.commit.hexsha
            logger.info(f"Cloned successfully. HEAD commit: {head_commit}")
            return clone_path, head_commit
        except Exception as e:
            logger.error(f"Failed to clone repository {repository_url}: {e}")
            force_rmtree(clone_path)
            raise e

    def cleanup(self, path: str) -> None:
        """Keeps the clone for cache reuse."""
        logger.info(f"Retaining cached repository at {path} for future increments.")
