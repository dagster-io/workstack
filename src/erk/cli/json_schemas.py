"""Pydantic models for JSON output schemas.

This module defines the validated JSON schemas for CLI commands that support
--json or --format json output. These models ensure type safety and provide
runtime validation of JSON output structures.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from erk.status.models.status_data import StatusData


class CreateCommandResponse(BaseModel):
    """JSON response schema for the `erk create` command.

    Attributes:
        worktree_name: Name of the worktree
        worktree_path: Absolute path to the worktree directory
        branch_name: Git branch name (None if not available)
        plan_file: Path to plan file if exists (None otherwise)
        status: Status of the operation ("created" or "exists")
    """

    model_config = ConfigDict(strict=True)

    worktree_name: str
    worktree_path: str
    branch_name: str | None
    plan_file: str | None
    status: str = Field(..., pattern="^(created|exists)$")


class CurrentCommandResponse(BaseModel):
    """JSON response schema for the `erk current` command.

    Attributes:
        name: Name of the worktree (or "root" if in root worktree)
        path: Absolute path to the worktree directory
        is_root: Whether this is the root worktree
    """

    model_config = ConfigDict(strict=True)

    name: str
    path: str
    is_root: bool


class GlobalConfigInfo(BaseModel):
    """Global configuration information for `erk config list --json`.

    This represents the global configuration from ~/.erk/config.toml.
    Note: The `shell_setup_complete` field is intentionally excluded as it
    is internal state not shown to users.

    Attributes:
        erk_root: Path to the erk root directory
        use_graphite: Whether Graphite integration is enabled
        show_pr_info: Whether to show PR information in status output
        exists: Whether the global config file exists
    """

    model_config = ConfigDict(strict=True)

    erk_root: str
    use_graphite: bool
    show_pr_info: bool
    exists: bool


class RepositoryConfigInfo(BaseModel):
    """Repository configuration information for `erk config list --json`.

    This represents the repository-level configuration merged from
    pyproject.toml and .erk/config.toml.

    Attributes:
        trunk_branch: Trunk branch name (main/master) or None if not configured
        env: Environment variables dict (may be empty)
        post_create_shell: Shell to use for post-create commands or None
        post_create_commands: List of commands to run after worktree creation (may be empty)
    """

    model_config = ConfigDict(strict=True)

    trunk_branch: str | None
    env: dict[str, str]
    post_create_shell: str | None
    post_create_commands: list[str]


class ConfigListResponse(BaseModel):
    """JSON response schema for the `erk config list --json` command.

    This is the top-level container for configuration information.

    Attributes:
        global_config: Global configuration (None if ~/.erk/config.toml doesn't exist)
        repository_config: Repository configuration (None if not in a repository)
    """

    model_config = ConfigDict(strict=True)

    global_config: GlobalConfigInfo | None
    repository_config: RepositoryConfigInfo | None


class StatusWorktreeInfo(BaseModel):
    """Worktree information in status command output.

    Attributes:
        name: Worktree name
        path: Absolute path to worktree
        branch: Current branch name (None if detached HEAD)
        is_root: Whether this is the root worktree
    """

    model_config = ConfigDict(strict=True)

    name: str
    path: str
    branch: str | None
    is_root: bool


class StatusPlanInfo(BaseModel):
    """Plan information in status command output.

    Attributes:
        exists: Whether a .plan/ folder exists
        objective: Plan objective/summary (None if no plan)
        progress_summary: Progress information like "3/10 steps completed" (None if no plan)
    """

    model_config = ConfigDict(strict=True)

    exists: bool
    objective: str | None
    progress_summary: str | None


class StatusStackInfo(BaseModel):
    """Graphite stack position information in status command output.

    Attributes:
        position: Stack position ("leaf", "middle", or "trunk")
        parent: Parent branch name (None if at trunk)
        children: List of child branch names
    """

    model_config = ConfigDict(strict=True)

    position: str = Field(..., pattern="^(leaf|middle|trunk)$")
    parent: str | None
    children: list[str]


class StatusPRInfo(BaseModel):
    """Pull request information in status command output.

    Attributes:
        number: GitHub PR number
        title: PR title
        url: Full URL to PR
        state: PR state ("open", "merged", or "closed")
        is_draft: Whether PR is a draft
    """

    model_config = ConfigDict(strict=True)

    number: int
    title: str
    url: str
    state: str = Field(..., pattern="^(open|merged|closed)$")
    is_draft: bool


class StatusGitInfo(BaseModel):
    """Git status information in status command output.

    Attributes:
        staged: List of staged file paths
        unstaged: List of modified but unstaged file paths
        untracked: List of untracked file paths
        is_clean: Whether working tree is clean (no changes)
    """

    model_config = ConfigDict(strict=True)

    staged: list[str]
    unstaged: list[str]
    untracked: list[str]
    is_clean: bool


class StatusRelatedWorktree(BaseModel):
    """Related worktree information in status command output.

    Attributes:
        name: Worktree name
        path: Absolute path to worktree
        branch: Branch name
        relationship: Relationship to current worktree ("parent", "child", or "sibling")
    """

    model_config = ConfigDict(strict=True)

    name: str
    path: str
    branch: str
    relationship: str = Field(..., pattern="^(parent|child|sibling)$")


class StatusCommandResponse(BaseModel):
    """JSON response schema for the `erk status --format json` command.

    This is the top-level container for all status information.

    Attributes:
        worktree_info: Information about the current worktree
        plan: Plan folder status (None if no plan data)
        stack: Graphite stack position (None if not in a stack)
        pr_status: Pull request status (None if no PR)
        git_status: Git working tree status
        related_worktrees: List of related worktrees (empty if none)
    """

    model_config = ConfigDict(strict=True)

    worktree_info: StatusWorktreeInfo
    plan: StatusPlanInfo | None
    stack: StatusStackInfo | None
    pr_status: StatusPRInfo | None
    git_status: StatusGitInfo
    related_worktrees: list[StatusRelatedWorktree]


def create_response_from_dict(
    *,
    worktree_name: str,
    worktree_path: Path,
    branch_name: str | None,
    plan_file_path: Path | None,
    status: str,
) -> str:
    """Create validated JSON response for create command.

    Args:
        worktree_name: Name of the worktree
        worktree_path: Path to the worktree directory
        branch_name: Git branch name (may be None if not available)
        plan_file_path: Path to plan file if exists, None otherwise
        status: Status string ("created" or "exists")

    Returns:
        JSON string with worktree information, validated by Pydantic model

    Raises:
        ValueError: If status is not "created" or "exists"
    """
    response = CreateCommandResponse(
        worktree_name=worktree_name,
        worktree_path=str(worktree_path),
        branch_name=branch_name,
        plan_file=str(plan_file_path) if plan_file_path else None,
        status=status,
    )
    return response.model_dump_json()


def status_data_to_pydantic(status_data: "StatusData") -> StatusCommandResponse:
    """Convert StatusData dataclass to Pydantic model for validation.

    Args:
        status_data: StatusData object from status collectors

    Returns:
        StatusCommandResponse Pydantic model with validated structure
    """
    from erk.status.models.status_data import StatusData

    if not isinstance(status_data, StatusData):
        msg = f"Expected StatusData, got {type(status_data)}"
        raise TypeError(msg)

    # Convert worktree_info
    worktree_info = StatusWorktreeInfo(
        name=status_data.worktree_info.name,
        path=str(status_data.worktree_info.path),
        branch=status_data.worktree_info.branch,
        is_root=status_data.worktree_info.is_root,
    )

    # Convert plan
    plan: StatusPlanInfo | None = None
    if status_data.plan:
        plan = StatusPlanInfo(
            exists=status_data.plan.exists,
            objective=status_data.plan.summary,
            progress_summary=status_data.plan.progress_summary,
        )

    # Convert stack_position
    stack: StatusStackInfo | None = None
    if status_data.stack_position:
        stack = StatusStackInfo(
            position="trunk"
            if status_data.stack_position.is_trunk
            else ("leaf" if not status_data.stack_position.children_branches else "middle"),
            parent=status_data.stack_position.parent_branch,
            children=status_data.stack_position.children_branches,
        )

    # Convert pr_status
    pr_status: StatusPRInfo | None = None
    if status_data.pr_status:
        pr_status = StatusPRInfo(
            number=status_data.pr_status.number,
            title=status_data.pr_status.title or "",
            url=status_data.pr_status.url,
            state=status_data.pr_status.state,
            is_draft=status_data.pr_status.is_draft,
        )

    # Convert git_status
    git_status = StatusGitInfo(
        staged=status_data.git_status.staged_files if status_data.git_status else [],
        unstaged=status_data.git_status.modified_files if status_data.git_status else [],
        untracked=status_data.git_status.untracked_files if status_data.git_status else [],
        is_clean=status_data.git_status.clean if status_data.git_status else True,
    )

    # Convert related_worktrees
    related_worktrees: list[StatusRelatedWorktree] = []
    for wt in status_data.related_worktrees:
        # Determine relationship based on stack position
        relationship = "sibling"  # Default, will be refined if we have stack info
        if stack and wt.branch:
            if stack.parent and wt.branch == stack.parent:
                relationship = "parent"
            elif wt.branch in stack.children:
                relationship = "child"

        related_worktrees.append(
            StatusRelatedWorktree(
                name=wt.name,
                path=str(wt.path),
                branch=wt.branch or "",
                relationship=relationship,
            )
        )

    return StatusCommandResponse(
        worktree_info=worktree_info,
        plan=plan,
        stack=stack,
        pr_status=pr_status,
        git_status=git_status,
        related_worktrees=related_worktrees,
    )
