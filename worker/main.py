"""
OneClick-Host worker entry point.

Polls queued deployments and runs the pipeline:
clone -> detect stack -> generate Dockerfile -> build -> deploy.
"""
import logging
import time
import traceback
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from config import MAX_CONCURRENT_BUILDS, POLL_INTERVAL
from db import (
    fetch_queued_deployment,
    get_connection,
    get_env_vars,
    update_deployment_status,
    update_service_status,
)
from modules.build_runner import build_image, run_container, slugify
from modules.dockerfile_generator import generate_dockerfile
from modules.repo_cloner import cleanup_workspace, clone_repo
from modules.stack_detector import detect_stack

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker")


def process_deployment(conn, deployment: dict):
    """Run the full deployment pipeline for one queued deployment."""
    deployment_id = str(deployment["Id"])
    service_id = str(deployment["ServiceId"])
    repo_url = deployment["RepoUrl"]
    branch = deployment["Branch"]
    subfolder = deployment["Subfolder"]
    service_name = deployment["ServiceName"]
    project_name = deployment["ProjectName"]
    version = deployment["Version"]

    image_tag = f"oneclick-{slugify(project_name)}-{slugify(service_name)}:v{version}"
    container_name = f"oc-{slugify(project_name)}-{slugify(service_name)}"
    all_logs = []

    try:
        all_logs.append(f"=== Cloning {repo_url} (branch: {branch}) ===")
        source_path = clone_repo(repo_url, branch, subfolder, deployment_id)
        all_logs.append("Repository cloned successfully")

        update_deployment_status(conn, deployment_id, "building", build_logs="\n".join(all_logs))

        all_logs.append("\n=== Detecting technology stack ===")
        stack = detect_stack(source_path)
        all_logs.append(f"Detected stack: {stack}")
        update_service_status(conn, service_id, "deploying", detected_stack=stack)

        all_logs.append("\n=== Generating Dockerfile ===")
        dockerfile_path = generate_dockerfile(source_path, stack)
        all_logs.append(f"Dockerfile ready at {dockerfile_path}")

        all_logs.append(f"\n=== Building Docker image: {image_tag} ===")
        update_deployment_status(conn, deployment_id, "building", build_logs="\n".join(all_logs))

        success, build_logs = build_image(source_path, image_tag)
        all_logs.append(build_logs)
        if not success:
            raise RuntimeError("Docker build failed. See logs above.")

        all_logs.append(f"\nImage built: {image_tag}")

        all_logs.append(f"\n=== Deploying container: {container_name} ===")
        update_deployment_status(
            conn,
            deployment_id,
            "deploying",
            image_tag=image_tag,
            build_logs="\n".join(all_logs),
        )

        env_vars = get_env_vars(conn, service_id)
        container_id, live_url = run_container(
            image_tag,
            container_name,
            project_name,
            service_name,
            env_vars=env_vars,
        )

        all_logs.append(f"Container running: {container_id}")
        all_logs.append(f"Live URL: {live_url}")

        update_deployment_status(
            conn,
            deployment_id,
            "live",
            image_tag=image_tag,
            build_logs="\n".join(all_logs),
        )
        update_service_status(conn, service_id, "live", live_url=live_url, container_id=container_id)

        logger.info(f"Deployment {deployment_id} succeeded -> {live_url}")

    except Exception as e:
        error_msg = str(e)
        all_logs.append(f"\nERROR: {error_msg}")
        all_logs.append(traceback.format_exc())

        update_deployment_status(
            conn,
            deployment_id,
            "failed",
            error_message=error_msg,
            build_logs="\n".join(all_logs),
        )
        update_service_status(conn, service_id, "failed")

        logger.error(f"Deployment {deployment_id} failed: {error_msg}")

    finally:
        cleanup_workspace(deployment_id)


def main():
    """Poll the queue and process up to MAX_CONCURRENT_BUILDS at a time."""
    logger.info("OneClick-Host worker started")
    logger.info(f"Poll interval: {POLL_INTERVAL}s")
    logger.info(f"Max concurrent builds: {MAX_CONCURRENT_BUILDS}")

    def process_with_connection(deployment: dict):
        conn = get_connection()
        try:
            process_deployment(conn, deployment)
        finally:
            conn.close()

    active = set()
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BUILDS) as executor:
        while True:
            try:
                done = {future for future in active if future.done()}
                for future in done:
                    active.remove(future)
                    future.result()

                while len(active) < MAX_CONCURRENT_BUILDS:
                    conn = get_connection()
                    try:
                        deployment = fetch_queued_deployment(conn)
                    finally:
                        conn.close()

                    if not deployment:
                        logger.debug("No queued deployments. Sleeping...")
                        break

                    logger.info(
                        f"Processing deployment {deployment['Id']} "
                        f"for {deployment['ProjectName']}/{deployment['ServiceName']}"
                    )
                    active.add(executor.submit(process_with_connection, deployment))

                if active:
                    wait(active, timeout=POLL_INTERVAL, return_when=FIRST_COMPLETED)
                else:
                    time.sleep(POLL_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Worker shutting down...")
                break
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
                logger.debug(traceback.format_exc())
                time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
