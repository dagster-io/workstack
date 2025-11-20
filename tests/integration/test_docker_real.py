"""Integration tests for RealDocker (Layer 2: Adapter Implementation Tests).

These tests verify the real Docker implementation with mocked subprocess calls.
They ensure code coverage of real implementations without requiring Docker daemon.

Tests that ACTUALLY require Docker daemon are marked with @pytest.mark.docker
and are optional (skipped if Docker not available).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from erk.ops.docker_real import RealDocker


def test_real_docker_is_daemon_running_returns_true_on_success() -> None:
    """is_daemon_running should return True when docker info succeeds."""
    docker = RealDocker()
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = docker.is_daemon_running()

        assert result is True
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["docker", "info"]


def test_real_docker_is_daemon_running_returns_false_on_failure() -> None:
    """is_daemon_running should return False when docker info fails."""
    docker = RealDocker()
    mock_result = MagicMock()
    mock_result.returncode = 1

    with patch("subprocess.run", return_value=mock_result):
        result = docker.is_daemon_running()

        assert result is False


def test_real_docker_is_daemon_running_handles_file_not_found() -> None:
    """is_daemon_running should return False when docker command not found."""
    docker = RealDocker()

    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = docker.is_daemon_running()

        assert result is False


def test_real_docker_build_image_validates_dockerfile_exists(
    tmp_path: Path,
) -> None:
    """build_image should check Dockerfile exists before calling Docker."""
    docker = RealDocker()
    missing_dockerfile = tmp_path / "missing.Dockerfile"
    context = tmp_path

    with pytest.raises(FileNotFoundError, match="Dockerfile not found"):
        docker.build_image(missing_dockerfile, "my-tag", context)


def test_real_docker_build_image_validates_context_exists(tmp_path: Path) -> None:
    """build_image should check build context exists before calling Docker."""
    docker = RealDocker()
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.13")
    missing_context = tmp_path / "missing-dir"

    with pytest.raises(FileNotFoundError, match="Build context not found"):
        docker.build_image(dockerfile, "my-tag", missing_context)


def test_real_docker_build_image_calls_docker_build(tmp_path: Path) -> None:
    """build_image should call docker build with correct arguments."""
    docker = RealDocker()
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.13")
    context = tmp_path

    with patch("subprocess.run") as mock_run:
        docker.build_image(dockerfile, "my-tag:latest", context)

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == [
            "docker",
            "build",
            "-f",
            str(dockerfile),
            "-t",
            "my-tag:latest",
            str(context),
        ]


def test_real_docker_run_container_validates_volume_paths(tmp_path: Path) -> None:
    """run_container should check volume mount paths exist before running."""
    docker = RealDocker()
    missing_path = tmp_path / "missing-dir"
    volumes = {str(missing_path): "/workspace"}

    with pytest.raises(FileNotFoundError, match="Volume mount path not found"):
        docker.run_container("my-image", volumes, {}, ["echo"])


def test_real_docker_run_container_calls_docker_run(tmp_path: Path) -> None:
    """run_container should call docker run with correct arguments."""
    docker = RealDocker()
    volumes = {str(tmp_path): "/workspace"}
    env_vars = {"FOO": "bar", "BAZ": "qux"}
    command = ["python", "-c", "print('hello')"]
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        exit_code = docker.run_container(
            "my-image:latest", volumes, env_vars, command, interactive=True
        )

        assert exit_code == 0
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]

        # Verify command structure
        assert call_args[0:3] == ["docker", "run", "--rm"]
        assert "-it" in call_args
        assert "-v" in call_args
        assert f"{tmp_path}:/workspace" in call_args
        assert "-e" in call_args
        assert "my-image:latest" in call_args


def test_real_docker_run_container_returns_exit_code(tmp_path: Path) -> None:
    """run_container should return container exit code."""
    docker = RealDocker()
    volumes = {str(tmp_path): "/workspace"}
    mock_result = MagicMock()
    mock_result.returncode = 42

    with patch("subprocess.run", return_value=mock_result):
        exit_code = docker.run_container("my-image", volumes, {}, ["echo"])

        assert exit_code == 42


def test_real_docker_cleanup_container_calls_docker_rm() -> None:
    """cleanup_container should call docker rm with container ID."""
    docker = RealDocker()

    with patch("subprocess.run") as mock_run:
        docker.cleanup_container("container-123")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["docker", "rm", "-f", "container-123"]


# Optional integration tests that require Docker daemon
# Run with: pytest -m docker


@pytest.mark.docker
def test_docker_daemon_is_accessible() -> None:
    """Integration test: Verify Docker daemon is running and accessible."""
    docker = RealDocker()

    # This test requires Docker daemon to be running
    is_running = docker.is_daemon_running()

    # If Docker is installed and running, this should be True
    # If not, this test will be skipped (see pytest.mark.docker)
    assert is_running is True, "Docker daemon should be running for integration tests"
