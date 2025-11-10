"""Unit tests for trunk branch detection logic.

These tests verify the business logic of `_is_trunk_branch` function, which determines
whether a branch should be treated as a trunk (main/master/develop) based on Graphite
cache metadata.

Business logic rules:
1. Branch with validationResult == "TRUNK" → True
2. Branch with no parent (parentBranchName == None) → True
3. Branch with a parent → False
4. Branch not in cache → False (default behavior)
"""

import json
from pathlib import Path

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.commands.list import _is_trunk_branch
from workstack.core.context import WorkstackContext
from workstack.core.global_config import GlobalConfig


def test_branch_with_trunk_validation_result(tmp_path: Path) -> None:
    """Branch with validationResult == "TRUNK" is identified as trunk."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Create graphite cache with main marked as TRUNK
    graphite_cache = {
        "branches": [
            ["main", {"validationResult": "TRUNK", "children": ["feature-1"]}],
            ["feature-1", {"parentBranchName": "main", "children": []}],
        ]
    }
    (git_dir / ".graphite_cache_persist").write_text(json.dumps(graphite_cache), encoding="utf-8")

    git_ops = FakeGitOps(git_common_dirs={tmp_path: git_dir})
    global_config_ops = GlobalConfig(
        workstacks_root=tmp_path / "workstacks",
        use_graphite=True,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )
    ctx = WorkstackContext(
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        graphite_ops=FakeGraphiteOps(),
        github_ops=FakeGitHubOps(),
        shell_ops=FakeShellOps(),
        cwd=Path("/test/default/cwd"),
        dry_run=False,
    )

    assert _is_trunk_branch(ctx, tmp_path, "main") is True


def test_branch_with_no_parent_is_trunk(tmp_path: Path) -> None:
    """Branch with parentBranchName == None but no TRUNK marker is still trunk."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    # Create graphite cache with orphan branch (no parent, but not marked TRUNK)
    graphite_cache = {
        "branches": [
            ["orphan", {"parentBranchName": None, "children": ["feature-1"]}],
            ["feature-1", {"parentBranchName": "orphan", "children": []}],
        ]
    }
    (git_dir / ".graphite_cache_persist").write_text(json.dumps(graphite_cache), encoding="utf-8")

    git_ops = FakeGitOps(git_common_dirs={tmp_path: git_dir})
    global_config_ops = GlobalConfig(
        workstacks_root=tmp_path / "workstacks",
        use_graphite=True,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )
    ctx = WorkstackContext(
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        graphite_ops=FakeGraphiteOps(),
        github_ops=FakeGitHubOps(),
        shell_ops=FakeShellOps(),
        cwd=Path("/test/default/cwd"),
        dry_run=False,
    )

    assert _is_trunk_branch(ctx, tmp_path, "orphan") is True


def test_branch_with_parent_is_not_trunk(tmp_path: Path) -> None:
    """Branch with parentBranchName is not a trunk."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    graphite_cache = {
        "branches": [
            ["main", {"validationResult": "TRUNK", "children": ["feature-1"]}],
            ["feature-1", {"parentBranchName": "main", "children": []}],
        ]
    }
    (git_dir / ".graphite_cache_persist").write_text(json.dumps(graphite_cache), encoding="utf-8")

    git_ops = FakeGitOps(git_common_dirs={tmp_path: git_dir})
    global_config_ops = GlobalConfig(
        workstacks_root=tmp_path / "workstacks",
        use_graphite=True,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )
    ctx = WorkstackContext(
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        graphite_ops=FakeGraphiteOps(),
        github_ops=FakeGitHubOps(),
        shell_ops=FakeShellOps(),
        cwd=Path("/test/default/cwd"),
        dry_run=False,
    )

    assert _is_trunk_branch(ctx, tmp_path, "feature-1") is False


def test_branch_not_in_cache_is_not_trunk(tmp_path: Path) -> None:
    """Branch not present in graphite cache is not a trunk."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    graphite_cache = {
        "branches": [
            ["main", {"validationResult": "TRUNK", "children": []}],
        ]
    }
    (git_dir / ".graphite_cache_persist").write_text(json.dumps(graphite_cache), encoding="utf-8")

    git_ops = FakeGitOps(git_common_dirs={tmp_path: git_dir})
    global_config_ops = GlobalConfig(
        workstacks_root=tmp_path / "workstacks",
        use_graphite=True,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )
    ctx = WorkstackContext(
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        graphite_ops=FakeGraphiteOps(),
        github_ops=FakeGitHubOps(),
        shell_ops=FakeShellOps(),
        cwd=Path("/test/default/cwd"),
        dry_run=False,
    )

    # Query for branch not in cache
    assert _is_trunk_branch(ctx, tmp_path, "unknown-branch") is False


def test_graphite_disabled_returns_false(tmp_path: Path) -> None:
    """When Graphite is disabled, trunk detection returns False."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    git_ops = FakeGitOps(git_common_dirs={tmp_path: git_dir})
    global_config_ops = GlobalConfig(
        workstacks_root=tmp_path / "workstacks",
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )
    ctx = WorkstackContext(
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        graphite_ops=FakeGraphiteOps(),
        github_ops=FakeGitHubOps(),
        shell_ops=FakeShellOps(),
        cwd=Path("/test/default/cwd"),
        dry_run=False,
    )

    # Without Graphite, should return False (no way to detect trunk)
    assert _is_trunk_branch(ctx, tmp_path, "main") is False
