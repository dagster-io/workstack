"""Tests for the current command."""

import os
import subprocess
from pathlib import Path

from click.testing import CliRunner

from workstack.cli.cli import cli


def test_current_returns_worktree_name(tmp_path: Path) -> None:
    """Test that current returns worktree name when in named worktree."""
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n'
    )

    # Set up a fake git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create an initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Create a worktree using CliRunner with isolated config
    env_vars = os.environ.copy()
    env_vars["HOME"] = str(tmp_path)
    runner = CliRunner(env=env_vars)

    # Change to repo directory and create worktree
    original_cwd = os.getcwd()
    try:
        os.chdir(repo)
        result = runner.invoke(cli, ["create", "feature-x", "--no-post"])
        assert result.exit_code == 0, f"Create failed: {result.output}"

        # Get worktree path
        worktree_path = workstacks_root / "repo" / "feature-x"
        assert worktree_path.exists()

        # Run current command from worktree directory
        os.chdir(worktree_path)
        result = runner.invoke(cli, ["current"])

        assert result.exit_code == 0
        assert result.output.strip() == "feature-x"
    finally:
        os.chdir(original_cwd)


def test_current_returns_root_in_root_repository(tmp_path: Path) -> None:
    """Test that current returns 'root' when in root repository."""
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n'
    )

    # Set up a fake git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create an initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Run current command from root directory using CliRunner
    env_vars = os.environ.copy()
    env_vars["HOME"] = str(tmp_path)
    runner = CliRunner(env=env_vars)

    original_cwd = os.getcwd()
    try:
        os.chdir(repo)
        result = runner.invoke(cli, ["current"])

        assert result.exit_code == 0
        assert result.output.strip() == "root"
    finally:
        os.chdir(original_cwd)


def test_current_exits_with_error_when_not_in_worktree(tmp_path: Path) -> None:
    """Test that current exits with code 1 when not in any worktree."""
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n'
    )

    # Set up a fake git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create an initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Create a worktree using CliRunner
    env_vars = os.environ.copy()
    env_vars["HOME"] = str(tmp_path)
    runner = CliRunner(env=env_vars)

    original_cwd = os.getcwd()
    try:
        os.chdir(repo)
        result = runner.invoke(cli, ["create", "feature-y", "--no-post"])
        assert result.exit_code == 0

        # Run current command from a directory outside any worktree
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        os.chdir(outside_dir)
        result = runner.invoke(cli, ["current"])

        assert result.exit_code == 1
        assert result.output.strip() == ""
    finally:
        os.chdir(original_cwd)


def test_current_works_from_subdirectory(tmp_path: Path) -> None:
    """Test that current returns worktree name from subdirectory within worktree."""
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n'
    )

    # Set up a fake git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)

    # Create an initial commit
    (repo / "README.md").write_text("test")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True)

    # Create a worktree using CliRunner with isolated config
    env_vars = os.environ.copy()
    env_vars["HOME"] = str(tmp_path)
    runner = CliRunner(env=env_vars)

    original_cwd = os.getcwd()
    try:
        os.chdir(repo)
        result = runner.invoke(cli, ["create", "feature-y", "--no-post"])
        assert result.exit_code == 0, f"Create failed: {result.output}"

        # Get worktree path and create subdirectory
        worktree_path = workstacks_root / "repo" / "feature-y"
        assert worktree_path.exists()
        subdir = worktree_path / "src" / "nested"
        subdir.mkdir(parents=True)

        # Run current command from subdirectory
        os.chdir(subdir)
        result = runner.invoke(cli, ["current"])

        assert result.exit_code == 0
        assert result.output.strip() == "feature-y"
    finally:
        os.chdir(original_cwd)


def test_current_handles_missing_git_gracefully(tmp_path: Path) -> None:
    """Test that current exits with code 1 when not in a git repository."""
    # Set up isolated global config
    global_config_dir = tmp_path / ".workstack"
    global_config_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"
    (global_config_dir / "config.toml").write_text(
        f'workstacks_root = "{workstacks_root}"\nuse_graphite = false\n'
    )

    # Create a non-git directory
    non_git_dir = tmp_path / "not-git"
    non_git_dir.mkdir()

    # Run current command from non-git directory using CliRunner
    env_vars = os.environ.copy()
    env_vars["HOME"] = str(tmp_path)
    runner = CliRunner(env=env_vars)

    original_cwd = os.getcwd()
    try:
        os.chdir(non_git_dir)
        result = runner.invoke(cli, ["current"])

        assert result.exit_code == 1
        assert result.output.strip() == ""
    finally:
        os.chdir(original_cwd)
