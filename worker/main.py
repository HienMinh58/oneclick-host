"""
OneClick-Host Worker — Main Entry Point

Polls the database for queued deployments and processes them sequentially.
Pipeline: Clone → Detect Stack → Generate Dockerfile → Build → Deploy
"""
import time
import logging
import traceback

from config import POLL_INTERVAL
from db import (
    get_connection,
    fetch_queued_deployment,
    update_deployment_status,
    update_service_status,
    get_env_vars,
)
from modules.repo_cloner import clone_repo, cleanup_workspace
from modules.stack_detector import detect_stack
from modules.dockerfile_generator import generate_dockerfile
from modules.build_runner import build_image, run_container

# ── Logging Setup ─────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker")


def process_deployment(conn, deployment: dict):
    """
    Full deployment pipeline for a single queued deployment.
    """
    deployment_id = str(deployment["Id"])
    service_id = str(deployment["ServiceId"])
    repo_url = deployment["RepoUrl"]
    branch = deployment["Branch"]
    subfolder = deployment["Subfolder"]
    service_name = deployment["ServiceName"]
    project_name = deployment["ProjectName"]
    version = deployment["Version"]

    image_tag = f"oneclick-{project_name}-{service_name}:v{version}".lower().replace(" ", "-")
    container_name = f"oc-{project_name}-{service_name}".lower().replace(" ", "-")

    all_logs = []

    try:
        # ── Step 1: Clone ─────────────────────────
        all_logs.append(f"=== Cloning {repo_url} (branch: {branch}) ===")
        source_path = clone_repo(repo_url, branch, subfolder, deployment_id)
        all_logs.append("✓ Repository cloned successfully")

        # ── Step 2: Detect Stack ──────────────────
        update_deployment_status(conn, deployment_id, "building",
                                 build_logs="\n".join(all_logs))

        all_logs.append("\n=== Detecting technology stack ===")
        stack = detect_stack(source_path)
        all_logs.append(f"✓ Detected stack: {stack}")

        # Update service with detected stack
        update_service_status(conn, service_id, "deploying", detected_stack=stack)

        # ── Step 3: Generate Dockerfile ───────────
        all_logs.append("\n=== Generating Dockerfile ===")
        dockerfile_path = generate_dockerfile(source_path, stack)
        all_logs.append(f"✓ Dockerfile ready at {dockerfile_path}")

        # ── Step 4: Build Image ───────────────────
        all_logs.append(f"\n=== Building Docker image: {image_tag} ===")
        update_deployment_status(conn, deployment_id, "building",
                                 build_logs="\n".join(all_logs))

        success, build_logs = build_image(source_path, image_tag)
        all_logs.append(build_logs)

        if not success:
            raise RuntimeError(f"Docker build failed. See logs above.")

        all_logs.append(f"\n✓ Image built: {image_tag}")

        # ── Step 5: Deploy Container ──────────────
        all_logs.append(f"\n=== Deploying container: {container_name} ===")
        update_deployment_status(conn, deployment_id, "deploying",
                                 image_tag=image_tag,
                                 build_logs="\n".join(all_logs))

        env_vars = get_env_vars(conn, service_id)
        container_id, live_url = run_container(
            image_tag, container_name,
            project_name, service_name,
            env_vars=env_vars,
        )

        all_logs.append(f"✓ Container running: {container_id}")
        all_logs.append(f"✓ Live URL: {live_url}")

        # ── Success ───────────────────────────────
        update_deployment_status(conn, deployment_id, "live",
                                 image_tag=image_tag,
                                 build_logs="\n".join(all_logs))
        update_service_status(conn, service_id, "live",
                              live_url=live_url,
                              container_id=container_id)

        logger.info(f"✅ Deployment {deployment_id} succeeded → {live_url}")

    except Exception as e:
        error_msg = str(e)
        all_logs.append(f"\n❌ ERROR: {error_msg}")
        all_logs.append(traceback.format_exc())

        update_deployment_status(conn, deployment_id, "failed",
                                 error_message=error_msg,
                                 build_logs="\n".join(all_logs))
        update_service_status(conn, service_id, "failed")

        logger.error(f"❌ Deployment {deployment_id} failed: {error_msg}")

    finally:
        # Clean up workspace
        cleanup_workspace(deployment_id)


def main():
    """Main polling loop."""
    logger.info("🚀 OneClick-Host Worker started")
    logger.info(f"   Poll interval: {POLL_INTERVAL}s")

    while True:
        try:
            conn = get_connection()
            deployment = fetch_queued_deployment(conn)

            if deployment:
                logger.info(
                    f"📦 Processing deployment {deployment['Id']} "
                    f"for {deployment['ProjectName']}/{deployment['ServiceName']}"
                )
                process_deployment(conn, deployment)
            else:
                logger.debug("No queued deployments. Sleeping...")

            conn.close()

        except KeyboardInterrupt:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            logger.debug(traceback.format_exc())

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
