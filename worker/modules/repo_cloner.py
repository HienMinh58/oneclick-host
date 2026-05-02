import os
import shutil
import logging
from git import Repo

from config import WORKSPACE_DIR

logger = logging.getLogger(__name__)


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
        source_path = os.path.join(clone_path, subfolder)
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
