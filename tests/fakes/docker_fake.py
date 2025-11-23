"""Fake Docker operations for testing without Docker daemon.

This module provides an in-memory fake implementation of Docker for unit
testing. No actual Docker operations are performed - all calls are recorded
for verification in tests.

Follows erk's testing pattern: fakes are pure in-memory, no I/O operations.
"""

from pathlib import Path

from erk.ops.docker import Docker


class FakeDocker(Docker):
    """In-memory fake Docker operations for unit testing.

    Records all calls for verification in tests. No actual Docker operations
    are performed. All operations succeed by default - configure failures by
    setting daemon_running flag or exit_code.

    Attributes:
        daemon_running: Whether is_daemon_running() returns True (default: True)
        build_calls: List of (dockerfile_path, tag, build_context) tuples
        run_calls: List of (image_tag, volumes, env_vars, command, interactive) tuples
        cleanup_calls: List of container_ids removed
        exit_code: Exit code to return from run_container() (default: 0)

    Example:
        fake = FakeDocker()
        fake.build_image(Path("Dockerfile"), "my-tag", Path("."))
        assert len(fake.build_calls) == 1
        assert fake.build_calls[0][1] == "my-tag"
    """

    def __init__(self) -> None:
        """Initialize fake with empty call history."""
        self.daemon_running = True
        self.build_calls: list[tuple[Path, str, Path]] = []
        self.run_calls: list[tuple[str, dict[str, str], dict[str, str], list[str], bool]] = []
        self.cleanup_calls: list[str] = []
        self.exit_code = 0

    def is_daemon_running(self) -> bool:
        """Return configured daemon status.

        Returns:
            Value of daemon_running attribute (default: True)
        """
        return self.daemon_running

    def build_image(self, dockerfile_path: Path, tag: str, build_context: Path) -> None:
        """Record build_image call.

        LBYL checks (same as real implementation):
        - Validates dockerfile_path exists
        - Validates build_context exists

        Args:
            dockerfile_path: Path to Dockerfile (must exist)
            tag: Image tag
            build_context: Build context directory (must exist)

        Raises:
            FileNotFoundError: If paths don't exist
        """
        # LBYL: Check paths exist (same validation as real implementation)
        if not dockerfile_path.exists():
            raise FileNotFoundError(f"Dockerfile not found: {dockerfile_path}")
        if not build_context.exists():
            raise FileNotFoundError(f"Build context not found: {build_context}")

        # Record call
        self.build_calls.append((dockerfile_path, tag, build_context))

    def run_container(
        self,
        image_tag: str,
        volumes: dict[str, str],
        env_vars: dict[str, str],
        command: list[str],
        interactive: bool = True,
    ) -> int:
        """Record run_container call and return configured exit code.

        LBYL checks (same as real implementation):
        - Validates volume mount paths exist on host

        Args:
            image_tag: Docker image tag
            volumes: Volume mounts
            env_vars: Environment variables
            command: Command to execute
            interactive: Interactive mode flag

        Returns:
            Value of exit_code attribute (default: 0)

        Raises:
            FileNotFoundError: If volume mount paths don't exist
        """
        # LBYL: Check volume mount paths exist (same validation as real)
        for host_path_str in volumes.keys():
            host_path = Path(host_path_str)
            if not host_path.exists():
                raise FileNotFoundError(f"Volume mount path not found: {host_path}")

        # Record call
        self.run_calls.append((image_tag, volumes, env_vars, command, interactive))

        # Return configured exit code
        return self.exit_code

    def cleanup_container(self, container_id: str) -> None:
        """Record cleanup_container call.

        Args:
            container_id: Container ID to remove
        """
        self.cleanup_calls.append(container_id)
