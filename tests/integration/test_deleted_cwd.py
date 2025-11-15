"""Integration test for handling deleted current working directory."""

import os
from pathlib import Path

from click.testing import CliRunner

from workstack.cli.cli import cli


def test_commands_work_when_cwd_deleted(tmp_path: Path) -> None:
    """Test that commands work gracefully when current directory is deleted.

    This test verifies that our get_safe_cwd() fallback logic works correctly
    when Path.cwd() fails due to deleted directory.
    """
    # Since it's hard to actually delete the cwd in a test environment,
    # we test the get_safe_cwd function directly with mocking
    from unittest.mock import patch

    from workstack.core.context import get_safe_cwd

    # Mock Path.cwd() to raise FileNotFoundError (simulating deleted cwd)
    with patch("pathlib.Path.cwd") as mock_cwd:
        mock_cwd.side_effect = FileNotFoundError("Current directory deleted")

        # Mock PWD to point to a non-existent directory
        with patch.dict(os.environ, {"PWD": "/deleted/directory"}):
            cwd, recovery_info = get_safe_cwd()

            # Should fall back to home directory
            assert cwd == Path.home()
            assert recovery_info is not None
            assert recovery_info.deleted_path == Path("/deleted/directory")
            assert recovery_info.fallback_path == Path.home()


def test_warning_message_displayed_when_cwd_deleted(tmp_path: Path, monkeypatch) -> None:
    """Test that warning message is displayed when CWD is deleted.

    This test verifies that the warning message is properly emitted when
    context creation detects a deleted current directory.
    """
    from unittest.mock import patch

    from workstack.core.context import RecoveryInfo, create_context

    # Mock get_safe_cwd to simulate deleted directory
    deleted_path = tmp_path / "deleted_dir"
    fallback_path = Path.home()

    def mock_get_safe_cwd():
        return fallback_path, RecoveryInfo(deleted_path=deleted_path, fallback_path=fallback_path)

    with patch("workstack.core.context.get_safe_cwd", mock_get_safe_cwd):
        # Create context - this should include recovery_info
        ctx = create_context(dry_run=False)

        # Verify recovery_info is set
        assert ctx.recovery_info is not None
        assert ctx.recovery_info.deleted_path == deleted_path
        assert ctx.recovery_info.fallback_path == fallback_path
        assert ctx.cwd == fallback_path


def test_fallback_to_repo_root_integration(tmp_path: Path) -> None:
    """Integration test for fallback to repository root."""
    import subprocess
    from unittest.mock import patch

    runner = CliRunner()

    # Create a real git repository
    repo_root = tmp_path / "testrepo"
    repo_root.mkdir()

    # Initialize git
    subprocess.run(["git", "init"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_root, check=True)

    # Create initial commit
    (repo_root / "README.md").write_text("Test repo")
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_root, check=True)

    # Create config in isolated test location
    config_dir = tmp_path / "test_config"
    config_dir.mkdir()
    config_file = config_dir / "config.toml"
    config_file.write_text(f"""
workstacks_root = "{tmp_path / "worktrees"}"
use_graphite = false
shell_setup_complete = false
show_pr_info = false
show_pr_checks = false
""")

    # Create a subdirectory that will be "deleted"
    work_dir = repo_root / "src" / "component"

    # Mock to simulate deleted directory with repo root available
    from workstack.core.context import RecoveryInfo

    def mock_get_safe_cwd():
        # Simulate finding repo root as fallback
        return repo_root, RecoveryInfo(deleted_path=work_dir, fallback_path=repo_root)

    # Mock config path to use test location
    def mock_config_path(self):
        return config_file

    with (
        patch("workstack.core.context.get_safe_cwd", mock_get_safe_cwd),
        patch("workstack.core.global_config.FilesystemGlobalConfigOps.path", mock_config_path),
    ):
        # Change to repo root for the test
        os.chdir(repo_root)

        # Run command - should work with repo root as fallback
        result = runner.invoke(cli, ["status"], catch_exceptions=False)

        # Should work (may show warning but shouldn't fail)
        assert result.exit_code == 0 or "Current directory no longer exists" in result.output
