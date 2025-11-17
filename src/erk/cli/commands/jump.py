"""Jump command - find and switch to a worktree by branch name."""

import subprocess
from pathlib import Path

import click

from erk.cli.activation import render_activation_script
from erk.cli.commands.create import (
    add_worktree,
    make_env_content,
    run_commands_in_worktree,
)
from erk.cli.config import LoadedConfig
from erk.cli.core import discover_repo_context, worktree_path_for
from erk.cli.graphite import find_worktrees_containing_branch
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.gitops import WorktreeInfo
from erk.core.naming_utils import (
    ensure_unique_worktree_name,
    sanitize_worktree_name,
)
from erk.core.repo_discovery import RepoContext, ensure_repo_dir


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
    ctx: ErkContext,
    repo_root: Path,
    target_worktree: WorktreeInfo,
    branch: str,
    script: bool,
    is_newly_created: bool = False,
) -> None:
    """Perform the actual jump to a worktree.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        target_worktree: The worktree to jump to
        branch: Target branch name
        script: Whether to output only the activation script
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
        ctx.git_ops.checkout_branch(target_path, branch)

        # Show stack context
        if not script:
            stack = ctx.graphite_ops.get_branch_stack(ctx.git_ops, repo_root, branch)
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
        user_output(f"Or use: source <(erk jump {branch} --script)")


@click.command("jump")
@click.argument("branch", metavar="BRANCH")
@click.option(
    "--script", is_flag=True, help="Print only the activation script without usage instructions."
)
@click.pass_obj
def jump_cmd(ctx: ErkContext, branch: str, script: bool) -> None:
    """Jump to BRANCH by finding and switching to its worktree.

    This command finds which worktree has the specified branch checked out
    and switches to it. If the branch exists but isn't checked out anywhere,
    a worktree is automatically created. If the branch exists on origin but
    not locally, a tracking branch and worktree are created automatically.

    Examples:

        erk jump feature/user-auth      # Jump to existing worktree

        erk jump unchecked-branch       # Auto-create worktree

        erk jump origin-only-branch     # Create tracking branch + worktree

    If multiple worktrees contain the branch, all options are shown.
    """
    # Use existing repo from context if available (for tests), otherwise discover
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)
    ensure_repo_dir(repo)

    # Get all worktrees
    worktrees = ctx.git_ops.list_worktrees(repo.root)

    # Find worktrees containing the target branch
    matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)

    # Track whether we're creating a new worktree
    is_newly_created = False

    # Handle three cases: no match, one match, multiple matches
    if len(matching_worktrees) == 0:
        # No worktrees have this branch checked out - check if branch exists
        local_branches = ctx.git_ops.list_local_branches(repo.root)

        if branch not in local_branches:
            # Not a local branch - check if remote branch exists
            remote_branches = ctx.git_ops.list_remote_branches(repo.root)
            remote_ref = f"origin/{branch}"

            if remote_ref not in remote_branches:
                # Branch doesn't exist locally or on origin
                user_output(
                    f"Error: Branch '{branch}' does not exist.\n"
                    f"To create a new branch and worktree, run:\n"
                    f"  erk create --branch {branch}"
                )
                raise SystemExit(1)

            # Remote branch exists - create local tracking branch
            user_output(f"Branch '{branch}' exists on origin, creating local tracking branch...")
            try:
                ctx.git_ops.create_tracking_branch(repo.root, branch, remote_ref)
            except subprocess.CalledProcessError as e:
                user_output(
                    f"Error: Failed to create local tracking branch from {remote_ref}\n"
                    f"Details: {e.stderr}\n"
                    f"Suggested action:\n"
                    f"  1. Check git status and resolve any issues\n"
                    f"  2. Manually create branch: git branch --track {branch} {remote_ref}\n"
                    f"  3. Or use: erk create --branch {branch}"
                )
                raise SystemExit(1) from e

        # Branch exists but not checked out - auto-create worktree
        user_output(f"Branch '{branch}' not checked out, creating worktree...")

        # Load local config for .env template and post-create commands
        config = (
            ctx.local_config
            if ctx.local_config is not None
            else LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)
        )

        # Ensure workstacks directory exists

        # Generate and ensure unique worktree name
        name = sanitize_worktree_name(branch)
        name = ensure_unique_worktree_name(name, repo.worktrees_dir)

        # Calculate worktree path
        wt_path = worktree_path_for(repo.worktrees_dir, name)

        # Create worktree from existing branch
        add_worktree(
            ctx,
            repo.root,
            wt_path,
            branch=branch,
            ref=None,
            use_existing_branch=True,
            use_graphite=False,
            skip_remote_check=True,
        )

        user_output(click.style(f"✓ Created worktree: {name}", fg="green"))

        # Write .env file if template exists
        env_content = make_env_content(
            config, worktree_path=wt_path, repo_root=repo.root, name=name
        )
        if env_content:
            env_path = wt_path / ".env"
            env_path.write_text(env_content, encoding="utf-8")

        # Run post-create commands
        if config.post_create_commands:
            run_commands_in_worktree(
                commands=config.post_create_commands,
                worktree_path=wt_path,
                shell=config.post_create_shell,
            )

        # Refresh worktree list to include the newly created worktree
        worktrees = ctx.git_ops.list_worktrees(repo.root)
        matching_worktrees = find_worktrees_containing_branch(ctx, repo.root, worktrees, branch)

        # Mark that we just created this worktree
        is_newly_created = True

        # Fall through to jump to the newly created worktree

    if len(matching_worktrees) == 1:
        # Exactly one worktree contains this branch
        target_worktree = matching_worktrees[0]
        _perform_jump(ctx, repo.root, target_worktree, branch, script, is_newly_created)

    else:
        # Multiple worktrees contain this branch
        # Check if any worktree has the branch directly checked out
        directly_checked_out = [wt for wt in matching_worktrees if wt.branch == branch]

        if len(directly_checked_out) == 1:
            # Exactly one worktree has the branch directly checked out - jump to it
            target_worktree = directly_checked_out[0]
            _perform_jump(ctx, repo.root, target_worktree, branch, script, is_newly_created)
        else:
            # Zero or multiple worktrees have it directly checked out
            # Show error message listing all options
            user_output(f"Branch '{branch}' exists in multiple worktrees:")
            for wt in matching_worktrees:
                user_output(_format_worktree_info(wt, repo.root))

            user_output("\nUse 'erk switch' to choose a specific worktree first.")
            raise SystemExit(1)
