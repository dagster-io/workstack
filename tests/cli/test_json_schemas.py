"""Tests for Pydantic JSON schema models.

These tests verify that JSON output schemas are properly validated by Pydantic models.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from erk.cli.json_schemas import (
    CreateCommandResponse,
    StatusCommandResponse,
    StatusGitInfo,
    StatusPlanInfo,
    StatusPRInfo,
    StatusRelatedWorktree,
    StatusStackInfo,
    StatusWorktreeInfo,
    create_response_from_dict,
    status_data_to_pydantic,
)
from erk.status.models.status_data import (
    GitStatus,
    PlanStatus,
    PullRequestStatus,
    StackPosition,
    StatusData,
    WorktreeDisplayInfo,
)

# CreateCommandResponse tests


def test_create_command_response_valid() -> None:
    """CreateCommandResponse should validate correct data."""
    response = CreateCommandResponse(
        worktree_name="test-feature",
        worktree_path="/path/to/worktree",
        branch_name="feature-branch",
        plan_file="/path/to/plan.md",
        status="created",
    )

    assert response.worktree_name == "test-feature"
    assert response.status == "created"


def test_create_command_response_invalid_status() -> None:
    """CreateCommandResponse should reject invalid status values."""
    with pytest.raises(ValidationError) as exc_info:
        CreateCommandResponse(
            worktree_name="test",
            worktree_path="/path",
            branch_name="branch",
            plan_file=None,
            status="invalid",
        )

    assert "status" in str(exc_info.value)


def test_create_command_response_with_none_values() -> None:
    """CreateCommandResponse should accept None for optional fields."""
    response = CreateCommandResponse(
        worktree_name="test",
        worktree_path="/path",
        branch_name=None,
        plan_file=None,
        status="exists",
    )

    assert response.branch_name is None
    assert response.plan_file is None


def test_create_response_from_dict() -> None:
    """create_response_from_dict should create valid JSON."""
    json_str = create_response_from_dict(
        worktree_name="my-feature",
        worktree_path=Path("/repo/worktrees/my-feature"),
        branch_name="feature-123",
        plan_file_path=Path("/repo/worktrees/my-feature/.plan/plan.md"),
        status="created",
    )

    assert "my-feature" in json_str
    assert "created" in json_str
    assert "feature-123" in json_str


# StatusCommandResponse tests


def test_status_worktree_info_valid() -> None:
    """StatusWorktreeInfo should validate correct data."""
    info = StatusWorktreeInfo(
        name="test-wt",
        path="/path/to/wt",
        branch="main",
        is_root=True,
    )

    assert info.name == "test-wt"
    assert info.is_root is True


def test_status_stack_info_invalid_position() -> None:
    """StatusStackInfo should reject invalid position values."""
    with pytest.raises(ValidationError) as exc_info:
        StatusStackInfo(
            position="invalid",
            parent=None,
            children=[],
        )

    assert "position" in str(exc_info.value)


def test_status_pr_info_invalid_state() -> None:
    """StatusPRInfo should reject invalid state values."""
    with pytest.raises(ValidationError) as exc_info:
        StatusPRInfo(
            number=123,
            title="Test PR",
            url="https://github.com/test/repo/pull/123",
            state="invalid",
            is_draft=False,
        )

    assert "state" in str(exc_info.value)


def test_status_related_worktree_invalid_relationship() -> None:
    """StatusRelatedWorktree should reject invalid relationship values."""
    with pytest.raises(ValidationError) as exc_info:
        StatusRelatedWorktree(
            name="other-wt",
            path="/path",
            branch="other",
            relationship="invalid",
        )

    assert "relationship" in str(exc_info.value)


def test_status_command_response_minimal() -> None:
    """StatusCommandResponse should accept minimal valid data."""
    response = StatusCommandResponse(
        worktree_info=StatusWorktreeInfo(
            name="test",
            path="/path",
            branch="main",
            is_root=True,
        ),
        plan=None,
        stack=None,
        pr_status=None,
        git_status=StatusGitInfo(
            staged=[],
            unstaged=[],
            untracked=[],
            is_clean=True,
        ),
        related_worktrees=[],
    )

    assert response.worktree_info.name == "test"
    assert response.plan is None
    assert response.git_status.is_clean is True


def test_status_command_response_full() -> None:
    """StatusCommandResponse should accept complete data."""
    response = StatusCommandResponse(
        worktree_info=StatusWorktreeInfo(
            name="feature-wt",
            path="/path/to/wt",
            branch="feature",
            is_root=False,
        ),
        plan=StatusPlanInfo(
            exists=True,
            objective="Implement feature X",
            progress_summary="2/5 tasks completed",
        ),
        stack=StatusStackInfo(
            position="middle",
            parent="main",
            children=["child-feature"],
        ),
        pr_status=StatusPRInfo(
            number=42,
            title="Add feature X",
            url="https://github.com/test/repo/pull/42",
            state="open",
            is_draft=False,
        ),
        git_status=StatusGitInfo(
            staged=["file1.py"],
            unstaged=["file2.py"],
            untracked=["file3.py"],
            is_clean=False,
        ),
        related_worktrees=[
            StatusRelatedWorktree(
                name="parent-wt",
                path="/path/to/parent",
                branch="main",
                relationship="parent",
            )
        ],
    )

    assert response.worktree_info.name == "feature-wt"
    assert response.plan is not None
    assert response.plan.objective == "Implement feature X"
    assert response.stack is not None
    assert response.stack.position == "middle"


# Conversion function tests


def test_status_data_to_pydantic_minimal() -> None:
    """status_data_to_pydantic should convert minimal StatusData."""
    worktree_info = WorktreeDisplayInfo.root(Path("/repo"))
    git_status = GitStatus.clean_status("main")
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

    pydantic_model = status_data_to_pydantic(status_data)

    assert pydantic_model.worktree_info.name == "root"
    assert pydantic_model.git_status.is_clean is True
    assert pydantic_model.plan is None


def test_status_data_to_pydantic_with_stack() -> None:
    """status_data_to_pydantic should convert stack position correctly."""
    worktree_info = WorktreeDisplayInfo.feature(Path("/repo/wt"), "feature")
    git_status = GitStatus.clean_status("feature")
    stack_position = StackPosition(
        stack=["main", "feature", "child"],
        current_branch="feature",
        parent_branch="main",
        children_branches=["child"],
        is_trunk=False,
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

    pydantic_model = status_data_to_pydantic(status_data)

    assert pydantic_model.stack is not None
    assert pydantic_model.stack.position == "middle"
    assert pydantic_model.stack.parent == "main"
    assert pydantic_model.stack.children == ["child"]


def test_status_data_to_pydantic_leaf_position() -> None:
    """status_data_to_pydantic should detect leaf position."""
    worktree_info = WorktreeDisplayInfo.feature(Path("/repo/wt"), "leaf")
    git_status = GitStatus.clean_status("leaf")
    stack_position = StackPosition(
        stack=["main", "leaf"],
        current_branch="leaf",
        parent_branch="main",
        children_branches=[],
        is_trunk=False,
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

    pydantic_model = status_data_to_pydantic(status_data)

    assert pydantic_model.stack is not None
    assert pydantic_model.stack.position == "leaf"


def test_status_data_to_pydantic_trunk_position() -> None:
    """status_data_to_pydantic should detect trunk position."""
    worktree_info = WorktreeDisplayInfo.root(Path("/repo"))
    git_status = GitStatus.clean_status("main")
    stack_position = StackPosition(
        stack=["main"],
        current_branch="main",
        parent_branch=None,
        children_branches=["feature"],
        is_trunk=True,
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

    pydantic_model = status_data_to_pydantic(status_data)

    assert pydantic_model.stack is not None
    assert pydantic_model.stack.position == "trunk"


def test_status_data_to_pydantic_with_plan() -> None:
    """status_data_to_pydantic should convert plan status."""
    worktree_info = WorktreeDisplayInfo.feature(Path("/repo/wt"), "feature")
    git_status = GitStatus.clean_status("feature")
    plan_status = PlanStatus(
        exists=True,
        path=Path("/repo/wt/.plan"),
        summary="Build feature X",
        line_count=50,
        first_lines=["# Plan", "Build X"],
        progress_summary="3/10 steps",
        format="folder",
    )
    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=None,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=plan_status,
        related_worktrees=[],
    )

    pydantic_model = status_data_to_pydantic(status_data)

    assert pydantic_model.plan is not None
    assert pydantic_model.plan.exists is True
    assert pydantic_model.plan.objective == "Build feature X"
    assert pydantic_model.plan.progress_summary == "3/10 steps"


def test_status_data_to_pydantic_with_pr() -> None:
    """status_data_to_pydantic should convert PR status."""
    worktree_info = WorktreeDisplayInfo.feature(Path("/repo/wt"), "feature")
    git_status = GitStatus.clean_status("feature")
    pr_status = PullRequestStatus(
        number=123,
        title="Add feature",
        state="open",
        is_draft=True,
        url="https://github.com/test/repo/pull/123",
        checks_passing=True,
        reviews=["alice"],
        ready_to_merge=False,
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

    pydantic_model = status_data_to_pydantic(status_data)

    assert pydantic_model.pr_status is not None
    assert pydantic_model.pr_status.number == 123
    assert pydantic_model.pr_status.title == "Add feature"
    assert pydantic_model.pr_status.is_draft is True


def test_status_data_to_pydantic_with_related_worktrees() -> None:
    """status_data_to_pydantic should convert related worktrees with relationships."""
    worktree_info = WorktreeDisplayInfo.feature(Path("/repo/wt"), "feature")
    git_status = GitStatus.clean_status("feature")
    stack_position = StackPosition(
        stack=["main", "feature", "child"],
        current_branch="feature",
        parent_branch="main",
        children_branches=["child"],
        is_trunk=False,
    )
    related_worktrees = [
        WorktreeDisplayInfo.root(Path("/repo"), branch="main", name="main-wt"),
        WorktreeDisplayInfo.feature(Path("/repo/child-wt"), "child", name="child-wt"),
    ]
    status_data = StatusData(
        worktree_info=worktree_info,
        git_status=git_status,
        stack_position=stack_position,
        pr_status=None,
        environment=None,
        dependencies=None,
        plan=None,
        related_worktrees=related_worktrees,
    )

    pydantic_model = status_data_to_pydantic(status_data)

    assert len(pydantic_model.related_worktrees) == 2
    # First worktree is parent
    assert pydantic_model.related_worktrees[0].name == "main-wt"
    assert pydantic_model.related_worktrees[0].relationship == "parent"
    # Second worktree is child
    assert pydantic_model.related_worktrees[1].name == "child-wt"
    assert pydantic_model.related_worktrees[1].relationship == "child"


def test_status_data_to_pydantic_invalid_type() -> None:
    """status_data_to_pydantic should reject non-StatusData input."""
    with pytest.raises(TypeError, match="Expected StatusData"):
        status_data_to_pydantic({"invalid": "data"})  # type: ignore[arg-type]
