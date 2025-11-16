import os
import subprocess
from pathlib import Path

import click

from erk.cli.activation import render_activation_script
from erk.cli.commands.remove import _remove_worktree
from erk.cli.core import discover_repo_context, worktree_path_for
from erk.cli.output import user_output
from erk.cli.shell_utils import render_cd_script
from erk.core.context import ErkContext, regenerate_context
from erk.core.repo_discovery import ensure_repo_dir
from erk.core.script_writer import ScriptResult
from erk.core.sync_utils import PRStatus, identify_deletable_worktrees


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
    # Always route to stderr for consistent behavior
    user_output(message)


def _return_to_original_worktree(
    ctx: ErkContext,
    worktrees_dir: Path,
    current_worktree_name: str | None,
    *,
    script_mode: bool,
) -> None:
    """Return to original worktree if it exists.

    Only changes directory in non-script mode. In script mode, directory changes
    are handled by shell wrapper executing the output script.
    """
    if current_worktree_name is None:
        return

    wt_path = worktree_path_for(worktrees_dir, current_worktree_name)
    if not ctx.git_ops.path_exists(wt_path):
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
    ctx: ErkContext,
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
            "Error: 'erk sync' requires Graphite. Run 'erk config set use-graphite true'",
            script_mode=script,
            error=True,
        )
        raise SystemExit(1)

    # Step 2: Save current location
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_repo_dir(repo)

    # Determine current worktree (if any)
    current_wt_path = ctx.cwd.resolve()
    current_worktree_name: str | None = None

    if current_wt_path.parent == repo.worktrees_dir:
        current_worktree_name = current_wt_path.name

    # Step 3: Switch to root (only if not already at root)
    # In pure test mode with sentinel paths, os.chdir() will fail gracefully
    if ctx.cwd.resolve() != repo.root:
        try:
            os.chdir(repo.root)
            ctx = regenerate_context(ctx)
        except OSError:
            # Path doesn't exist (sentinel path in tests), skip chdir
            # Context remains unchanged, which is fine for pure test mode
            pass

    # Step 4: Run `gt sync`
    cmd = ["gt", "sync"]
    if force:
        cmd.append("-f")

    # For external commands like gt sync, check dry_run to avoid subprocess execution
    if not dry_run:
        if verbose:
            _emit(f"Running: {' '.join(cmd)}", script_mode=script)
        try:
            ctx.graphite_ops.sync(repo.root, force=force, quiet=not verbose)
        except subprocess.CalledProcessError as e:
            error_detail = e.stderr.strip() if e.stderr else f"exit code {e.returncode}"
            _emit(
                f"Error: gt sync failed: {error_detail}",
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

    # Fetch PR status for all branches
    pr_statuses: dict[str, PRStatus] = {}
    for wt in worktrees:
        if wt.branch is not None:
            state, pr_number, title = ctx.github_ops.get_pr_status(
                repo.root, wt.branch, debug=False
            )
            pr_statuses[wt.branch] = PRStatus(
                branch=wt.branch, state=state, pr_number=pr_number, title=title
            )

    # Identify deletable worktrees using pure business logic
    deletable = identify_deletable_worktrees(worktrees, pr_statuses, repo.root, repo.worktrees_dir)

    # Step 6: Display and optionally clean
    if not deletable:
        _emit("✓ No worktrees to clean up", script_mode=script)
    else:
        for wt in deletable:
            # Display formatted
            name_part = click.style(wt.name, fg="cyan", bold=True)
            branch_part = click.style(f"[{wt.branch}]", fg="yellow")
            state_part = click.style(
                wt.pr_state.lower(), fg="green" if wt.pr_state == "MERGED" else "red"
            )
            pr_part = click.style(f"PR #{wt.pr_number}", fg="bright_black")

            _emit(f"  {name_part} {branch_part} - {state_part} ({pr_part})", script_mode=script)

        # Confirm unless --force or --dry-run
        if not force and not dry_run:
            if not click.confirm(
                f"Remove {len(deletable)} worktree(s)?", default=False, err=script
            ):
                _emit("Cleanup cancelled.", script_mode=script)
                _return_to_original_worktree(
                    ctx, repo.worktrees_dir, current_worktree_name, script_mode=script
                )
                return

        # Remove each worktree
        for wt in deletable:
            if dry_run:
                _emit(
                    f"[DRY RUN] Would remove worktree: {wt.name} (branch: {wt.branch})",
                    script_mode=script,
                )
            else:
                # Reuse remove logic from remove.py
                _remove_worktree(
                    ctx,
                    wt.name,
                    force=True,  # Already confirmed above
                    delete_stack=False,  # Leave branches for gt sync -f
                    dry_run=False,
                    quiet=True,  # Suppress planning output during sync
                )
                # Show clean confirmation after removal completes
                _emit(f"✓ Removed: {wt.name} [{wt.branch}]", script_mode=script)

        # Step 6.5: Automatically run second gt sync -f to delete branches (when force=True)
        # For external commands like gt sync, check dry_run to avoid subprocess execution
        if force and not dry_run and deletable:
            ctx.graphite_ops.sync(repo.root, force=True, quiet=not verbose)
            _emit("✓ Deleted merged branches", script_mode=script)

        # Only show manual instruction if force was not used
        if not force:
            _emit(
                "Next step: Run 'erk sync -f' to automatically delete the merged branches.",
                script_mode=script,
            )

    # Step 7: Return to original worktree
    script_result: ScriptResult | None = None

    if current_worktree_name:
        wt_path = worktree_path_for(repo.worktrees_dir, current_worktree_name)

        # Check if worktree still exists
        if ctx.git_ops.path_exists(wt_path):
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
                result = ctx.script_writer.write_activation_script(
                    script_content,
                    command_name="sync",
                    comment=f"return to {current_worktree_name}",
                )
                script_result = result
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
                result = ctx.script_writer.write_activation_script(
                    script_content,
                    command_name="sync",
                    comment="return to root",
                )
                script_result = result

    # Output temp file path for shell wrapper
    if script and script_result:
        script_result.output_for_shell_integration()
