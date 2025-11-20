"""Tests for FakeDocker (Layer 1: Fake Infrastructure Tests).

These tests verify the fake implementation itself works correctly.
They ensure the test infrastructure is reliable for higher-layer tests.
"""

from pathlib import Path

import pytest
from tests.fakes.docker_fake import FakeDocker


def test_fake_docker_records_build_calls(tmp_path: Path) -> None:
    """FakeDocker should record build_image calls."""
    fake = FakeDocker()
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.13")
    context = tmp_path

    fake.build_image(dockerfile, "my-tag:latest", context)

    assert len(fake.build_calls) == 1
    assert fake.build_calls[0] == (dockerfile, "my-tag:latest", context)


def test_fake_docker_validates_dockerfile_exists(tmp_path: Path) -> None:
    """FakeDocker should check Dockerfile exists (LBYL)."""
    fake = FakeDocker()
    missing_dockerfile = tmp_path / "missing.Dockerfile"
    context = tmp_path

    with pytest.raises(FileNotFoundError, match="Dockerfile not found"):
        fake.build_image(missing_dockerfile, "my-tag", context)


def test_fake_docker_validates_build_context_exists(tmp_path: Path) -> None:
    """FakeDocker should check build context exists (LBYL)."""
    fake = FakeDocker()
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.13")
    missing_context = tmp_path / "missing-dir"

    with pytest.raises(FileNotFoundError, match="Build context not found"):
        fake.build_image(dockerfile, "my-tag", missing_context)


def test_fake_docker_records_run_calls(tmp_path: Path) -> None:
    """FakeDocker should record run_container calls."""
    fake = FakeDocker()
    volumes = {str(tmp_path): "/workspace"}
    env_vars = {"FOO": "bar"}
    command = ["echo", "hello"]

    exit_code = fake.run_container("my-image:latest", volumes, env_vars, command, interactive=True)

    assert exit_code == 0  # Default exit code
    assert len(fake.run_calls) == 1
    assert fake.run_calls[0] == ("my-image:latest", volumes, env_vars, command, True)


def test_fake_docker_returns_configured_exit_code(tmp_path: Path) -> None:
    """FakeDocker should return configurable exit code."""
    fake = FakeDocker()
    fake.exit_code = 42
    volumes = {str(tmp_path): "/workspace"}

    exit_code = fake.run_container("my-image", volumes, {}, ["echo"])

    assert exit_code == 42


def test_fake_docker_validates_volume_paths_exist(tmp_path: Path) -> None:
    """FakeDocker should check volume mount paths exist (LBYL)."""
    fake = FakeDocker()
    missing_path = tmp_path / "missing-dir"
    volumes = {str(missing_path): "/workspace"}

    with pytest.raises(FileNotFoundError, match="Volume mount path not found"):
        fake.run_container("my-image", volumes, {}, ["echo"])


def test_fake_docker_records_cleanup_calls() -> None:
    """FakeDocker should record cleanup_container calls."""
    fake = FakeDocker()

    fake.cleanup_container("container-123")
    fake.cleanup_container("container-456")

    assert fake.cleanup_calls == ["container-123", "container-456"]


def test_fake_docker_daemon_running_configurable() -> None:
    """FakeDocker should allow configuring daemon_running."""
    fake = FakeDocker()

    # Default: daemon running
    assert fake.is_daemon_running() is True

    # Configure: daemon not running
    fake.daemon_running = False
    assert fake.is_daemon_running() is False
