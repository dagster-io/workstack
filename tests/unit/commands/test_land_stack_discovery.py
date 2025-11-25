"""Tests for land_stack discovery module.

These tests verify the _get_branches_to_land() function behavior with and without
the down_only flag.
"""

from pathlib import Path

from erk_shared.integrations.graphite.fake import FakeGraphite

from erk.cli.commands.stack.land_old.discovery import _get_branches_to_land
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.git.fake import FakeGit
from tests.test_utils.builders import BranchStackBuilder


def test_get_branches_to_land_full_stack_default() -> None:
    """Default behavior (down_only=False) returns entire stack."""
    # Arrange: Set up stack main → feat-1 → feat-2 → feat-3
    repo_root = Path("/test/repo")
    git_ops = FakeGit(current_branches={repo_root: "feat-2"})

    graphite_ops = FakeGraphite(
        stacks={
            "feat-2": ["main", "feat-1", "feat-2", "feat-3"],
        },
        branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2", "feat-3").build(),
    )

    ctx = ErkContext.for_test(
        cwd=Path("/test"),
        git=git_ops,
        graphite=graphite_ops,
        global_config=GlobalConfig(
            erk_root=Path("/test/erks"),
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        ),
    )

    # Act: Call without down_only flag (default False)
    result = _get_branches_to_land(ctx, repo_root, "feat-2", down_only=False)

    # Assert: Returns entire stack excluding trunk
    assert result == ["feat-1", "feat-2", "feat-3"]


def test_get_branches_to_land_down_only_true() -> None:
    """With down_only=True, returns only trunk to current (downstack)."""
    # Arrange: Set up stack main → feat-1 → feat-2 → feat-3
    repo_root = Path("/test/repo")
    git_ops = FakeGit(current_branches={repo_root: "feat-2"})

    graphite_ops = FakeGraphite(
        stacks={
            "feat-2": ["main", "feat-1", "feat-2", "feat-3"],
        },
        branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2", "feat-3").build(),
    )

    ctx = ErkContext.for_test(
        cwd=Path("/test"),
        git=git_ops,
        graphite=graphite_ops,
        global_config=GlobalConfig(
            erk_root=Path("/test/erks"),
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        ),
    )

    # Act: Call with down_only=True
    result = _get_branches_to_land(ctx, repo_root, "feat-2", down_only=True)

    # Assert: Returns only trunk to current (excludes feat-3)
    assert result == ["feat-1", "feat-2"]


def test_get_branches_to_land_at_leaf_full_stack() -> None:
    """At leaf branch, full stack includes all branches."""
    # Arrange: Current branch is feat-3 (at top/leaf)
    repo_root = Path("/test/repo")
    git_ops = FakeGit(current_branches={repo_root: "feat-3"})

    graphite_ops = FakeGraphite(
        stacks={
            "feat-3": ["main", "feat-1", "feat-2", "feat-3"],
        },
        branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2", "feat-3").build(),
    )

    ctx = ErkContext.for_test(
        cwd=Path("/test"),
        git=git_ops,
        graphite=graphite_ops,
        global_config=GlobalConfig(
            erk_root=Path("/test/erks"),
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        ),
    )

    # Act: Call without down_only flag
    result = _get_branches_to_land(ctx, repo_root, "feat-3", down_only=False)

    # Assert: Returns entire stack
    assert result == ["feat-1", "feat-2", "feat-3"]


def test_get_branches_to_land_at_leaf_down_only() -> None:
    """At leaf branch with down_only=True, same as full stack."""
    # Arrange: Current branch is feat-3 (at top/leaf)
    repo_root = Path("/test/repo")
    git_ops = FakeGit(current_branches={repo_root: "feat-3"})

    graphite_ops = FakeGraphite(
        stacks={
            "feat-3": ["main", "feat-1", "feat-2", "feat-3"],
        },
        branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2", "feat-3").build(),
    )

    ctx = ErkContext.for_test(
        cwd=Path("/test"),
        git=git_ops,
        graphite=graphite_ops,
        global_config=GlobalConfig(
            erk_root=Path("/test/erks"),
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        ),
    )

    # Act: Call with down_only=True
    result = _get_branches_to_land(ctx, repo_root, "feat-3", down_only=True)

    # Assert: Returns entire stack (same as full stack since at leaf)
    assert result == ["feat-1", "feat-2", "feat-3"]


def test_get_branches_to_land_first_branch_full_stack() -> None:
    """At first branch above trunk, full stack includes all branches."""
    # Arrange: Current branch is feat-1 (first above trunk)
    repo_root = Path("/test/repo")
    git_ops = FakeGit(current_branches={repo_root: "feat-1"})

    graphite_ops = FakeGraphite(
        stacks={
            "feat-1": ["main", "feat-1", "feat-2", "feat-3"],
        },
        branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2", "feat-3").build(),
    )

    ctx = ErkContext.for_test(
        cwd=Path("/test"),
        git=git_ops,
        graphite=graphite_ops,
        global_config=GlobalConfig(
            erk_root=Path("/test/erks"),
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        ),
    )

    # Act: Call without down_only flag
    result = _get_branches_to_land(ctx, repo_root, "feat-1", down_only=False)

    # Assert: Returns entire stack
    assert result == ["feat-1", "feat-2", "feat-3"]


def test_get_branches_to_land_first_branch_down_only() -> None:
    """At first branch with down_only=True, returns only that branch."""
    # Arrange: Current branch is feat-1 (first above trunk)
    repo_root = Path("/test/repo")
    git_ops = FakeGit(current_branches={repo_root: "feat-1"})

    graphite_ops = FakeGraphite(
        stacks={
            "feat-1": ["main", "feat-1", "feat-2", "feat-3"],
        },
        branches=BranchStackBuilder().add_linear_stack("feat-1", "feat-2", "feat-3").build(),
    )

    ctx = ErkContext.for_test(
        cwd=Path("/test"),
        git=git_ops,
        graphite=graphite_ops,
        global_config=GlobalConfig(
            erk_root=Path("/test/erks"),
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        ),
    )

    # Act: Call with down_only=True
    result = _get_branches_to_land(ctx, repo_root, "feat-1", down_only=True)

    # Assert: Returns only first branch (no upstack)
    assert result == ["feat-1"]


def test_get_branches_to_land_no_stack() -> None:
    """Returns empty list when branch has no stack."""
    # Arrange: Branch not in any stack
    repo_root = Path("/test/repo")
    git_ops = FakeGit(current_branches={repo_root: "unknown"})

    graphite_ops = FakeGraphite(
        stacks={},  # No stack for unknown branch
        branches=BranchStackBuilder().build(),
    )

    ctx = ErkContext.for_test(
        cwd=Path("/test"),
        git=git_ops,
        graphite=graphite_ops,
        global_config=GlobalConfig(
            erk_root=Path("/test/erks"),
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        ),
    )

    # Act
    result = _get_branches_to_land(ctx, repo_root, "unknown", down_only=False)

    # Assert: Returns empty list
    assert result == []


def test_get_branches_to_land_excludes_trunk() -> None:
    """Trunk branches are excluded from result."""
    # Arrange: Stack with trunk
    repo_root = Path("/test/repo")
    git_ops = FakeGit(current_branches={repo_root: "feat-1"})

    graphite_ops = FakeGraphite(
        stacks={
            "feat-1": ["main", "feat-1"],
        },
        branches=BranchStackBuilder().add_linear_stack("feat-1").build(),
    )

    ctx = ErkContext.for_test(
        cwd=Path("/test"),
        git=git_ops,
        graphite=graphite_ops,
        global_config=GlobalConfig(
            erk_root=Path("/test/erks"),
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        ),
    )

    # Act
    result = _get_branches_to_land(ctx, repo_root, "feat-1", down_only=False)

    # Assert: main (trunk) is excluded
    assert result == ["feat-1"]
    assert "main" not in result
