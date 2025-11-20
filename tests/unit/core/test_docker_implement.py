"""Tests for Docker orchestration logic (Layer 3: Business Logic Tests).

These tests verify orchestration functions over FakeDocker.
This is where the majority of tests should be - testing business logic
extensively over fast in-memory fakes.
"""

from pathlib import Path

import pytest
from tests.fakes.docker_fake import FakeDocker

from erk.core.docker_implement import (
    build_implementation_image,
    execute_docker_implementation,
    setup_container_volumes,
)


def test_build_implementation_image_generates_unique_tag(tmp_path: Path) -> None:
    """build_implementation_image should generate unique image tag."""
    fake = FakeDocker()
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()

    # Create sandbox Dockerfile
    sandbox = worktree / ".erk" / "sandboxes" / "default"
    sandbox.mkdir(parents=True)
    dockerfile = sandbox / "Dockerfile"
    dockerfile.write_text("FROM python:3.13")

    image_tag = build_implementation_image(fake, worktree, "default")

    assert image_tag.startswith("erk-implement-my-worktree:")
    assert len(fake.build_calls) == 1
    assert fake.build_calls[0][0] == dockerfile  # Dockerfile path
    assert fake.build_calls[0][1] == image_tag  # Tag
    assert fake.build_calls[0][2] == worktree  # Build context


def test_build_implementation_image_fails_if_dockerfile_missing(tmp_path: Path) -> None:
    """build_implementation_image should fail if Dockerfile doesn't exist."""
    fake = FakeDocker()
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()

    # No sandbox Dockerfile created

    with pytest.raises(FileNotFoundError, match="Sandbox Dockerfile not found.*default/Dockerfile"):
        build_implementation_image(fake, worktree, "default")


def test_setup_container_volumes_includes_worktree(tmp_path: Path) -> None:
    """setup_container_volumes should mount worktree at /workspace."""
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()

    volumes = setup_container_volumes(worktree)

    # Should include worktree mount (absolute path)
    worktree_absolute = str(worktree.resolve())
    assert worktree_absolute in volumes
    assert volumes[worktree_absolute] == "/workspace"


def test_setup_container_volumes_includes_git_config_if_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """setup_container_volumes should mount git config if it exists."""
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()

    # Mock home directory with git config
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    gitconfig = fake_home / ".gitconfig"
    gitconfig.write_text("[user]\nname = Test User")
    monkeypatch.setenv("HOME", str(fake_home))

    volumes = setup_container_volumes(worktree)

    # Should include git config (read-only)
    gitconfig_absolute = str(gitconfig.resolve())
    assert gitconfig_absolute in volumes
    assert volumes[gitconfig_absolute] == "/root/.gitconfig:ro"


def test_setup_container_volumes_includes_ssh_if_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """setup_container_volumes should mount SSH directory if it exists."""
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()

    # Mock home directory with SSH
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    ssh_dir = fake_home / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_rsa").write_text("fake key")
    monkeypatch.setenv("HOME", str(fake_home))

    volumes = setup_container_volumes(worktree)

    # Should include SSH directory (read-only)
    ssh_absolute = str(ssh_dir.resolve())
    assert ssh_absolute in volumes
    assert volumes[ssh_absolute] == "/root/.ssh:ro"


def test_setup_container_volumes_fails_if_worktree_missing(tmp_path: Path) -> None:
    """setup_container_volumes should fail if worktree doesn't exist."""
    missing_worktree = tmp_path / "missing"

    with pytest.raises(FileNotFoundError, match="Worktree not found"):
        setup_container_volumes(missing_worktree)


def test_execute_docker_implementation_checks_daemon_running(tmp_path: Path) -> None:
    """execute_docker_implementation should check Docker daemon first."""
    fake = FakeDocker()
    fake.daemon_running = False
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()

    with pytest.raises(RuntimeError, match="Docker daemon not running"):
        execute_docker_implementation(fake, worktree, "default")


def test_execute_docker_implementation_checks_plan_exists(tmp_path: Path) -> None:
    """execute_docker_implementation should check plan.md exists."""
    fake = FakeDocker()
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()

    # No .plan/plan.md created

    with pytest.raises(FileNotFoundError, match="No plan found.*plan.md"):
        execute_docker_implementation(fake, worktree, "default")


def test_execute_docker_implementation_builds_and_runs(tmp_path: Path) -> None:
    """execute_docker_implementation should build image and run container."""
    fake = FakeDocker()
    fake.exit_code = 0

    # Setup worktree with plan and sandbox
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()
    plan_dir = worktree / ".plan"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text("# Test Plan")

    sandbox = worktree / ".erk" / "sandboxes" / "default"
    sandbox.mkdir(parents=True)
    dockerfile = sandbox / "Dockerfile"
    dockerfile.write_text("FROM python:3.13")

    exit_code = execute_docker_implementation(fake, worktree, "default")

    # Should build image
    assert len(fake.build_calls) == 1
    assert fake.build_calls[0][0] == dockerfile

    # Should run container
    assert len(fake.run_calls) == 1
    run_call = fake.run_calls[0]
    assert run_call[0].startswith("erk-implement-my-worktree:")  # Image tag
    assert "/workspace" in run_call[1].values()  # Volume mount
    assert run_call[3] == [
        "claude",
        "--permission-mode",
        "acceptEdits",
        "/erk:implement-plan",
    ]  # Command
    assert run_call[4] is True  # Interactive

    # Should return exit code
    assert exit_code == 0


def test_execute_docker_implementation_propagates_exit_code(tmp_path: Path) -> None:
    """execute_docker_implementation should propagate container exit code."""
    fake = FakeDocker()
    fake.exit_code = 42

    # Setup worktree
    worktree = tmp_path / "my-worktree"
    worktree.mkdir()
    (worktree / ".plan").mkdir()
    (worktree / ".plan" / "plan.md").write_text("# Plan")
    sandbox = worktree / ".erk" / "sandboxes" / "default"
    sandbox.mkdir(parents=True)
    (sandbox / "Dockerfile").write_text("FROM python:3.13")

    exit_code = execute_docker_implementation(fake, worktree, "default")

    assert exit_code == 42
