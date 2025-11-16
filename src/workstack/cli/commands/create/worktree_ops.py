"""Git worktree operations for the create command.

This module contains the core git worktree operations used by variant handlers.
These operations are isolated here to enable testing and reuse across variants.
"""

import shutil
from pathlib import Path

from workstack.cli.output import user_output
from workstack.cli.subprocess_utils import run_with_error_reporting
from workstack.core.context import WorkstackContext


def add_worktree(
    ctx: WorkstackContext,
    repo_root: Path,
    path: Path,
    *,
    branch: str | None,
    ref: str | None,
    use_existing_branch: bool,
    use_graphite: bool,
) -> None:
    """Create a git worktree.

    This function handles three distinct modes:
    1. use_existing_branch=True: Check out an existing branch in new worktree
    2. use_graphite=True: Create new branch via Graphite (gt create)
    3. Otherwise: Create new branch via standard git

    Args:
        ctx: Workstack context
        repo_root: Repository root path
        path: Path where worktree should be created
        branch: Branch name to create or check out
        ref: Git ref to base new branch on (ignored if use_existing_branch)
        use_existing_branch: Whether branch already exists
        use_graphite: Whether to create branch via Graphite

    Raises:
        SystemExit: If branch is already checked out elsewhere
        SystemExit: If Graphite has staged changes
        ValueError: If attempting Graphite operation from detached HEAD
    """
    if branch and use_existing_branch:
        # Validate branch is not already checked out
        existing_path = ctx.git_ops.is_branch_checked_out(repo_root, branch)
        if existing_path:
            user_output(
                f"Error: Branch '{branch}' is already checked out at {existing_path}\n"
                f"Git doesn't allow the same branch to be checked out in multiple worktrees.\n\n"
                f"Options:\n"
                f"  • Use a different branch name\n"
                f"  • Create a new branch instead: workstack create {path.name}\n"
                f"  • Switch to that worktree: workstack switch {path.name}",
            )
            raise SystemExit(1)

        ctx.git_ops.add_worktree(repo_root, path, branch=branch, ref=None, create_branch=False)
    elif branch:
        if use_graphite:
            cwd = ctx.cwd
            original_branch = ctx.git_ops.get_current_branch(cwd)
            if original_branch is None:
                raise ValueError("Cannot create graphite branch from detached HEAD")
            if ctx.git_ops.has_staged_changes(repo_root):
                user_output(
                    "Error: Staged changes detected. "
                    "Graphite cannot create a branch while staged changes are present.\n"
                    "`gt create --no-interactive` attempts to commit staged files but fails when "
                    "no commit message is provided.\n\n"
                    "Resolve the staged changes before running `workstack create`:\n"
                    '  • Commit them: git commit -m "message"\n'
                    "  • Unstage them: git reset\n"
                    "  • Stash them: git stash\n"
                    "  • Disable Graphite: workstack config set use_graphite false",
                )
                raise SystemExit(1)
            run_with_error_reporting(
                ["gt", "create", "--no-interactive", branch],
                cwd=cwd,
                error_prefix=f"Failed to create Graphite branch '{branch}'",
                troubleshooting=[
                    "Check if branch name is valid",
                    "Ensure Graphite is properly configured (gt repo init)",
                    f"Try creating the branch manually: gt create {branch}",
                    "Disable Graphite: workstack config set use_graphite false",
                ],
            )
            ctx.git_ops.checkout_branch(cwd, original_branch)
            ctx.git_ops.add_worktree(repo_root, path, branch=branch, ref=None, create_branch=False)
        else:
            ctx.git_ops.add_worktree(repo_root, path, branch=branch, ref=ref, create_branch=True)
    else:
        ctx.git_ops.add_worktree(repo_root, path, branch=None, ref=ref, create_branch=False)


def copy_plan_folder(source_wt: Path, target_wt: Path) -> None:
    """Copy .plan/ directory from source worktree to target worktree.

    Preserves both plan.md and progress.md files using shutil.copytree
    to maintain directory structure and metadata.

    Args:
        source_wt: Source worktree path containing .plan/ directory
        target_wt: Target worktree path where .plan/ should be copied

    Raises:
        ValueError: If source .plan/ directory does not exist (programming error)
    """
    source_plan_dir = source_wt / ".plan"
    target_plan_dir = target_wt / ".plan"

    if not source_plan_dir.exists():
        raise ValueError(
            f"Source .plan/ directory does not exist at {source_plan_dir}. "
            "This should have been validated before calling copy_plan_folder()."
        )

    # Use shutil.copytree to preserve structure and metadata
    shutil.copytree(source_plan_dir, target_plan_dir)
