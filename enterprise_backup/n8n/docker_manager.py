"""Docker operations wrapper for N8N container management."""

import time
from typing import Any, Dict, List, Optional, Tuple

import docker
import requests
from docker.models.containers import Container
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import DockerError, HealthcheckError, N8NError


class DockerManager:
    """Manages Docker operations for N8N container.

    Provides high-level interface for container management, command execution,
    and healthchecks with automatic retry logic.
    """

    def __init__(
        self,
        container_name: str = "n8n",
        docker_host: Optional[str] = None,
        api_url: str = "http://localhost:5678",
    ) -> None:
        """Initialize Docker manager.

        Args:
            container_name: Name of N8N Docker container
            docker_host: Docker host URL (None = Unix socket)
            api_url: N8N API URL for healthchecks

        Raises:
            DockerError: If Docker daemon is not accessible
        """
        self.container_name = container_name
        self.api_url = api_url

        try:
            if docker_host:
                self.client = docker.DockerClient(base_url=docker_host)
            else:
                self.client = docker.from_env()

            # Test connection
            self.client.ping()
        except docker.errors.DockerException as e:
            raise DockerError(
                "Failed to connect to Docker daemon",
                details={
                    "docker_host": docker_host or "/var/run/docker.sock",
                    "error": str(e),
                    "suggestion": "Ensure Docker is running and user has permissions",
                },
            )

    def find_n8n_container(self) -> Container:
        """Find N8N container by name.

        Returns:
            Docker Container object

        Raises:
            DockerError: If container not found or multiple containers match
        """
        try:
            containers = self.client.containers.list(
                all=True, filters={"name": self.container_name}
            )

            if not containers:
                # Try to find by image name as fallback
                containers = self.client.containers.list(
                    all=True, filters={"ancestor": "n8nio/n8n"}
                )

                if not containers:
                    raise DockerError(
                        f"N8N container not found: {self.container_name}",
                        details={
                            "container_name": self.container_name,
                            "available_containers": [
                                c.name for c in self.client.containers.list(all=True)
                            ],
                            "suggestion": "Check N8N_CONTAINER_NAME in configuration",
                        },
                    )

                if len(containers) > 1:
                    raise DockerError(
                        f"Multiple N8N containers found, specify exact name",
                        details={
                            "found_containers": [c.name for c in containers],
                            "suggestion": "Set N8N_CONTAINER_NAME to specific container name",
                        },
                    )

            container = containers[0]

            # Verify it's actually an N8N container
            if "n8n" not in container.image.tags[0].lower():
                raise DockerError(
                    f"Container {container.name} doesn't appear to be N8N",
                    details={
                        "container_name": container.name,
                        "image": container.image.tags[0] if container.image.tags else "unknown",
                        "suggestion": "Verify container is running n8nio/n8n image",
                    },
                )

            return container

        except docker.errors.DockerException as e:
            raise DockerError(
                f"Docker API error while finding container",
                details={"error": str(e), "container_name": self.container_name},
            )

    def exec_command(
        self, command: List[str], workdir: Optional[str] = None
    ) -> Tuple[int, str, str]:
        """Execute command inside N8N container.

        Args:
            command: Command as list of strings (e.g., ['n8n', 'export:credentials'])
            workdir: Working directory inside container

        Returns:
            Tuple of (exit_code, stdout, stderr)

        Raises:
            DockerError: If container not running
            N8NError: If command execution fails
        """
        container = self.find_n8n_container()

        if container.status != "running":
            raise DockerError(
                f"Container {container.name} is not running",
                details={
                    "container_name": container.name,
                    "status": container.status,
                    "suggestion": "Start the container before backup/restore operations",
                },
            )

        try:
            exec_result = container.exec_run(
                cmd=command,
                workdir=workdir,
                demux=True,  # Separate stdout and stderr
            )

            exit_code = exec_result.exit_code
            stdout_bytes, stderr_bytes = exec_result.output

            stdout = stdout_bytes.decode("utf-8") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8") if stderr_bytes else ""

            if exit_code != 0:
                raise N8NError(
                    f"N8N CLI command failed: {' '.join(command)}",
                    details={
                        "command": command,
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                    },
                )

            return exit_code, stdout, stderr

        except docker.errors.APIError as e:
            raise DockerError(
                f"Docker API error during command execution",
                details={"command": command, "error": str(e)},
            )

    def stop_container(self, timeout: int = 30) -> None:
        """Stop N8N container gracefully.

        Args:
            timeout: Seconds to wait before SIGKILL

        Raises:
            DockerError: If stop operation fails
        """
        container = self.find_n8n_container()

        if container.status != "running":
            return  # Already stopped

        try:
            # SIGTERM first, then SIGKILL after timeout
            container.stop(timeout=timeout)
        except docker.errors.APIError as e:
            raise DockerError(
                f"Failed to stop container {container.name}",
                details={"error": str(e), "timeout": timeout},
            )

    def start_container(self) -> None:
        """Start N8N container.

        Raises:
            DockerError: If start operation fails
        """
        container = self.find_n8n_container()

        if container.status == "running":
            return  # Already running

        try:
            container.start()
        except docker.errors.APIError as e:
            raise DockerError(
                f"Failed to start container {container.name}",
                details={"error": str(e)},
            )

    def get_container_env(self, var_name: str) -> Optional[str]:
        """Get environment variable from container.

        Args:
            var_name: Environment variable name

        Returns:
            Variable value or None if not found

        Example:
            >>> manager = DockerManager()
            >>> key = manager.get_container_env('N8N_ENCRYPTION_KEY')
        """
        container = self.find_n8n_container()

        try:
            env_list = container.attrs.get("Config", {}).get("Env", [])

            for env_var in env_list:
                if env_var.startswith(f"{var_name}="):
                    return env_var.split("=", 1)[1]

            return None

        except Exception as e:
            raise DockerError(
                f"Failed to read environment variable {var_name}",
                details={"error": str(e)},
            )

    @retry(
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        reraise=True,
    )
    def healthcheck(self, endpoint: str = "/healthz", timeout: int = 5) -> bool:
        """Check if N8N is healthy via HTTP endpoint.

        Uses exponential backoff retry: 1s, 2s, 4s, 8s, 16s (max 31s total).

        Args:
            endpoint: Health check endpoint (default: /healthz)
            timeout: HTTP request timeout in seconds

        Returns:
            True if healthy (HTTP 200)

        Raises:
            HealthcheckError: If N8N doesn't respond after retries
        """
        url = f"{self.api_url}{endpoint}"

        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code == 200
        except requests.RequestException as e:
            # Let tenacity retry, this will be caught
            raise

    def wait_for_healthy(
        self, max_wait: int = 60, check_interval: int = 2
    ) -> None:
        """Wait for N8N to become healthy after restart.

        Args:
            max_wait: Maximum seconds to wait
            check_interval: Seconds between checks

        Raises:
            HealthcheckError: If N8N doesn't become healthy in time
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                if self.healthcheck():
                    return
            except requests.RequestException:
                pass  # Not healthy yet, continue waiting

            time.sleep(check_interval)

        # Timeout reached
        raise HealthcheckError(
            f"N8N did not become healthy within {max_wait}s",
            details={
                "api_url": self.api_url,
                "max_wait": max_wait,
                "suggestion": "Check N8N logs: docker logs " + self.container_name,
            },
        )

    def get_container_info(self) -> Dict[str, Any]:
        """Get container information for logging/debugging.

        Returns:
            Dictionary with container details
        """
        container = self.find_n8n_container()

        return {
            "id": container.id[:12],
            "name": container.name,
            "status": container.status,
            "image": container.image.tags[0] if container.image.tags else "unknown",
            "created": container.attrs.get("Created", "unknown"),
        }
