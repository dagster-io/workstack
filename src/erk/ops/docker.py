"""Docker operations interface for container-based plan execution.

This module defines the abstract interface for Docker operations, following
erk's ops pattern with ABC-based dependency injection for testability.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class Docker(ABC):
    """Abstract interface for Docker operations.

    This interface enables dependency injection for testing. Real implementations
    use subprocess to call Docker CLI. Fake implementations are pure in-memory
    for unit tests without requiring Docker daemon.

    Pattern follows erk's integration architecture (Git, GitHub, Graphite, Shell).
    """

    @abstractmethod
    def build_image(self, dockerfile_path: Path, tag: str, build_context: Path) -> None:
        """Build Docker image from Dockerfile.

        Args:
            dockerfile_path: Path to Dockerfile (must exist)
            tag: Image tag to use (e.g., "erk-implement:abc123")
            build_context: Directory to use as build context (must exist)

        Raises:
            FileNotFoundError: If dockerfile_path or build_context don't exist
            RuntimeError: If Docker build fails
            OSError: If Docker daemon not running
        """
        ...

    @abstractmethod
    def run_container(
        self,
        image_tag: str,
        volumes: dict[str, str],
        env_vars: dict[str, str],
        command: list[str],
        interactive: bool = True,
    ) -> int:
        """Run Docker container with specified configuration.

        Args:
            image_tag: Docker image tag to run
            volumes: Volume mounts (host_path:container_path format)
            env_vars: Environment variables to set in container
            command: Command and arguments to execute in container
            interactive: Whether to attach TTY for interactive sessions

        Returns:
            Exit code from container process

        Raises:
            RuntimeError: If container execution fails
            OSError: If Docker daemon not running
        """
        ...

    @abstractmethod
    def cleanup_container(self, container_id: str) -> None:
        """Remove Docker container.

        Args:
            container_id: Container ID to remove

        Raises:
            RuntimeError: If container removal fails
        """
        ...

    @abstractmethod
    def is_daemon_running(self) -> bool:
        """Check if Docker daemon is running and accessible.

        Returns:
            True if Docker daemon is running, False otherwise

        Note:
            This is a LBYL check - call before other operations to provide
            helpful error messages if Docker isn't available.
        """
        ...
