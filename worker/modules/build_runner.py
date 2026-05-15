import logging
import os
import re
import subprocess

import docker
import yaml
from docker.errors import APIError, NotFound

from config import (
    BUILD_TIMEOUT,
    TRAEFIK_DOMAIN,
    TRAEFIK_NETWORK,
    CONTAINER_MEMORY_LIMIT,
    CONTAINER_CPU_LIMIT,
    CONTAINER_PIDS_LIMIT,
)

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """Lazily initialize the Docker client."""
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def slugify(value: str, max_length: int = 63) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return (slug or "app")[:max_length].strip("-") or "app"


def build_image(source_path: str, image_tag: str) -> tuple[bool, str]:
    """
    Build a Docker image from the source path with a hard timeout.

    Returns:
        (success: bool, logs: str)
    """
    log_lines = []

    try:
        logger.info(
            f"Building Docker image: {image_tag} from {source_path} "
            f"(timeout: {BUILD_TIMEOUT}s)"
        )

        result = subprocess.run(
            ["docker", "build", "--rm", "--force-rm", "-t", image_tag, source_path],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=BUILD_TIMEOUT,
            check=False,
        )

        if result.stdout:
            log_lines.extend(line for line in result.stdout.splitlines() if line)

        if result.returncode != 0:
            logs_text = "\n".join(log_lines)
            logger.error(f"Build failed for {image_tag} with exit code {result.returncode}")
            return False, logs_text

        logs_text = "\n".join(log_lines)
        logger.info(f"Successfully built image: {image_tag}")
        return True, logs_text

    except subprocess.TimeoutExpired as e:
        if e.stdout:
            stdout = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else e.stdout
            log_lines.extend(line for line in stdout.splitlines() if line)
        message = f"Docker build timed out after {BUILD_TIMEOUT} seconds"
        log_lines.append(f"ERROR: {message}")
        logger.error(f"{message}: {image_tag}")
        return False, "\n".join(log_lines)

    except OSError as e:
        logger.error(f"Docker build command failed: {e}")
        return False, f"Docker build command failed: {str(e)}"


def stop_previous_container(container_name: str):
    """Stop and remove a previously running container if it exists."""
    try:
        container = get_client().containers.get(container_name)
        logger.info(f"Stopping previous container: {container_name}")
        container.stop(timeout=10)
        container.remove(force=True)
    except NotFound:
        pass
    except APIError as e:
        logger.warning(f"Error stopping container {container_name}: {e}")


def run_container(
    image_tag: str,
    container_name: str,
    project_name: str,
    service_name: str,
    env_vars: dict[str, str] | None = None,
) -> tuple[str, str]:
    """
    Run a new user workload on apps-net and create Traefik file-provider routing.

    User workloads receive no Docker socket, no host mounts, no privileged mode,
    and no host-published ports. This reduces blast radius, but shared Docker
    is not strong sandboxing.

    Returns:
        (container_id, live_url)
    """
    safe_container_name = slugify(container_name)
    stop_previous_container(safe_container_name)

    subdomain = slugify(f"{service_name}-{project_name}")
    live_url = f"http://{subdomain}.{TRAEFIK_DOMAIN}"
    router_name = safe_container_name.replace("-", "")

    labels = {
        "traefik.enable": "true",
        f"traefik.http.routers.{router_name}.rule": f"Host(`{subdomain}.{TRAEFIK_DOMAIN}`)",
        f"traefik.http.routers.{router_name}.entrypoints": "web",
    }

    logger.info(f"Running container: {safe_container_name} -> {live_url}")

    container = get_client().containers.run(
        image=image_tag,
        name=safe_container_name,
        detach=True,
        labels=labels,
        environment=dict(env_vars or {}),
        mem_limit=CONTAINER_MEMORY_LIMIT,
        nano_cpus=int(CONTAINER_CPU_LIMIT * 1e9),
        pids_limit=CONTAINER_PIDS_LIMIT,
        privileged=False,
        security_opt=["no-new-privileges:true"],
        restart_policy={"Name": "unless-stopped"},
        network=TRAEFIK_NETWORK,
        ports={},
        volumes={},
    )

    logger.info(f"Container started: {container.short_id}")
    container.reload()

    port = 80
    exposed_ports = container.attrs.get("Config", {}).get("ExposedPorts", {})
    if exposed_ports:
        port_str = list(exposed_ports.keys())[0]
        port = int(port_str.split("/")[0])

    dynamic_dir = "/etc/traefik/dynamic"
    if os.path.exists(dynamic_dir):
        config = {
            "http": {
                "routers": {
                    router_name: {
                        "rule": f"Host(`{subdomain}.{TRAEFIK_DOMAIN}`)",
                        "service": router_name,
                        "entryPoints": ["web"],
                    }
                },
                "services": {
                    router_name: {
                        "loadBalancer": {
                            "servers": [
                                {"url": f"http://{safe_container_name}:{port}"}
                            ]
                        }
                    }
                },
            }
        }
        config_path = os.path.join(dynamic_dir, f"{router_name}.yml")
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f)
        logger.info(f"Wrote Traefik routing config to {config_path} for port {port}")

    return container.short_id, live_url
