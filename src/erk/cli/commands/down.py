from pathlib import Path

import click

from erk.cli.commands.navigation_helpers import (
    _activate_root_repo,
    _activate_worktree,
    _ensure_graphite_enabled,
    _resolve_down_navigation,
    render_activation_script,
)
from erk.cli.core import discover_repo_context
from erk.cli.output import machine_output, user_output
from erk.core.context import ErkContext


def _check_clean_working_tree(ctx: ErkContext) -> None:
    """Check that working tree has no uncommitted changes.

    Raises SystemExit if uncommitted changes found.
    """
    if ctx.git.has_uncommitted_changes(ctx.cwd):
        user_output(
            click.style("Error: ", fg="red")
            + "Cannot delete current branch with uncommitted changes.\n"
            "Please commit or stash your changes first."
        )
        raise SystemExit(1)


def _verify_pr_merged(ctx: ErkContext, repo_root: Path, branch: str) -> None:
    """Verify that the branch's PR is merged on GitHub.

    Raises SystemExit if PR not found or not merged.
    """
    pr_info = ctx.github.get_pr_status(repo_root, branch, debug=False)

    if pr_info.state == "NONE" or pr_info.pr_number is None:
        user_output(
            click.style("Error: ", fg="red") + f"No pull request found for branch '{branch}'.\n"
            "Cannot verify merge status."
        )
        raise SystemExit(1)

    if pr_info.state != "MERGED":
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request for branch '{branch}' is not merged.\n"
            "Only merged branches can be deleted with --delete-current."
        )
        raise SystemExit(1)


def _delete_branch_and_worktree(
    ctx: ErkContext, repo_root: Path, branch: str, worktree_path: Path
) -> None:
    """Delete the specified branch and its worktree.

    Uses two-step deletion: git worktree remove, then manual cleanup.
    """

    # Remove the worktree
    ctx.git.remove_worktree(repo_root, worktree_path, force=True)
    user_output(f"✓ Removed worktree: {click.style(str(worktree_path), fg='green')}")

    # Delete the branch using Git abstraction
    ctx.git.delete_branch_with_graphite(repo_root, branch, force=True)
    user_output(f"✓ Deleted branch: {click.style(branch, fg='yellow')}")

    # Prune worktree metadata
    ctx.git.prune_worktrees(repo_root)


@click.command("down")
@click.option(
    "--script", is_flag=True, help="Print only the activation script without usage instructions."
)
@click.option(
    "--delete-current",
    is_flag=True,
    help="Delete current branch and worktree after navigating down",
)
@click.pass_obj
def down_cmd(ctx: ErkContext, script: bool, delete_current: bool) -> None:
    """Move to parent branch in Graphite stack.

    With shell integration (recommended):
      erk down

    The shell wrapper function automatically activates the worktree.
    Run 'erk init --shell' to set up shell integration.

    Without shell integration:
      source <(erk down --script)

    This will cd to the parent branch's worktree (or root repo if parent is trunk),
    create/activate .venv, and load .env variables.
    Requires Graphite to be enabled: 'erk config set use_graphite true'
    """
    _ensure_graphite_enabled(ctx)
    repo = discover_repo_context(ctx, ctx.cwd)
    trunk_branch = ctx.trunk_branch

    # Get current branch
    current_branch = ctx.git.get_current_branch(ctx.cwd)
    if current_branch is None:
        user_output("Error: Not currently on a branch (detached HEAD)")
        raise SystemExit(1)

    # Store current worktree path for deletion (before navigation)
    # Find the worktree for the current branch
    current_worktree_path = None
    if delete_current:
        current_worktree_path = ctx.git.find_worktree_for_branch(repo.root, current_branch)
        if current_worktree_path is None:
            user_output(
                click.style("Error: ", fg="red")
                + f"Cannot find worktree for current branch '{current_branch}'."
            )
            raise SystemExit(1)

    # Safety checks before navigation (if --delete-current flag is set)
    if delete_current:
        _check_clean_working_tree(ctx)
        _verify_pr_merged(ctx, repo.root, current_branch)

    # Get all worktrees for checking if target has a worktree
    worktrees = ctx.git.list_worktrees(repo.root)

    # Resolve navigation to get target branch or 'root' (may auto-create worktree)
    target_name, was_created = _resolve_down_navigation(
        ctx, repo, current_branch, worktrees, trunk_branch
    )

    # Show creation message if worktree was just created
    if was_created and not script:
        user_output(
            click.style("✓", fg="green")
            + f" Created worktree for {click.style(target_name, fg='yellow')} and moved to it"
        )

    # Check if target_name refers to 'root' which means root repo
    if target_name == "root":
        if delete_current and current_worktree_path is not None:
            # Handle activation inline so we can do cleanup before exiting
            root_path = repo.root
            if script:
                script_content = render_activation_script(
                    worktree_path=root_path,
                    final_message='echo "Switched to root repo: $(pwd)"',
                    comment="work activate-script (root repo)",
                )
                result = ctx.script_writer.write_activation_script(
                    script_content,
                    command_name="down",
                    comment="activate root",
                )
                machine_output(str(result.path), nl=False)
            else:
                user_output(f"Switched to root repo: {root_path}")

            # Perform cleanup (no context regeneration needed - we haven't changed dirs)
            _delete_branch_and_worktree(ctx, repo.root, current_branch, current_worktree_path)

            # Exit after cleanup
            raise SystemExit(0)
        else:
            # No cleanup needed, use standard activation
            _activate_root_repo(ctx, repo, script, "down")

    # Resolve target branch to actual worktree path
    target_wt_path = ctx.git.find_worktree_for_branch(repo.root, target_name)
    if target_wt_path is None:
        # This should not happen because _resolve_down_navigation already checks
        # But include defensive error handling
        user_output(
            f"Error: Branch '{target_name}' has no worktree. This should not happen.",
        )
        raise SystemExit(1)

    if delete_current and current_worktree_path is not None:
        # Handle activation inline so we can do cleanup before exiting
        if not ctx.git.path_exists(target_wt_path):
            user_output(f"Worktree not found: {target_wt_path}")
            raise SystemExit(1)

        if script:
            activation_script = render_activation_script(worktree_path=target_wt_path)
            result = ctx.script_writer.write_activation_script(
                activation_script,
                command_name="down",
                comment=f"activate {target_wt_path.name}",
            )
            machine_output(str(result.path), nl=False)
        else:
            user_output(
                "Shell integration not detected. "
                "Run 'erk init --shell' to set up automatic activation."
            )
            user_output("\nOr use: source <(erk down --script)")

        # Perform cleanup (no context regeneration needed - we haven't actually changed directories)
        _delete_branch_and_worktree(ctx, repo.root, current_branch, current_worktree_path)

        # Exit after cleanup
        raise SystemExit(0)
    else:
        # No cleanup needed, use standard activation
        _activate_worktree(ctx, repo, target_wt_path, script, "down")
