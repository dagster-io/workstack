"""Real Docker operations using subprocess to call Docker CLI.

This module provides the production implementation of Docker interface,
using subprocess to interact with Docker daemon via Docker CLI.

All operations follow LBYL philosophy: check conditions before acting,
let exceptions bubble to error boundaries.
"""

import subprocess
from pathlib import Path

from erk.ops.docker import Docker


class RealDocker(Docker):
    """Real Docker operations using Docker CLI via subprocess.

    This implementation calls Docker CLI commands using subprocess.run().
    All operations follow LBYL pattern:
    - Check Docker daemon running before operations
    - Validate paths exist before passing to Docker
    - Use check=True for subprocess calls (let exceptions bubble)

    Example:
        docker = RealDocker()
        if not docker.is_daemon_running():
            raise RuntimeError("Docker daemon not running")
        docker.build_image(dockerfile, "my-tag:latest", context_dir)
    """

    def is_daemon_running(self) -> bool:
        """Check if Docker daemon is running.

        Returns:
            True if Docker daemon responds to `docker info`, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                check=False,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def build_image(self, dockerfile_path: Path, tag: str, build_context: Path) -> None:
        """Build Docker image from Dockerfile.

        LBYL checks:
        - Validates dockerfile_path exists
        - Validates build_context exists
        - Docker daemon running checked by caller

        Args:
            dockerfile_path: Path to Dockerfile (must exist)
            tag: Image tag to use
            build_context: Directory to use as build context (must exist)

        Raises:
            FileNotFoundError: If dockerfile_path or build_context don't exist
            RuntimeError: If Docker build fails
        """
        # LBYL: Check paths exist before passing to Docker
        if not dockerfile_path.exists():
            raise FileNotFoundError(f"Dockerfile not found: {dockerfile_path}")
        if not build_context.exists():
            raise FileNotFoundError(f"Build context not found: {build_context}")

        # Build Docker image
        # Let subprocess exceptions bubble (check=True)
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(dockerfile_path),
                "-t",
                tag,
                str(build_context),
            ],
            check=True,
        )

    def run_container(
        self,
        image_tag: str,
        volumes: dict[str, str],
        env_vars: dict[str, str],
        command: list[str],
        interactive: bool = True,
    ) -> int:
        """Run Docker container with specified configuration.

        LBYL checks:
        - Validates volume mount paths exist on host
        - Docker daemon running checked by caller

        Args:
            image_tag: Docker image tag to run
            volumes: Volume mounts (host_path:container_path format)
            env_vars: Environment variables
            command: Command to execute
            interactive: Attach TTY for interactive sessions

        Returns:
            Exit code from container

        Raises:
            FileNotFoundError: If volume mount paths don't exist
            RuntimeError: If container execution fails
        """
        # LBYL: Check volume mount paths exist
        for host_path_str in volumes.keys():
            host_path = Path(host_path_str)
            if not host_path.exists():
                raise FileNotFoundError(f"Volume mount path not found: {host_path}")

        # Build docker run command
        docker_cmd = ["docker", "run", "--rm"]

        # Add interactive TTY flags if needed
        if interactive:
            docker_cmd.extend(["-it"])

        # Add volume mounts
        for host_path, container_path in volumes.items():
            docker_cmd.extend(["-v", f"{host_path}:{container_path}"])

        # Add environment variables
        for key, value in env_vars.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        # Add image and command
        docker_cmd.append(image_tag)
        docker_cmd.extend(command)

        # Run container
        # Let subprocess exceptions bubble (check=True NOT used - we want exit code)
        result = subprocess.run(docker_cmd, check=False)
        return result.returncode

    def cleanup_container(self, container_id: str) -> None:
        """Remove Docker container.

        Note: When using --rm flag in run_container, cleanup is automatic.
        This method is for cases where containers are created without --rm.

        Args:
            container_id: Container ID to remove

        Raises:
            RuntimeError: If container removal fails
        """
        # Let subprocess exceptions bubble (check=True)
        subprocess.run(["docker", "rm", "-f", container_id], check=True)
