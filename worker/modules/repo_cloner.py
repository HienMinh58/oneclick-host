import os
import shutil
import logging
from urllib.parse import urlparse
from git import Repo

from config import WORKSPACE_DIR

logger = logging.getLogger(__name__)

ALLOWED_REPO_HOSTS = {"github.com"}


def validate_repo_url(repo_url: str) -> str:
    """Allow public GitHub HTTPS clone URLs without embedded credentials."""
    parsed = urlparse(repo_url)
    if parsed.scheme != "https":
        raise ValueError("Repository URL must use https://")
    if parsed.hostname not in ALLOWED_REPO_HOSTS:
        raise ValueError("Only github.com repositories are supported")
    if parsed.username or parsed.password:
        raise ValueError("Repository URL must not include credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("Repository URL must not include query strings or fragments")
    path = parsed.path.removesuffix(".git").strip("/")
    parts = path.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("Repository URL must be in the form https://github.com/owner/repo")
    if ".." in parts or any(part.startswith(".") for part in parts):
        raise ValueError("Repository owner and name must be explicit")
    return repo_url


def validate_relative_subfolder(subfolder: str | None) -> str | None:
    """Keep requested source paths inside the cloned repository."""
    if not subfolder:
        return None
    normalized = os.path.normpath(subfolder).replace("\\", "/")
    if normalized.startswith("../") or normalized == ".." or os.path.isabs(normalized):
        raise ValueError("Subfolder must be a relative path inside the repository")
    return normalized


def clone_repo(repo_url: str, branch: str, subfolder: str | None, deployment_id: str) -> str:
    """
    Clone a Git repository and return the path to the source code.

    Args:
        repo_url: GitHub repository URL
        branch: Branch to clone
        subfolder: Optional subfolder within the repo
        deployment_id: Used to create a unique workspace directory

    Returns:
        Path to the cloned source code (respecting subfolder if specified)
    """
    repo_url = validate_repo_url(repo_url)
    subfolder = validate_relative_subfolder(subfolder)
    workspace = os.path.join(WORKSPACE_DIR, str(deployment_id))

    # Clean up any previous workspace
    if os.path.exists(workspace):
        shutil.rmtree(workspace)

    os.makedirs(workspace, exist_ok=True)

    clone_path = os.path.join(workspace, "repo")

    logger.info(f"Cloning {repo_url} (branch: {branch}) into {clone_path}")

    Repo.clone_from(
        repo_url,
        clone_path,
        branch=branch,
        depth=1,  # Shallow clone for speed
    )

    # If subfolder is specified, return path to that subfolder
    if subfolder:
        source_path = os.path.abspath(os.path.join(clone_path, subfolder))
        clone_root = os.path.abspath(clone_path)
        if os.path.commonpath([clone_root, source_path]) != clone_root:
            raise ValueError("Subfolder must stay inside the repository")
        if not os.path.exists(source_path):
            raise FileNotFoundError(
                f"Subfolder '{subfolder}' not found in repository"
            )
        return source_path

    return clone_path


def cleanup_workspace(deployment_id: str):
    """Remove the workspace directory for a deployment."""
    workspace = os.path.join(WORKSPACE_DIR, str(deployment_id))
    if os.path.exists(workspace):
        shutil.rmtree(workspace, ignore_errors=True)
        logger.info(f"Cleaned up workspace for deployment {deployment_id}")
