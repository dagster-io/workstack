"""Tests for shell utility functions."""

from pathlib import Path

from erk.cli.activation import render_activation_script
from erk.cli.shell_utils import render_cd_script, render_navigation_script


def test_render_navigation_script_root_worktree(tmp_path: Path) -> None:
    """Root worktree should generate simple cd script."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    result = render_navigation_script(
        repo_root,
        repo_root,
        comment="test navigation to root",
        success_message="At root",
    )

    # Should contain cd command
    assert "cd" in result
    # Should NOT contain venv activation keywords
    assert "uv sync" not in result
    assert "VIRTUAL_ENV" not in result
    assert ".venv" not in result


def test_render_navigation_script_non_root_worktree(tmp_path: Path) -> None:
    """Non-root worktree should generate full activation script."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()

    result = render_navigation_script(
        worktree_path,
        repo_root,
        comment="test navigation to worktree",
        success_message="At worktree",
    )

    # Should contain venv activation keywords
    assert "uv sync" in result
    assert "VIRTUAL_ENV" in result
    # Should also contain cd command
    assert "cd" in result


def test_render_navigation_script_root_matches_cd_script(tmp_path: Path) -> None:
    """Root path should generate same output as direct render_cd_script() call."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    navigation_result = render_navigation_script(
        repo_root,
        repo_root,
        comment="test comment",
        success_message="Success",
    )

    cd_result = render_cd_script(
        repo_root,
        comment="test comment",
        success_message="Success",
    )

    assert navigation_result == cd_result


def test_render_navigation_script_non_root_matches_activation_script(tmp_path: Path) -> None:
    """Non-root path should generate same output as direct render_activation_script() call."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()

    navigation_result = render_navigation_script(
        worktree_path,
        repo_root,
        comment="test comment",
        success_message="Success",
    )

    activation_result = render_activation_script(
        worktree_path=worktree_path,
        final_message='echo "Success"',
        comment="test comment",
    )

    assert navigation_result == activation_result
