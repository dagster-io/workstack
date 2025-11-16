"""Pre-flight validation for land-stack command."""

from pathlib import Path

import click

from erk.cli.commands.land_stack.models import BranchPR
from erk.cli.commands.land_stack.output import _emit
from erk.core.context import WorkstackContext


def _validate_landing_preconditions(
    ctx: WorkstackContext,
    repo_root: Path,
    current_branch: str | None,
    branches_to_land: list[str],
    down: bool,
    *,
    script_mode: bool,
) -> None:
    """Validate all preconditions for landing are met.

    Args:
        ctx: WorkstackContext with access to operations
        repo_root: Repository root directory
        current_branch: Current branch name (None if detached HEAD)
        branches_to_land: List of branches to land
        down: True to include --down flag in error suggestions
        script_mode: True when running in --script mode (output to stderr)

    Raises:
        SystemExit: If any precondition fails
    """
    # Check Graphite enabled
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
    if not use_graphite:
        _emit(
            "Error: 'workstack land-stack' requires Graphite.\n\n"
            "To fix:\n"
            "  • Run: workstack config set use-graphite true\n"
            "  • Install Graphite CLI if needed: brew install withgraphite/tap/graphite",
            script_mode=script_mode,
            error=True,
        )
        raise SystemExit(1)

    # Check not detached HEAD
    if current_branch is None:
        _emit(
            "Error: HEAD is detached (not on a branch)\n\n"
            "To fix:\n"
            "  • Check out a branch: git checkout <branch-name>",
            script_mode=script_mode,
            error=True,
        )
        raise SystemExit(1)

    # Check no uncommitted changes in current worktree
    if ctx.git_ops.has_uncommitted_changes(ctx.cwd):
        _emit(
            f"Error: Current worktree has uncommitted changes\n"
            f"Path: {ctx.cwd}\n"
            f"Branch: {current_branch}\n\n"
            "Landing requires a clean working directory.\n\n"
            "To fix:\n"
            "  • Commit your changes: git add . && git commit -m 'message'\n"
            "  • Stash your changes: git stash\n"
            "  • Discard your changes: git reset --hard HEAD",
            script_mode=script_mode,
            error=True,
        )
        raise SystemExit(1)

    # Check current branch not trunk
    all_branches = ctx.graphite_ops.get_all_branches(ctx.git_ops, repo_root)
    if current_branch in all_branches and all_branches[current_branch].is_trunk:
        _emit(
            f"Error: Cannot land trunk branch '{current_branch}'\n"
            "Trunk branches (main/master) cannot be landed.\n\n"
            "To fix:\n"
            "  • Check out a feature branch: git checkout <feature-branch>",
            script_mode=script_mode,
            error=True,
        )
        raise SystemExit(1)

    # Validate stack exists
    if not branches_to_land:
        stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, current_branch)
        if stack is None:
            _emit(
                f"Error: Branch '{current_branch}' is not tracked by Graphite\n\n"
                "To fix:\n"
                "  • Track the branch with Graphite: gt create -s\n"
                "  • Or switch to a Graphite-tracked branch",
                script_mode=script_mode,
                error=True,
            )
        else:
            _emit(
                f"Error: No branches to land\n"
                f"Branch '{current_branch}' may already be landed or is a trunk branch.",
                script_mode=script_mode,
                error=True,
            )
        raise SystemExit(1)

    # Check no branches in stack are checked out in other worktrees
    current_worktree = ctx.cwd.resolve()
    worktree_conflicts: list[tuple[str, Path]] = []

    for branch in branches_to_land:
        worktree_path = ctx.git_ops.is_branch_checked_out(repo_root, branch)
        if worktree_path and worktree_path.resolve() != current_worktree:
            worktree_conflicts.append((branch, worktree_path))

    if worktree_conflicts:
        _emit(
            "Error: Cannot land stack - branches are checked out in multiple worktrees\n\n"
            "The following branches are checked out in other worktrees:",
            script_mode=script_mode,
            error=True,
        )
        for branch, path in worktree_conflicts:
            branch_styled = click.style(branch, fg="yellow")
            path_styled = click.style(str(path), fg="white", dim=True)
            _emit(f"  • {branch_styled} → {path_styled}", script_mode=script_mode, error=True)

        _emit(
            "\nGit does not allow checking out a branch that is already checked out\n"
            "in another worktree. To land this stack, you need to consolidate all\n"
            "branches into the current worktree first.\n\n"
            "To fix:\n"
            f"  • Run: workstack consolidate{' --down' if down else ''}\n"
            "  • This will remove other worktrees for branches in this stack\n"
            f"  • Then retry: workstack land-stack{' --down' if down else ''}",
            script_mode=script_mode,
            error=True,
        )
        raise SystemExit(1)


def _validate_branches_have_prs(
    ctx: WorkstackContext, repo_root: Path, branches: list[str], *, script_mode: bool
) -> list[BranchPR]:
    """Validate all branches have open PRs.

    Args:
        ctx: WorkstackContext with access to GitHub operations
        repo_root: Repository root directory
        branches: List of branch names to validate
        script_mode: True when running in --script mode (output to stderr)

    Returns:
        List of BranchPR for all valid branches

    Raises:
        SystemExit: If any branch has invalid PR state
    """
    errors: list[str] = []
    valid_branches: list[BranchPR] = []

    for branch in branches:
        pr_info = ctx.github_ops.get_pr_status(repo_root, branch, debug=False)

        if pr_info.state == "NONE":
            errors.append(f"No PR found for branch '{branch}'")
        elif pr_info.state == "MERGED":
            errors.append(f"PR #{pr_info.pr_number} for '{branch}' is already merged")
        elif pr_info.state == "CLOSED":
            errors.append(f"PR #{pr_info.pr_number} for '{branch}' is closed")
        elif (
            pr_info.state == "OPEN" and pr_info.pr_number is not None and pr_info.title is not None
        ):
            valid_branches.append(BranchPR(branch, pr_info.pr_number, pr_info.title))
        else:
            errors.append(f"Unexpected PR state for '{branch}': {pr_info.state}")

    if errors:
        _emit(
            "Error: Cannot land stack\n\nThe following branches have issues:",
            script_mode=script_mode,
            error=True,
        )
        for error in errors:
            _emit(f"  • {error}", script_mode=script_mode, error=True)
        raise SystemExit(1)

    return valid_branches


def _validate_pr_mergeability(
    ctx: WorkstackContext,
    repo_root: Path,
    branches: list[BranchPR],
    *,
    script_mode: bool,
) -> None:
    """Validate all PRs are mergeable (no conflicts)."""
    conflicts: list[tuple[str, int]] = []

    for branch_pr in branches:
        mergeability = ctx.github_ops.get_pr_mergeability(repo_root, branch_pr.pr_number)

        if mergeability is None:
            # API error - log warning but don't fail
            continue

        if mergeability.mergeable == "CONFLICTING":
            conflicts.append((branch_pr.branch, branch_pr.pr_number))
        elif mergeability.mergeable == "UNKNOWN":
            # GitHub hasn't computed yet - log warning but don't fail
            _emit(
                f"⚠️  Warning: PR #{branch_pr.pr_number} mergeability unknown",
                script_mode=script_mode,
                error=False,
            )

    if conflicts:
        # Show error with all conflicts and resolution steps
        _emit(
            "Error: Cannot land stack - PRs have merge conflicts\n",
            script_mode=script_mode,
            error=True,
        )
        for branch, pr_num in conflicts:
            _emit(
                f"  • PR #{pr_num} ({branch}): has conflicts with main",
                script_mode=script_mode,
                error=True,
            )
        _emit("\nTo fix:", script_mode=script_mode, error=True)
        _emit("  1. Fetch latest: git fetch origin main", script_mode=script_mode, error=True)
        _emit("  2. Rebase stack: gt stack rebase", script_mode=script_mode, error=True)
        raise SystemExit(1)
