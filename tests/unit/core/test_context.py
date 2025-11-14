"""Tests for context creation and regeneration."""

import os
from pathlib import Path

from workstack.core.context import create_context, regenerate_context


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


def test_create_context_detects_deleted_directory(tmp_path: Path) -> None:
    """Test that create_context exits with clear error when CWD has been deleted."""
    original_cwd = Path.cwd()

    try:
        # Create a temporary directory and cd into it
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        os.chdir(work_dir)

        # Delete the directory while we're still in it
        # This simulates running a command after the directory was removed
        work_dir.rmdir()

        # Now Path.cwd() will fail because we're in a deleted directory
        # Attempt to create context should fail gracefully
        try:
            create_context(dry_run=False)
            # If we get here, the test failed - should have raised SystemExit
            raise AssertionError("Expected SystemExit but context creation succeeded")
        except SystemExit as e:
            # Verify exit code is 1 (error)
            assert e.code == 1

    finally:
        # Cleanup: restore original directory
        os.chdir(original_cwd)


def test_regenerate_context_detects_deleted_directory(tmp_path: Path) -> None:
    """Test that regenerate_context exits with clear error when CWD has been deleted."""
    original_cwd = Path.cwd()

    try:
        # Create initial context
        ctx1 = create_context(dry_run=False)

        # Create a temporary directory and cd into it
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        os.chdir(work_dir)

        # Delete the directory while we're still in it
        work_dir.rmdir()

        # Now Path.cwd() will fail because we're in a deleted directory
        # Attempt to regenerate context should fail gracefully
        try:
            regenerate_context(ctx1)
            # If we get here, the test failed - should have raised SystemExit
            raise AssertionError("Expected SystemExit but context regeneration succeeded")
        except SystemExit as e:
            # Verify exit code is 1 (error)
            assert e.code == 1

    finally:
        # Cleanup: restore original directory
        os.chdir(original_cwd)
