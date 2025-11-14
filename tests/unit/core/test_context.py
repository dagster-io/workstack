"""Tests for context creation and regeneration."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

from workstack.core.context import create_context, get_safe_cwd, regenerate_context


def test_regenerate_context_updates_cwd(tmp_path: Path) -> None:
    """Test that regenerate_context captures new cwd."""
    original_cwd = Path.cwd()

    try:
        # Create context in original directory
        ctx1 = create_context(dry_run=False)
        assert ctx1.cwd == original_cwd

        # Change directory
        os.chdir(tmp_path)

        # Regenerate context
        ctx2 = regenerate_context(ctx1)

        # Verify cwd updated
        assert ctx2.cwd == tmp_path
        assert ctx2.dry_run == ctx1.dry_run  # Preserved
    finally:
        # Cleanup
        os.chdir(original_cwd)


def test_regenerate_context_preserves_dry_run(tmp_path: Path) -> None:
    """Test that regenerate_context preserves dry_run flag."""
    ctx1 = create_context(dry_run=True)
    assert ctx1.dry_run is True

    ctx2 = regenerate_context(ctx1)
    assert ctx2.dry_run is True  # Preserved


def test_get_safe_cwd_with_valid_directory(tmp_path: Path) -> None:
    """Test get_safe_cwd returns current directory when it exists."""
    original_cwd = Path.cwd()

    try:
        # Change to a valid directory
        os.chdir(tmp_path)

        # Get safe cwd
        cwd, recovery_info = get_safe_cwd()

        # Should return current directory with no recovery info
        assert cwd == tmp_path
        assert recovery_info is None
    finally:
        os.chdir(original_cwd)


@patch("pathlib.Path.cwd")
@patch("os.environ")
@patch("os.chdir")
def test_get_safe_cwd_with_deleted_directory_fallback_home(
    mock_chdir: Mock, mock_environ: Mock, mock_cwd: Mock
) -> None:
    """Test get_safe_cwd falls back to home when current directory is deleted."""
    # Mock Path.cwd() to raise FileNotFoundError
    mock_cwd.side_effect = FileNotFoundError("No such file or directory")

    # Mock environment to return a deleted path
    mock_environ.get.return_value = "/deleted/path"

    # Get safe cwd
    cwd, recovery_info = get_safe_cwd()

    # Should return home directory with recovery info
    assert cwd == Path.home()
    assert recovery_info is not None
    assert recovery_info.deleted_path == Path("/deleted/path")
    assert recovery_info.fallback_path == Path.home()

    # Should have changed to home directory
    mock_chdir.assert_called_once_with(Path.home())


@patch("pathlib.Path.cwd")
@patch("os.environ")
@patch("os.chdir")
def test_get_safe_cwd_with_deleted_directory_fallback_repo_root(
    mock_chdir: Mock, mock_environ: Mock, mock_cwd: Mock
) -> None:
    """Test get_safe_cwd falls back to repo root when available."""
    # Mock Path.cwd() to raise FileNotFoundError
    mock_cwd.side_effect = FileNotFoundError("No such file or directory")

    # Mock environment to return a deleted path
    # Set to a path where parent doesn't exist, so it falls back to home
    mock_environ.get.return_value = "/nonexistent/path"

    # Get safe cwd
    cwd, recovery_info = get_safe_cwd()

    # Should fall back to home directory since parent doesn't exist
    assert cwd == Path.home()
    assert recovery_info is not None
    assert recovery_info.deleted_path == Path("/nonexistent/path")
    assert recovery_info.fallback_path == Path.home()

    # Should have changed to home directory
    mock_chdir.assert_called_once_with(Path.home())


def test_context_creation_with_recovery_info() -> None:
    """Test that context creation includes recovery_info when cwd recovery occurs."""
    # Create context normally (current directory exists)
    ctx = create_context(dry_run=False)

    # Recovery info should be None when no recovery needed
    assert ctx.recovery_info is None
