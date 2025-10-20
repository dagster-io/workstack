"""Comprehensive unit tests for SimpleRenderer."""

from pathlib import Path

import click
from click.testing import CliRunner

from workstack.status.models.status_data import (
    CommitInfo,
    GitStatus,
    PlanStatus,
    PullRequestStatus,
    StackPosition,
    StatusData,
    WorktreeInfo,
)
from workstack.status.renderers.simple import SimpleRenderer


def capture_renderer_output(renderer: SimpleRenderer, status_data: StatusData) -> str:
    """Helper to capture renderer output.

    Args:
        renderer: The renderer to test
        status_data: The status data to render

    Returns:
        The captured output as a string
    """
    runner = CliRunner()

    @click.command()
    def test_cmd() -> None:
        renderer.render(status_data)

    result = runner.invoke(test_cmd)
    return result.output


def test_renderer_clean_working_tree() -> None:
    """Test rendering with clean working tree."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="main",
        is_root=False,
    )

    git_status = GitStatus(
        branch="main",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Worktree: test-worktree" in output
    assert "Location: /tmp/test" in output
    assert "Branch:   main" in output
    assert "Working tree clean" in output


def test_renderer_dirty_working_tree() -> None:
    """Test rendering with dirty working tree."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    git_status = GitStatus(
        branch="feature",
        clean=False,
        ahead=2,
        behind=1,
        staged_files=["file1.py", "file2.py"],
        modified_files=["file3.py", "file4.py", "file5.py"],
        untracked_files=["file6.py", "file7.py", "file8.py", "file9.py", "file10.py"],
        recent_commits=[
            CommitInfo(
                sha="abc123",
                message="Add new feature",
                author="Test Author",
                date="2 hours ago",
            ),
            CommitInfo(
                sha="def456",
                message="Fix bug in previous commit that was really long and needs truncation",
                author="Test Author",
                date="3 hours ago",
            ),
        ],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Working tree has changes:" in output
    assert "Staged:" in output
    assert "file1.py" in output
    assert "Modified:" in output
    assert "file3.py" in output
    assert "Untracked:" in output
    assert "file6.py" in output
    assert "... and 2 more" in output  # Untracked files truncated
    assert "2 ahead" in output
    assert "1 behind" in output
    assert "Recent commits:" in output
    assert "abc123" in output
    assert "Add new feature" in output
    assert "..." in output  # Long message truncated


def test_renderer_with_plan_file() -> None:
    """Test rendering with plan file."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    plan = PlanStatus(
        exists=True,
        path=Path("/tmp/test/.PLAN.md"),
        summary="Test plan summary",
        line_count=42,
        first_lines=[
            "# Test Plan",
            "",
            "## Overview",
            "",
            "This is a test plan.",
        ],
    )

    git_status = GitStatus(
        branch="feature",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=plan,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Plan:" in output
    assert "# Test Plan" in output
    assert "## Overview" in output
    assert "This is a test plan." in output
    assert "(42 lines in .PLAN.md)" in output


def test_renderer_without_plan_file() -> None:
    """Test rendering when plan file doesn't exist."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    # Plan exists but file not found
    plan = PlanStatus(
        exists=False,
        path=Path("/tmp/test/.PLAN.md"),
        summary=None,
        line_count=0,
        first_lines=[],
    )

    git_status = GitStatus(
        branch="feature",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=plan,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert - plan section not rendered
    assert "Plan:" not in output


def test_renderer_with_stack_position() -> None:
    """Test rendering with Graphite stack position."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature-2",
        is_root=False,
    )

    stack_position = StackPosition(
        stack=["main", "feature-1", "feature-2", "feature-3"],
        current_branch="feature-2",
        parent_branch="feature-1",
        children_branches=["feature-3"],
        is_trunk=False,
    )

    git_status = GitStatus(
        branch="feature-2",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=stack_position,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Stack Position:" in output
    assert "Parent: feature-1" in output
    assert "Children: feature-3" in output
    assert "Stack:" in output
    assert "◉  feature-2" in output  # Current branch
    assert "◯  feature-1" in output  # Other branches
    assert "◯  main" in output


def test_renderer_trunk_branch() -> None:
    """Test rendering when on trunk branch."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="main",
        is_root=True,
    )

    stack_position = StackPosition(
        stack=["main"],
        current_branch="main",
        parent_branch=None,
        children_branches=[],
        is_trunk=True,
    )

    git_status = GitStatus(
        branch="main",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=stack_position,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Stack Position:" in output
    assert "This is a trunk branch" in output
    assert "Parent:" not in output  # No parent for trunk
    assert "Children:" not in output  # No children shown


def test_renderer_with_pr_status() -> None:
    """Test rendering with pull request status."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    pr_status = PullRequestStatus(
        number=123,
        state="OPEN",
        title="Add new feature",
        url="https://github.com/owner/repo/pull/123",
        is_draft=False,
        checks_passing=True,
        reviews=None,
        ready_to_merge=True,
    )

    git_status = GitStatus(
        branch="feature",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=pr_status,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Pull Request:" in output
    assert "#123" in output
    assert "OPEN" in output
    assert "Checks: passing" in output
    assert "✓ Ready to merge" in output
    assert "https://github.com/owner/repo/pull/123" in output


def test_renderer_draft_pr() -> None:
    """Test rendering with draft PR."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    pr_status = PullRequestStatus(
        number=456,
        state="OPEN",
        title="WIP: Add new feature",
        url="https://github.com/owner/repo/pull/456",
        is_draft=True,
        checks_passing=False,
        reviews=None,
        ready_to_merge=False,
    )

    git_status = GitStatus(
        branch="feature",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=pr_status,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Pull Request:" in output
    assert "#456" in output
    assert "OPEN" in output
    assert "Draft PR" in output
    assert "Checks: failing" in output
    assert "Ready to merge" not in output  # Not ready


def test_renderer_closed_pr() -> None:
    """Test rendering with closed PR."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    pr_status = PullRequestStatus(
        number=789,
        state="CLOSED",
        title="Old feature",
        url="https://github.com/owner/repo/pull/789",
        is_draft=False,
        checks_passing=None,  # No checks for closed PR
        reviews=None,
        ready_to_merge=False,
    )

    git_status = GitStatus(
        branch="feature",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=pr_status,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Pull Request:" in output
    assert "#789" in output
    assert "CLOSED" in output
    assert "Checks:" not in output  # No checks section


def test_renderer_merged_pr() -> None:
    """Test rendering with merged PR."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    pr_status = PullRequestStatus(
        number=999,
        state="MERGED",
        title="Completed feature",
        url="https://github.com/owner/repo/pull/999",
        is_draft=False,
        checks_passing=True,
        reviews=None,
        ready_to_merge=False,  # Already merged
    )

    git_status = GitStatus(
        branch="feature",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=pr_status,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Pull Request:" in output
    assert "#999" in output
    assert "MERGED" in output


def test_renderer_related_worktrees() -> None:
    """Test rendering with related worktrees."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    related_worktrees = [
        WorktreeInfo(
            name="root",
            path=Path("/tmp/repo"),
            branch="main",
            is_root=True,
        ),
        WorktreeInfo(
            name="feature-1",
            path=Path("/tmp/feature-1"),
            branch="feature-1",
            is_root=False,
        ),
        WorktreeInfo(
            name="feature-2",
            path=Path("/tmp/feature-2"),
            branch="feature-2",
            is_root=False,
        ),
    ]

    git_status = GitStatus(
        branch="feature",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=related_worktrees,
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Related Worktrees:" in output
    # Note: Colors are stripped in test output
    assert "root" in output
    assert "[main]" in output
    assert "feature-1" in output
    assert "[feature-1]" in output


def test_renderer_many_related_worktrees() -> None:
    """Test rendering with many related worktrees (truncation)."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    # Create many related worktrees
    related_worktrees = []
    for i in range(10):
        related_worktrees.append(
            WorktreeInfo(
                name=f"feature-{i}",
                path=Path(f"/tmp/feature-{i}"),
                branch=f"feature-{i}",
                is_root=False,
            )
        )

    git_status = GitStatus(
        branch="feature",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=related_worktrees,
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Related Worktrees:" in output
    assert "feature-0" in output
    assert "feature-4" in output  # Shows first 5
    assert "feature-5" not in output  # Truncated
    assert "... and 5 more" in output


def test_renderer_detached_head() -> None:
    """Test rendering with detached HEAD."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch=None,  # Detached HEAD
        is_root=False,
    )

    git_status = GitStatus(
        branch=None,
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert
    assert "Worktree: test-worktree" in output
    assert "(detached HEAD)" in output


def test_renderer_root_worktree() -> None:
    """Test rendering with root worktree."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="root",
        path=Path("/tmp/repo"),
        branch="main",
        is_root=True,  # Root worktree
    )

    git_status = GitStatus(
        branch="main",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert - root worktree shown
    assert "Worktree: root" in output


def test_renderer_many_recent_commits() -> None:
    """Test rendering with many recent commits (truncation)."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    # Create many commits
    commits = []
    for i in range(10):
        commits.append(
            CommitInfo(
                sha=f"sha{i:03d}",
                message=f"Commit message {i}",
                author="Test Author",
                date=f"{i} hours ago",
            )
        )

    git_status = GitStatus(
        branch="feature",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=commits,
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert - only first 3 commits shown
    assert "Recent commits:" in output
    assert "sha000" in output
    assert "sha001" in output
    assert "sha002" in output
    assert "sha003" not in output  # Only shows first 3


def test_renderer_full_status() -> None:
    """Test rendering with all status components."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature-2",
        is_root=False,
    )

    git_status = GitStatus(
        branch="feature-2",
        clean=False,
        ahead=1,
        behind=2,
        staged_files=["file1.py"],
        modified_files=["file2.py"],
        untracked_files=["file3.py"],
        recent_commits=[
            CommitInfo(
                sha="abc123",
                message="Recent change",
                author="Test Author",
                date="1 hour ago",
            )
        ],
    )

    stack_position = StackPosition(
        stack=["main", "feature-1", "feature-2"],
        current_branch="feature-2",
        parent_branch="feature-1",
        children_branches=[],
        is_trunk=False,
    )

    pr_status = PullRequestStatus(
        number=42,
        state="OPEN",
        title="Add feature 2",
        url="https://github.com/owner/repo/pull/42",
        is_draft=False,
        checks_passing=True,
        reviews=None,
        ready_to_merge=False,
    )

    plan = PlanStatus(
        exists=True,
        path=Path("/tmp/test/.PLAN.md"),
        summary="Implementation plan",
        line_count=20,
        first_lines=["# Implementation Plan"],
    )

    related_worktrees = [
        WorktreeInfo(
            name="root",
            path=Path("/tmp/repo"),
            branch="main",
            is_root=True,
        ),
    ]

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=stack_position,
        pr_status=pr_status,
        environment=None,
        dependencies=None,
        plan=plan,
        related_worktrees=related_worktrees,
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert - all sections are present
    assert "Worktree: test-worktree" in output
    assert "Plan:" in output
    assert "Stack Position:" in output
    assert "Pull Request:" in output
    assert "Git Status:" in output
    assert "Related Worktrees:" in output


def test_renderer_no_git_status() -> None:
    """Test rendering when git status is None."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=None,  # No git status
        stack_position=None,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert - Git Status section should not appear
    assert "Git Status:" not in output
    assert "Worktree:" in output  # But header should


def test_renderer_no_stack_position() -> None:
    """Test rendering when stack position is None."""
    # Arrange
    worktree_info = WorktreeInfo(
        name="test-worktree",
        path=Path("/tmp/test"),
        branch="feature",
        is_root=False,
    )

    git_status = GitStatus(
        branch="feature",
        clean=True,
        ahead=0,
        behind=0,
        staged_files=[],
        modified_files=[],
        untracked_files=[],
        recent_commits=[],
    )

    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,  # No stack position
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=[],
    )

    renderer = SimpleRenderer()

    # Act
    output = capture_renderer_output(renderer, status_data)

    # Assert - Stack Position section should not appear
    assert "Stack Position:" not in output
    assert "Git Status:" in output  # But git status should


def test_renderer_file_list_method() -> None:
    """Test _render_file_list method directly."""
    # Arrange
    renderer = SimpleRenderer()
    runner = CliRunner()

    @click.command()
    def test_cmd() -> None:
        # Test empty list
        renderer._render_file_list([], max_files=3)
        # Test single file
        renderer._render_file_list(["single.py"], max_files=3)
        # Test truncation
        renderer._render_file_list(["f1.py", "f2.py", "f3.py", "f4.py"], max_files=3)

    # Act
    result = runner.invoke(test_cmd)

    # Assert
    assert result.exit_code == 0
    assert "single.py" in result.output
    assert "f1.py" in result.output
    assert "... and 1 more" in result.output
