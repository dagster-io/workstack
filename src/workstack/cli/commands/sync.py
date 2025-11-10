import os
import subprocess
from pathlib import Path

import click

from workstack.cli.activation import render_activation_script
from workstack.cli.commands.remove import _remove_worktree
from workstack.cli.core import discover_repo_context, worktree_path_for
from workstack.cli.shell_utils import render_cd_script, write_script_to_temp
from workstack.core.context import WorkstackContext, regenerate_context
from workstack.core.repo_discovery import ensure_workstacks_dir


def _emit(message: str, *, script_mode: bool, error: bool = False) -> None:
    """Emit a message to stdout or stderr based on script mode.

    In script mode, ALL output goes to stderr (so the shell wrapper can capture
    only the activation script from stdout). The `error` parameter has no effect
    in script mode since everything is already sent to stderr.

    In non-script mode, output goes to stdout by default, unless `error=True`.

    Args:
        message: Text to output.
        script_mode: True when running in --script mode (all output to stderr).
        error: Force stderr output in non-script mode (ignored in script mode).
    """
    click.echo(message, err=error or script_mode)


def _return_to_original_worktree(
    workstacks_dir: Path, current_worktree_name: str | None, *, script_mode: bool
) -> None:
    """Return to original worktree if it exists.

    Only changes directory in non-script mode. In script mode, directory changes
    are handled by shell wrapper executing the output script.
    """
    if current_worktree_name is None:
        return

    wt_path = worktree_path_for(workstacks_dir, current_worktree_name)
    if not wt_path.exists():
        return

    _emit(f"✓ Returning to: {current_worktree_name}", script_mode=script_mode)
    # Only chdir in non-script mode; script output handles cd in script mode
    if not script_mode:
        os.chdir(wt_path)


@click.command("sync")
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Pass --force to gt sync and automatically remove merged worktrees without confirmation.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    # dry_run=False: Allow destructive operations by default
    default=False,
    help="Show what would be done without executing destructive operations.",
)
@click.option(
    "--script",
    is_flag=True,
    hidden=True,
    help="Output shell script for directory change instead of messages.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed sync output.",
)
@click.pass_obj
def sync_cmd(
    ctx: WorkstackContext,
    force: bool,
    dry_run: bool,
    script: bool,
    verbose: bool,
) -> None:
    """Sync with Graphite and clean up merged worktrees.

    This command must be run from a workstack-managed repository.

    Steps:
    1. Verify graphite is enabled
    2. Save current worktree location
    3. Switch to root worktree (to avoid git checkout conflicts)
    4. Run `gt sync [-f]` from root
    5. Identify merged/closed workstacks
    6. With -f: automatically remove worktrees without confirmation
    7. Without -f: show deletable worktrees and prompt for confirmation
    8. Return to original worktree (if it still exists)
    """

    # Step 1: Verify Graphite is enabled
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
    if not use_graphite:
        _emit(
            "Error: 'workstack sync' requires Graphite. "
            "Run 'workstack config set use-graphite true'",
            script_mode=script,
            error=True,
        )
        raise SystemExit(1)

    # Step 2: Save current location
    repo = discover_repo_context(ctx, ctx.cwd)
    workstacks_dir = ensure_workstacks_dir(repo)

    # Determine current worktree (if any)
    current_wt_path = ctx.cwd.resolve()
    current_worktree_name: str | None = None

    if current_wt_path.parent == workstacks_dir:
        current_worktree_name = current_wt_path.name

    # Step 3: Switch to root (only if not already at root)
    if ctx.cwd.resolve() != repo.root:
        os.chdir(repo.root)
        ctx = regenerate_context(ctx, repo_root=repo.root)

    # Step 4: Run `gt sync`
    cmd = ["gt", "sync"]
    if force:
        cmd.append("-f")

    if not dry_run:
        if verbose:
            _emit(f"Running: {' '.join(cmd)}", script_mode=script)
        try:
            ctx.graphite_ops.sync(repo.root, force=force, quiet=not verbose)
        except subprocess.CalledProcessError as e:
            _emit(
                f"Error: gt sync failed with exit code {e.returncode}",
                script_mode=script,
                error=True,
            )
            raise SystemExit(e.returncode) from e
        except FileNotFoundError as e:
            _emit(
                "Error: 'gt' command not found. Install Graphite CLI: "
                "brew install withgraphite/tap/graphite",
                script_mode=script,
                error=True,
            )
            raise SystemExit(1) from e
    else:
        _emit(f"[DRY RUN] Would run {' '.join(cmd)}", script_mode=script)

    # Step 5: Identify deletable workstacks
    worktrees = ctx.git_ops.list_worktrees(repo.root)

    # Track workstacks eligible for deletion
    deletable: list[tuple[str, str, str, int]] = []

    for wt in worktrees:
        # Skip root
        if wt.path == repo.root:
            continue

        # Skip detached HEAD
        if wt.branch is None:
            continue

        # Skip non-managed worktrees
        if wt.path.parent != workstacks_dir:
            continue

        # Check PR status
        state, pr_number, title = ctx.github_ops.get_pr_status(repo.root, wt.branch, debug=False)

        if state in ("MERGED", "CLOSED") and pr_number is not None:
            name = wt.path.name
            deletable.append((name, wt.branch, state, pr_number))

    # Step 6: Display and optionally clean
    if not deletable:
        _emit("✓ No worktrees to clean up", script_mode=script)
    else:
        for name, branch, state, pr_number in deletable:
            # Display formatted
            name_part = click.style(name, fg="cyan", bold=True)
            branch_part = click.style(f"[{branch}]", fg="yellow")
            state_part = click.style(state.lower(), fg="green" if state == "MERGED" else "red")
            pr_part = click.style(f"PR #{pr_number}", fg="bright_black")

            _emit(f"  {name_part} {branch_part} - {state_part} ({pr_part})", script_mode=script)

        # Confirm unless --force or --dry-run
        if not force and not dry_run:
            if not click.confirm(
                f"Remove {len(deletable)} worktree(s)?", default=False, err=script
            ):
                _emit("Cleanup cancelled.", script_mode=script)
                _return_to_original_worktree(
                    workstacks_dir, current_worktree_name, script_mode=script
                )
                return

        # Remove each worktree
        for name, _branch, _state, _pr_number in deletable:
            if dry_run:
                _emit(
                    f"[DRY RUN] Would remove worktree: {name} (branch: {_branch})",
                    script_mode=script,
                )
            else:
                # Reuse remove logic from remove.py
                _remove_worktree(
                    ctx,
                    name,
                    force=True,  # Already confirmed above
                    delete_stack=False,  # Leave branches for gt sync -f
                    dry_run=False,
                    quiet=True,  # Suppress planning output during sync
                )
                # Show clean confirmation after removal completes
                _emit(f"✓ Removed: {name} [{_branch}]", script_mode=script)

        # Step 6.5: Automatically run second gt sync -f to delete branches (when force=True)
        if force and not dry_run and deletable:
            ctx.graphite_ops.sync(repo.root, force=True, quiet=not verbose)
            _emit("✓ Deleted merged branches", script_mode=script)

        # Only show manual instruction if force was not used
        if not force:
            _emit(
                "Next step: Run 'workstack sync -f' to automatically delete the merged branches.",
                script_mode=script,
            )

    # Step 7: Return to original worktree
    script_output_path: Path | None = None

    if current_worktree_name:
        wt_path = worktree_path_for(workstacks_dir, current_worktree_name)

        # Check if worktree still exists
        if wt_path.exists():
            _emit(f"✓ Returning to: {current_worktree_name}", script_mode=script)
            if not script:
                os.chdir(wt_path)
            else:
                # Generate cd script for shell wrapper
                script_content = render_cd_script(
                    wt_path,
                    comment=f"return to {current_worktree_name}",
                    success_message=f"✓ Returned to {current_worktree_name}.",
                )
                script_output_path = write_script_to_temp(
                    script_content,
                    command_name="sync",
                    comment=f"return to {current_worktree_name}",
                )
        else:
            _emit(
                f"✅ {repo.root}",
                script_mode=script,
            )
            if script:
                script_content = render_activation_script(
                    worktree_path=repo.root,
                    comment="return to root",
                    final_message=f'echo "✓ Switched to: root [{repo.root}]"',
                )
                script_output_path = write_script_to_temp(
                    script_content,
                    command_name="sync",
                    comment="return to root",
                )

    # Output temp file path for shell wrapper
    if script and script_output_path:
        click.echo(str(script_output_path), nl=False)
