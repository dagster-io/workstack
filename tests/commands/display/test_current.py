"""Tests for the current command."""

import os
import subprocess
from pathlib import Path


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

    # Create a worktree using isolated config
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        ["uv", "run", "workstack", "create", "feature-x", "--no-post"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"Create failed: {result.stderr}"

    # Get worktree path
    worktree_path = workstacks_root / "repo" / "feature-x"
    assert worktree_path.exists()

    # Run current command from worktree directory
    result = subprocess.run(
        ["uv", "run", "workstack", "current"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "feature-x"


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

    # Run current command from root directory
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        ["uv", "run", "workstack", "current"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "root"


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

    # Create a worktree
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        ["uv", "run", "workstack", "create", "feature-y", "--no-post"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0

    # Run current command from a directory outside any worktree
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    result = subprocess.run(
        ["uv", "run", "workstack", "current"],
        cwd=outside_dir,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 1
    assert result.stdout.strip() == ""


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

    # Create a worktree using isolated config
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        ["uv", "run", "workstack", "create", "feature-y", "--no-post"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"Create failed: {result.stderr}"

    # Get worktree path and create subdirectory
    worktree_path = workstacks_root / "repo" / "feature-y"
    assert worktree_path.exists()
    subdir = worktree_path / "src" / "nested"
    subdir.mkdir(parents=True)

    # Run current command from subdirectory
    result = subprocess.run(
        ["uv", "run", "workstack", "current"],
        cwd=subdir,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "feature-y"


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

    # Run current command from non-git directory
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        ["uv", "run", "workstack", "current"],
        cwd=non_git_dir,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 1
    assert result.stdout.strip() == ""
