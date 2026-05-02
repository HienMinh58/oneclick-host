import logging
import docker
from docker.errors import NotFound, BuildError, APIError

from config import (
    TRAEFIK_DOMAIN,
    TRAEFIK_NETWORK,
    CONTAINER_MEMORY_LIMIT,
    CONTAINER_CPU_LIMIT,
)

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """Lazily initialize the Docker client."""
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def build_image(source_path: str, image_tag: str) -> tuple[bool, str]:
    """
    Build a Docker image from the source path.

    Returns:
        (success: bool, logs: str)
    """
    log_lines = []

    try:
        logger.info(f"Building Docker image: {image_tag} from {source_path}")

        # Build the image and stream logs
        image, build_logs = get_client().images.build(
            path=source_path,
            tag=image_tag,
            rm=True,
            forcerm=True,
        )

        for chunk in build_logs:
            if "stream" in chunk:
                line = chunk["stream"].strip()
                if line:
                    log_lines.append(line)
                    logger.debug(line)
            elif "error" in chunk:
                log_lines.append(f"ERROR: {chunk['error']}")

        logs_text = "\n".join(log_lines)
        logger.info(f"Successfully built image: {image_tag}")
        return True, logs_text

    except BuildError as e:
        for chunk in e.build_log:
            if "stream" in chunk:
                log_lines.append(chunk["stream"].strip())
            elif "error" in chunk:
                log_lines.append(f"ERROR: {chunk['error']}")

        logs_text = "\n".join(log_lines)
        logger.error(f"Build failed for {image_tag}: {e}")
        return False, logs_text

    except APIError as e:
        logger.error(f"Docker API error: {e}")
        return False, f"Docker API error: {str(e)}"


def stop_previous_container(container_name: str):
    """Stop and remove a previously running container if it exists."""
    try:
        container = get_client().containers.get(container_name)
        logger.info(f"Stopping previous container: {container_name}")
        container.stop(timeout=10)
        container.remove(force=True)
    except NotFound:
        pass  # No previous container
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
    Run a new container with Traefik labels for automatic routing.

    Returns:
        (container_id, live_url)
    """
    # Stop any existing container with the same name
    stop_previous_container(container_name)

    # Build the subdomain: {service}-{project}.{domain}
    subdomain = f"{service_name}-{project_name}".lower().replace(" ", "-")
    live_url = f"http://{subdomain}.{TRAEFIK_DOMAIN}"
    router_name = container_name.replace("-", "")

    labels = {
        "traefik.enable": "true",
        f"traefik.http.routers.{router_name}.rule": f"Host(`{subdomain}.{TRAEFIK_DOMAIN}`)",
        f"traefik.http.routers.{router_name}.entrypoints": "web",
    }

    environment = env_vars or {}

    logger.info(f"Running container: {container_name} → {live_url}")

    container = get_client().containers.run(
        image=image_tag,
        name=container_name,
        detach=True,
        labels=labels,
        environment=environment,
        mem_limit=CONTAINER_MEMORY_LIMIT,
        nano_cpus=int(CONTAINER_CPU_LIMIT * 1e9),
        restart_policy={"Name": "unless-stopped"},
        network=TRAEFIK_NETWORK,
    )

    logger.info(f"Container started: {container.short_id}")

    # Reload container attrs to get assigned ports
    container.reload()
    
    # Try to find the exposed port
    port = 80
    exposed_ports = container.attrs.get("Config", {}).get("ExposedPorts", {})
    if exposed_ports:
        port_str = list(exposed_ports.keys())[0]
        port = int(port_str.split("/")[0])

    # Generate Traefik File Provider config
    # This bypasses the Docker Socket provider which fails on Docker Desktop Windows
    try:
        import os
        import yaml
        
        dynamic_dir = "/etc/traefik/dynamic"
        if os.path.exists(dynamic_dir):
            config = {
                "http": {
                    "routers": {
                        router_name: {
                            "rule": f"Host(`{subdomain}.{TRAEFIK_DOMAIN}`)",
                            "service": router_name,
                            "entryPoints": ["web"]
                        }
                    },
                    "services": {
                        router_name: {
                            "loadBalancer": {
                                "servers": [
                                    {"url": f"http://{container_name}:{port}"}
                                ]
                            }
                        }
                    }
                }
            }
            config_path = os.path.join(dynamic_dir, f"{router_name}.yml")
            with open(config_path, "w") as f:
                yaml.dump(config, f)
            logger.info(f"Wrote Traefik routing config to {config_path} for port {port}")
    except Exception as e:
        logger.error(f"Failed to generate Traefik config: {e}")

    return container.short_id, live_url
