"""Jump command - find and switch to a worktree by branch name."""

import shlex
from pathlib import Path

import click

from workstack.cli.activation import render_activation_script
from workstack.cli.core import discover_repo_context
from workstack.cli.graphite import find_worktrees_containing_branch
from workstack.cli.shell_utils import write_script_to_temp
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo


def _format_worktree_info(wt: WorktreeInfo, repo_root: Path) -> str:
    """Format worktree information for display.

    Args:
        wt: WorktreeInfo to format
        repo_root: Path to repository root (used to identify root worktree)

    Returns:
        Formatted string like "root (currently on 'main')" or "wt-name (currently on 'feature')"
    """
    current = wt.branch or "(detached HEAD)"
    if wt.path == repo_root:
        return f"  - root (currently on '{current}')"
    else:
        # Get worktree name from path
        wt_name = wt.path.name
        return f"  - {wt_name} (currently on '{current}')"


def _perform_jump(
    ctx: WorkstackContext,
    repo_root: Path,
    target_worktree: WorktreeInfo,
    branch: str,
    script: bool,
) -> None:
    """Perform the actual jump to a worktree.

    Args:
        ctx: Workstack context
        repo_root: Repository root path
        target_worktree: The worktree to jump to
        branch: Target branch name
        script: Whether to output only the activation script
    """
    target_path = target_worktree.path
    current_branch_in_worktree = target_worktree.branch

    # Defensive check: verify path exists before any operations
    if not target_path.exists():
        click.echo(
            f"Error: Worktree path does not exist: {target_path}",
            err=True,
        )
        raise SystemExit(1)

    # Check if we're already on the target branch in the target worktree
    current_cwd = Path.cwd()
    if current_cwd == target_path and current_branch_in_worktree == branch:
        # Already in the right place - activation script will show the message
        return

    # Check if branch is already checked out in the worktree
    need_checkout = current_branch_in_worktree != branch

    # If we need to checkout, do it before generating the activation script
    if need_checkout:
        # Checkout the branch in the target worktree
        ctx.git_ops.checkout_branch(target_path, branch)

        # Show stack context
        if not script:
            stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, branch)
            if stack:
                click.echo(f"Stack: {' -> '.join(stack)}")
            click.echo(f"Checked out '{branch}' in worktree")

    # Generate activation script
    if script:
        # Script mode: always generate script (for shell integration or manual sourcing)
        # Use shlex.quote() for branch name security (defense-in-depth)
        safe_branch = shlex.quote(branch)
        if need_checkout:
            jump_message = f'echo "Jumped to branch {safe_branch}: $(pwd)"'
        else:
            jump_message = f'echo "Already on branch {safe_branch}: $(pwd)"'
        script_content = render_activation_script(
            worktree_path=target_path, final_message=jump_message
        )

        script_path = write_script_to_temp(
            script_content,
            command_name="jump",
            comment=f"jump to {branch}",
        )
        click.echo(str(script_path), nl=False)
    else:
        # No shell integration available, show manual instructions
        click.echo(
            "Shell integration not detected. "
            "Run 'workstack init --shell' to set up automatic activation."
        )
        click.echo(f"\nOr use: source <(workstack jump {branch} --script)")


@click.command("jump")
@click.argument("branch", metavar="BRANCH")
@click.option(
    "--script", is_flag=True, help="Print only the activation script without usage instructions."
)
@click.pass_obj
def jump_cmd(ctx: WorkstackContext, branch: str, script: bool) -> None:
    """Jump to BRANCH by finding and switching to its worktree.

    This command finds which worktree has the specified branch
    checked out and switches to it.

    Examples:

        workstack jump feature/user-auth

        workstack jump hotfix/critical-bug

    If multiple worktrees contain the branch, all options are shown.
    """
    repo = discover_repo_context(ctx, Path.cwd())

    # Get all worktrees
    worktrees = ctx.git_ops.list_worktrees(repo.root)

    # Find worktrees containing the target branch
    matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)

    # Handle three cases: no match, one match, multiple matches
    if len(matching_worktrees) == 0:
        # No worktrees have this branch checked out
        click.echo(
            f"Error: Branch '{branch}' is not checked out in any worktree.\n"
            f"To create a worktree with this branch, run:\n"
            f"  workstack create --from-branch {branch}",
            err=True,
        )
        raise SystemExit(1)

    if len(matching_worktrees) == 1:
        # Exactly one worktree contains this branch
        target_worktree = matching_worktrees[0]
        _perform_jump(ctx, repo.root, target_worktree, branch, script)

    else:
        # Multiple worktrees contain this branch
        # Check if any worktree has the branch directly checked out
        directly_checked_out = [wt for wt in matching_worktrees if wt.branch == branch]

        if len(directly_checked_out) == 1:
            # Exactly one worktree has the branch directly checked out - jump to it
            target_worktree = directly_checked_out[0]
            _perform_jump(ctx, repo.root, target_worktree, branch, script)
        else:
            # Zero or multiple worktrees have it directly checked out
            # Show error message listing all options
            click.echo(f"Branch '{branch}' exists in multiple worktrees:", err=True)
            for wt in matching_worktrees:
                click.echo(_format_worktree_info(wt, repo.root), err=True)

            click.echo("\nUse 'workstack switch' to choose a specific worktree first.", err=True)
            raise SystemExit(1)
