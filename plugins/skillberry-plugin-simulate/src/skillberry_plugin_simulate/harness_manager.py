"""Manage the lifecycle of a simulation-harness Docker container."""
import logging
import socket
from typing import Any, Dict, Optional, Set, Tuple

from skillberry_plugin_simulate.config import SimulateConfig

logger = logging.getLogger(__name__)

HARNESS_REST_CONTAINER_PORT = 8086  # fixed inside the harness image


def find_free_port(port_range: Tuple[int, int], exclude: Set[int]) -> int:
    """Return the first bindable TCP port in [lo, hi] not in `exclude`."""
    lo, hi = port_range
    for port in range(lo, hi + 1):
        if port in exclude:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port in range {port_range}")


class HarnessManager:
    """Start/stop one harness container; allocate its REST + MCP host ports."""

    def __init__(self, config: SimulateConfig, docker_client: Optional[Any] = None):
        self._config = config
        if docker_client is None:
            import docker
            docker_client = docker.from_env()
        self._docker = docker_client

    def allocate_ports(self) -> Tuple[int, int]:
        rest_port = find_free_port(self._config.rest_port_range, exclude=set())
        mcp_port = find_free_port(self._config.mcp_port_range, exclude={rest_port})
        return rest_port, mcp_port

    def start(self, rest_port: int, mcp_port: int) -> Dict[str, Any]:
        environment = {"LLM_API_KEY": self._config.llm_api_key}
        if self._config.llm_api_base:
            environment["LLM_API_BASE"] = self._config.llm_api_base

        volumes: Dict[str, Dict[str, str]] = {}
        if self._config.skills_store_path:
            volumes[self._config.skills_store_path] = {"bind": "/skills-store", "mode": "ro"}
        if self._config.logs_path:
            volumes[self._config.logs_path] = {"bind": "/logs", "mode": "rw"}

        container = self._docker.containers.run(
            self._config.harness_image,
            detach=True,
            environment=environment,
            ports={
                f"{HARNESS_REST_CONTAINER_PORT}/tcp": rest_port,
                f"{mcp_port}/tcp": mcp_port,
            },
            volumes=volumes,
            remove=False,
        )
        logger.info("Started harness container %s (rest=%s mcp=%s)", container.id, rest_port, mcp_port)
        return {
            "container_id": container.id,
            "rest_port": rest_port,
            "mcp_port": mcp_port,
            "rest_url": f"http://127.0.0.1:{rest_port}",
        }

    def stop(self, container_id: str) -> None:
        try:
            container = self._docker.containers.get(container_id)
            container.stop()
            container.remove()
            logger.info("Stopped and removed harness container %s", container_id)
        except Exception as e:
            logger.warning("Could not stop harness container %s: %s", container_id, e)
