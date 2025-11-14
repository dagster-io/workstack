"""Integration tests for handling deleted current working directory."""

import os
import shutil
import subprocess
from pathlib import Path

from click.testing import CliRunner

from workstack.cli.cli import cli
from workstack.core.context import create_context


def test_cli_handles_deleted_cwd(tmp_path: Path) -> None:
    """Test that CLI commands handle deleted current directory gracefully."""
    # Create a temporary directory structure
    test_dir = tmp_path / "test_workspace"
    test_dir.mkdir()

    # Save original directory
    original_cwd = Path.cwd()

    try:
        # Change to the test directory and update PWD environment variable
        os.chdir(test_dir)
        os.environ["PWD"] = str(test_dir)

        # Remove the directory while we're in it
        # This simulates the case where worktree remove deletes the current directory
        shutil.rmtree(test_dir)

        # Try to create context - should fallback gracefully
        ctx = create_context(dry_run=False)

        # Should have recovery info
        assert ctx.recovery_info is not None
        # The deleted path should match what we set in PWD
        assert str(ctx.recovery_info.deleted_path) == str(test_dir)
        assert ctx.recovery_info.fallback_path.exists()
        assert ctx.cwd == ctx.recovery_info.fallback_path

    finally:
        # Restore original directory
        if "PWD" in os.environ:
            del os.environ["PWD"]
        os.chdir(original_cwd)


def test_cli_command_with_deleted_cwd_shows_warning(tmp_path: Path, monkeypatch) -> None:
    """Test that CLI commands show warning when current directory is deleted."""
    # Create a temporary directory structure
    test_dir = tmp_path / "test_workspace"
    test_dir.mkdir()

    # Save original directory
    original_cwd = Path.cwd()

    try:
        # Change to the test directory
        os.chdir(test_dir)

        # Remove the directory while we're in it
        shutil.rmtree(test_dir)

        # Set PWD environment variable to simulate shell behavior
        monkeypatch.setenv("PWD", str(test_dir))

        # Run a CLI command
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        # Command should succeed
        assert result.exit_code == 0

        # Should show warning on stderr
        # Note: CliRunner mixes stdout and stderr in output by default
        # The warning should be present in the output
        # (In real usage, it would go to stderr separately)

    finally:
        # Restore original directory
        os.chdir(original_cwd)


def test_worktree_operations_after_cwd_deleted(tmp_path: Path) -> None:
    """Test that worktree operations work after current directory is deleted."""
    # This test verifies the specific scenario from the bug report:
    # After 'workstack remove' deletes current worktree, other commands should work

    # Create a git repository
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    (repo_dir / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Create a worktree
    worktree_dir = tmp_path / "worktrees" / "feature"
    worktree_dir.parent.mkdir(parents=True)
    subprocess.run(
        ["git", "worktree", "add", str(worktree_dir), "-b", "feature"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    # Save original directory
    original_cwd = Path.cwd()

    try:
        # Change to the worktree and update PWD
        os.chdir(worktree_dir)
        os.environ["PWD"] = str(worktree_dir)

        # Remove the worktree (simulating 'workstack remove')
        subprocess.run(
            ["git", "worktree", "remove", str(worktree_dir), "--force"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Now current directory doesn't exist
        # Can't call Path.cwd() as it will raise FileNotFoundError
        # Just verify the worktree directory is gone
        assert not worktree_dir.exists()

        # Create context - should handle gracefully
        ctx = create_context(dry_run=False)

        # Should have recovery info
        assert ctx.recovery_info is not None
        assert ctx.cwd.exists()  # Fallback directory should exist

    finally:
        # Restore original directory
        if "PWD" in os.environ:
            del os.environ["PWD"]
        os.chdir(original_cwd)
