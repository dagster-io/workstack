import click
from erk_shared.output.output import machine_output, user_output

from erk.cli.activation import render_activation_script
from erk.cli.commands.navigation_helpers import (
    activate_worktree,
    check_clean_working_tree,
    delete_branch_and_worktree,
    ensure_graphite_enabled,
    resolve_up_navigation,
    verify_pr_merged,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.core.context import ErkContext


@click.command("up")
@click.option(
    "--script", is_flag=True, help="Print only the activation script without usage instructions."
)
@click.option(
    "--delete-current",
    is_flag=True,
    help="Delete current branch and worktree after navigating up",
)
@click.pass_obj
def up_cmd(ctx: ErkContext, script: bool, delete_current: bool) -> None:
    """Move to child branch in Graphite stack.

    With shell integration (recommended):
      erk up

    The shell wrapper function automatically activates the worktree.
    Run 'erk init --shell' to set up shell integration.

    Without shell integration:
      source <(erk up --script)

    This will cd to the child branch's worktree, create/activate .venv, and load .env variables.
    Requires Graphite to be enabled: 'erk config set use_graphite true'
    """
    ensure_graphite_enabled(ctx)
    repo = discover_repo_context(ctx, ctx.cwd)

    # Get current branch
    current_branch = ctx.git.get_current_branch(ctx.cwd)
    if current_branch is None:
        user_output("Error: Not currently on a branch (detached HEAD)")
        raise SystemExit(1)

    # Get all worktrees for checking if target has a worktree
    worktrees = ctx.git.list_worktrees(repo.root)

    # Get child branches for ambiguity checks
    children = ctx.graphite.get_child_branches(ctx.git, repo.root, current_branch)

    # Check for navigation ambiguity when --delete-current is set
    if delete_current and len(children) == 0:
        user_output(
            click.style("Error: ", fg="red") + "Cannot navigate up: already at top of stack"
        )
        user_output("Use 'gt branch delete' to delete this branch")
        raise SystemExit(1)

    if delete_current and len(children) > 1:
        user_output(
            click.style("Error: ", fg="red") + "Cannot navigate up: multiple child branches exist"
        )
        user_output("Use 'gt up' to interactively select a branch")
        raise SystemExit(1)

    # Safety checks before navigation (if --delete-current flag is set)
    current_worktree_path = None
    if delete_current:
        # Store current worktree path for later deletion
        current_worktree_path = ctx.git.find_worktree_for_branch(repo.root, current_branch)
        if current_worktree_path is None:
            user_output(
                click.style("Error: ", fg="red")
                + f"Could not find worktree for branch '{current_branch}'"
            )
            raise SystemExit(1)

        # Validate clean working tree (no uncommitted changes)
        check_clean_working_tree(ctx)

        # Validate PR is merged on GitHub
        verify_pr_merged(ctx, repo.root, current_branch)

    # Resolve navigation to get target branch (may auto-create worktree)
    target_name, was_created = resolve_up_navigation(ctx, repo, current_branch, worktrees)

    # Show creation message if worktree was just created
    if was_created and not script:
        user_output(
            click.style("✓", fg="green")
            + f" Created worktree for {click.style(target_name, fg='yellow')} and moved to it"
        )

    # Resolve target branch to actual worktree path
    target_wt_path = ctx.git.find_worktree_for_branch(repo.root, target_name)
    if target_wt_path is None:
        # This should not happen because _resolve_up_navigation already checks
        # But include defensive error handling
        user_output(
            f"Error: Branch '{target_name}' has no worktree. This should not happen.",
        )
        raise SystemExit(1)

    if delete_current and current_worktree_path is not None:
        # Handle activation inline when cleanup is needed
        Ensure.path_exists(ctx, target_wt_path, f"Worktree not found: {target_wt_path}")

        if script:
            # Generate activation script for shell integration
            activation_script = render_activation_script(worktree_path=target_wt_path)
            result = ctx.script_writer.write_activation_script(
                activation_script,
                command_name="up",
                comment=f"activate {target_wt_path.name}",
            )
            machine_output(str(result.path), nl=False)
        else:
            # Show user message for manual navigation
            user_output(
                "Shell integration not detected. "
                "Run 'erk init --shell' to set up automatic activation."
            )
            user_output("\nOr use: source <(erk up --script)")

        # Perform cleanup: delete branch and worktree
        delete_branch_and_worktree(ctx, repo.root, current_branch, current_worktree_path)

        # Exit after cleanup
        raise SystemExit(0)
    else:
        # No cleanup needed, use standard activation
        activate_worktree(ctx, repo, target_wt_path, script, "up")
