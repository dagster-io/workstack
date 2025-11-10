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


def test_regenerate_context_updates_trunk_branch(tmp_path: Path) -> None:
    """Test that regenerate_context reads fresh trunk_branch."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create pyproject.toml with trunk
    pyproject = repo_root / "pyproject.toml"
    pyproject.write_text("[tool.workstack]\ntrunk_branch = 'main'\n", encoding="utf-8")

    ctx1 = create_context(dry_run=False, repo_root=repo_root)
    assert ctx1.trunk_branch == "main"

    # Update pyproject.toml
    pyproject.write_text("[tool.workstack]\ntrunk_branch = 'master'\n", encoding="utf-8")

    # Regenerate
    ctx2 = regenerate_context(ctx1, repo_root=repo_root)

    # Verify trunk_branch updated
    assert ctx2.trunk_branch == "master"


def test_regenerate_context_without_repo_root(tmp_path: Path) -> None:
    """Test regenerate_context without repo_root sets trunk_branch to None."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create pyproject.toml with trunk
    pyproject = repo_root / "pyproject.toml"
    pyproject.write_text("[tool.workstack]\ntrunk_branch = 'main'\n", encoding="utf-8")

    ctx1 = create_context(dry_run=False, repo_root=repo_root)
    assert ctx1.trunk_branch is not None  # Has a value from repo_root

    ctx2 = regenerate_context(ctx1)  # No repo_root
    assert ctx2.trunk_branch is None  # Reset to None
