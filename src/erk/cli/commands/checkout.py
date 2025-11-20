"""Checkout command - find and switch to a worktree by branch name."""

import subprocess
from pathlib import Path

import click

from erk.cli.activation import render_activation_script
from erk.cli.commands.create import ensure_worktree_for_branch
from erk.cli.commands.navigation_helpers import complete_branch_names
from erk.cli.core import discover_repo_context
from erk.cli.graphite import find_worktrees_containing_branch
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.git.abc import WorktreeInfo
from erk.core.repo_discovery import RepoContext, ensure_repo_dir


def try_switch_root_worktree(ctx: ErkContext, repo: RepoContext, branch: str) -> Path | None:
    """Try to switch root worktree to branch if it's trunk and root is clean.

    This implements the "takeover" behavior where checking out trunk in a clean root
    worktree switches the root to trunk instead of creating a new dated worktree.

    Args:
        ctx: Erk context with git operations
        repo: Repository context
        branch: Branch name to check

    Returns:
        Root worktree path if successful, None otherwise
    """
    # Check if branch is trunk
    if branch != ctx.trunk_branch:
        return None

    # Find root worktree
    worktrees = ctx.git.list_worktrees(repo.root)
    root_worktree = None
    for wt in worktrees:
        if wt.is_root:
            root_worktree = wt
            break

    if root_worktree is None:
        return None

    # Check if root is clean
    if not ctx.git.is_worktree_clean(root_worktree.path):
        return None

    # Switch root to trunk branch
    ctx.git.checkout_branch(root_worktree.path, branch)

    return root_worktree.path


def _handle_implement_flag(worktree_path: Path, branch: str) -> None:
    """Handle the --implement flag by launching Claude Code if plan exists.

    Args:
        worktree_path: Path to the target worktree
        branch: Branch name for error messages
    """
    plan_file = worktree_path / ".plan" / "plan.md"

    if not plan_file.exists():
        # Display error and exit
        error_message = click.style("Error: ", fg="red")
        branch_styled = click.style(branch, fg="yellow")
        user_output(f"\n{error_message}No plan found for branch {branch_styled}")
        user_output("\nThis worktree does not have a .plan/ folder with plan.md.")
        user_output("The --implement flag only works after creating a planned worktree.")
        user_output("\nTo create a planned worktree:")
        user_output("  1. Run: /erk:persist-plan")
        user_output("  2. Run: /erk:create-planned-wt")
        user_output("  3. Then use: erk checkout <branch> --implement")
        raise SystemExit(1)

    # Plan exists - launch Claude Code
    success_message = click.style("✓", fg="green")
    user_output(f"\n{success_message} Launching Claude Code for plan implementation")

    # Launch Claude in foreground (blocking)
    # Note: Not using check=True because Claude may exit with non-zero codes during normal operation
    subprocess.run(
        ["claude", "--permission-mode", "acceptEdits", "/erk:implement-plan"],
        cwd=worktree_path,
    )


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


def _perform_checkout(
    ctx: ErkContext,
    repo_root: Path,
    target_worktree: WorktreeInfo,
    branch: str,
    script: bool,
    implement: bool,
    is_newly_created: bool = False,
) -> None:
    """Perform the actual jump to a worktree.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        target_worktree: The worktree to jump to
        branch: Target branch name
        script: Whether to output only the activation script
        implement: Whether to launch Claude Code for plan implementation
        is_newly_created: Whether the worktree was just created (default False)
    """
    target_path = target_worktree.path
    current_branch_in_worktree = target_worktree.branch
    current_cwd = ctx.cwd

    # Check if branch is already checked out in the worktree
    need_checkout = current_branch_in_worktree != branch

    # If we need to checkout, do it before generating the activation script
    if need_checkout:
        # Checkout the branch in the target worktree
        ctx.git.checkout_branch(target_path, branch)

        # Show stack context
        if not script:
            stack = ctx.graphite.get_branch_stack(ctx.git, repo_root, branch)
            if stack:
                user_output(f"Stack: {' -> '.join(stack)}")
            user_output(f"Checked out '{branch}' in worktree")

    # Generate activation script
    if script:
        # Script mode: always generate script (for shell integration or manual sourcing)
        is_switching_location = current_cwd != target_path

        # Determine worktree name from path
        worktree_name = target_path.name

        # Four-case message logic:
        if is_newly_created:
            # Case 4: Jumped to newly created worktree
            styled_wt = click.style(worktree_name, fg="cyan", bold=True)
            jump_message = f'echo "Jumped to new worktree {styled_wt}"'
        elif not is_switching_location:
            # Case 1: Already on target branch in current worktree
            styled_branch = click.style(branch, fg="yellow")
            styled_wt = click.style(worktree_name, fg="cyan", bold=True)
            jump_message = f'echo "Already on branch {styled_branch} in worktree {styled_wt}"'
        elif not need_checkout:
            # Case 2: Jumped to existing worktree with branch already checked out
            styled_wt = click.style(worktree_name, fg="cyan", bold=True)
            if worktree_name == branch:
                # Standard naming
                jump_message = f'echo "Jumped to worktree {styled_wt}"'
            else:
                # Edge case: non-standard naming
                styled_branch = click.style(branch, fg="yellow")
                jump_message = f'echo "Jumped to worktree {styled_wt} (branch {styled_branch})"'
        else:
            # Case 3: Jumped to existing worktree and checked out branch
            styled_wt = click.style(worktree_name, fg="cyan", bold=True)
            styled_branch = click.style(branch, fg="yellow")
            jump_message = (
                f'echo "Jumped to worktree {styled_wt} and checked out branch {styled_branch}"'
            )

        script_content = render_activation_script(
            worktree_path=target_path, final_message=jump_message
        )

        result = ctx.script_writer.write_activation_script(
            script_content,
            command_name="jump",
            comment=f"jump to {branch}",
        )
        result.output_for_shell_integration()
    else:
        # Non-script mode: Apply same four-case logic with user_output()
        worktree_name = target_path.name

        if is_newly_created:
            styled_wt = click.style(worktree_name, fg="cyan", bold=True)
            user_output(f"Jumped to new worktree {styled_wt}")
        elif ctx.cwd == target_path:
            styled_branch = click.style(branch, fg="yellow")
            styled_wt = click.style(worktree_name, fg="cyan", bold=True)
            user_output(f"Already on branch {styled_branch} in worktree {styled_wt}")
        elif current_branch_in_worktree == branch:
            styled_wt = click.style(worktree_name, fg="cyan", bold=True)
            if worktree_name == branch:
                user_output(f"Jumped to worktree {styled_wt}")
            else:
                styled_branch = click.style(branch, fg="yellow")
                user_output(f"Jumped to worktree {styled_wt} (branch {styled_branch})")
        else:
            styled_wt = click.style(worktree_name, fg="cyan", bold=True)
            styled_branch = click.style(branch, fg="yellow")
            user_output(f"Jumped to worktree {styled_wt} and checked out branch {styled_branch}")

        # Show manual instructions
        user_output("\nShell integration not detected. Run 'erk init --shell' to set up.")
        user_output(f"Or use: source <(erk checkout {branch} --script)")

    # Handle --implement flag (both script and non-script mode)
    if implement:
        _handle_implement_flag(target_path, branch)


@click.command("checkout")
@click.argument("branch", metavar="BRANCH", shell_complete=complete_branch_names)
@click.option(
    "--script", is_flag=True, help="Print only the activation script without usage instructions."
)
@click.option(
    "--implement", is_flag=True, help="Launch Claude Code to implement plan after checkout"
)
@click.pass_obj
def checkout_cmd(ctx: ErkContext, branch: str, script: bool, implement: bool) -> None:
    """Checkout BRANCH by finding and switching to its worktree.

    This command finds which worktree has the specified branch checked out
    and switches to it. If the branch exists but isn't checked out anywhere,
    a worktree is automatically created. If the branch exists on origin but
    not locally, a tracking branch and worktree are created automatically.

    Examples:

        erk checkout feature/user-auth      # Checkout existing worktree

        erk checkout unchecked-branch       # Auto-create worktree

        erk checkout origin-only-branch     # Create tracking branch + worktree

    If multiple worktrees contain the branch, all options are shown.
    """
    # Use existing repo from context if available (for tests), otherwise discover
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)
    ensure_repo_dir(repo)

    # Get all worktrees
    worktrees = ctx.git.list_worktrees(repo.root)

    # Find worktrees containing the target branch
    matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)

    # Track whether we're creating a new worktree
    is_newly_created = False

    # Handle three cases: no match, one match, multiple matches
    if len(matching_worktrees) == 0:
        # No worktrees have this branch checked out
        # First, try switching clean root worktree if checking out trunk
        root_path = try_switch_root_worktree(ctx, repo, branch)
        if root_path is not None:
            # Successfully switched root to trunk - refresh and jump to it
            worktrees = ctx.git.list_worktrees(repo.root)
            matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)
        else:
            # Root not available or not trunk - auto-create worktree
            _worktree_path, is_newly_created = ensure_worktree_for_branch(
                ctx, repo, branch, is_plan_derived=False
            )

            # Refresh worktree list to include the newly created worktree
            worktrees = ctx.git.list_worktrees(repo.root)
            matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)

        # Fall through to jump to the worktree

    if len(matching_worktrees) == 1:
        # Exactly one worktree contains this branch
        target_worktree = matching_worktrees[0]
        _perform_checkout(
            ctx, repo.root, target_worktree, branch, script, implement, is_newly_created
        )

    else:
        # Multiple worktrees contain this branch
        # Check if any worktree has the branch directly checked out
        directly_checked_out = [wt for wt in matching_worktrees if wt.branch == branch]

        if len(directly_checked_out) == 1:
            # Exactly one worktree has the branch directly checked out - jump to it
            target_worktree = directly_checked_out[0]
            _perform_checkout(
                ctx, repo.root, target_worktree, branch, script, implement, is_newly_created
            )
        else:
            # Zero or multiple worktrees have it directly checked out
            # Show error message listing all options
            user_output(f"Branch '{branch}' exists in multiple worktrees:")
            for wt in matching_worktrees:
                user_output(_format_worktree_info(wt, repo.root))

            user_output("\nPlease specify which worktree to use.")
            raise SystemExit(1)
