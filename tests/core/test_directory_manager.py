"""Tests for directory change manager."""

import os
from pathlib import Path

import pytest

from tests.fakes.context import create_test_context
from workstack.core.directory_manager import change_directory


def test_change_directory_updates_context_cwd(tmp_path: Path) -> None:
    """Test that change_directory updates ctx.cwd correctly."""
    # Create test directories
    original_dir = tmp_path / "original"
    target_dir = tmp_path / "target"
    original_dir.mkdir()
    target_dir.mkdir()

    # Start in original directory
    os.chdir(original_dir)

    # Create test context with cwd matching current directory
    ctx = create_test_context(cwd=original_dir)
    assert ctx.cwd == original_dir

    # Change directory using context manager
    with change_directory(ctx, target_dir, repo_root=tmp_path) as new_ctx:
        # Verify we're in target directory
        assert Path.cwd() == target_dir
        # Verify context was regenerated with new cwd
        assert new_ctx.cwd == target_dir

    # Verify we're back in original directory after exiting context
    assert Path.cwd() == original_dir


def test_change_directory_restores_on_exception(tmp_path: Path) -> None:
    """Test that change_directory restores original directory on exception."""
    # Create test directories
    original_dir = tmp_path / "original"
    target_dir = tmp_path / "target"
    original_dir.mkdir()
    target_dir.mkdir()

    # Start in original directory
    os.chdir(original_dir)

    # Create test context
    ctx = create_test_context(cwd=original_dir)

    # Raise exception inside context manager
    with pytest.raises(ValueError, match="test exception"):
        with change_directory(ctx, target_dir, repo_root=tmp_path):
            # Verify we changed to target
            assert Path.cwd() == target_dir
            # Raise exception
            raise ValueError("test exception")

    # Verify we're back in original directory even after exception
    assert Path.cwd() == original_dir


def test_change_directory_nested_contexts(tmp_path: Path) -> None:
    """Test that nested change_directory calls work correctly."""
    # Create test directories
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir3 = tmp_path / "dir3"
    dir1.mkdir()
    dir2.mkdir()
    dir3.mkdir()

    # Start in dir1
    os.chdir(dir1)

    # Create test context
    ctx = create_test_context(cwd=dir1)

    # Nested context managers
    with change_directory(ctx, dir2, repo_root=tmp_path) as ctx2:
        assert Path.cwd() == dir2
        assert ctx2.cwd == dir2

        with change_directory(ctx2, dir3, repo_root=tmp_path) as ctx3:
            assert Path.cwd() == dir3
            assert ctx3.cwd == dir3

        # Back to dir2
        assert Path.cwd() == dir2

    # Back to dir1
    assert Path.cwd() == dir1


def test_change_directory_preserves_dry_run_state(tmp_path: Path) -> None:
    """Test that change_directory preserves dry_run state during regeneration."""
    # Create test directories
    original_dir = tmp_path / "original"
    target_dir = tmp_path / "target"
    original_dir.mkdir()
    target_dir.mkdir()

    # Start in original directory
    os.chdir(original_dir)

    # Create test context with dry_run=True
    ctx = create_test_context(cwd=original_dir, dry_run=True)
    assert ctx.dry_run is True

    # Change directory using context manager
    with change_directory(ctx, target_dir, repo_root=tmp_path) as new_ctx:
        # Verify dry_run state is preserved
        assert new_ctx.dry_run is True
        # Verify directory changed
        assert Path.cwd() == target_dir
        assert new_ctx.cwd == target_dir

    # Verify we're back in original directory
    assert Path.cwd() == original_dir
