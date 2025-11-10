from pathlib import Path

import click

from workstack.cli.activation import render_activation_script
from workstack.cli.core import (
    RepoContext,
    discover_repo_context,
    ensure_workstacks_dir,
    worktree_path_for,
)
from workstack.cli.debug import debug_log
from workstack.cli.shell_utils import write_script_to_temp
from workstack.core.context import WorkstackContext, create_context, read_trunk_from_pyproject
from workstack.core.gitops import WorktreeInfo


def _ensure_graphite_enabled(ctx: WorkstackContext) -> None:
    """Validate that Graphite is enabled.

    Args:
        ctx: Workstack context

    Raises:
        SystemExit: If Graphite is not enabled
    """
    if not ctx.global_config_ops.get_use_graphite():
        click.echo(
            "Error: This command requires Graphite to be enabled. "
            "Run 'workstack config set use_graphite true'",
            err=True,
        )
        raise SystemExit(1)


def _activate_root_repo(repo: RepoContext, script: bool, command_name: str) -> None:
    """Activate the root repository and exit.

    Args:
        repo: Repository context
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation)

    Raises:
        SystemExit: Always (successful exit after activation)
    """
    root_path = repo.root
    if script:
        script_content = render_activation_script(
            worktree_path=root_path,
            final_message='echo "Switched to root repo: $(pwd)"',
            comment="work activate-script (root repo)",
        )
        script_path = write_script_to_temp(
            script_content,
            command_name=command_name,
            comment="activate root",
        )
        click.echo(str(script_path), nl=False)
    else:
        click.echo(f"Switched to root repo: {root_path}")
        click.echo(
            "\nShell integration not detected. "
            "Run 'workstack init --shell' to set up automatic activation."
        )
        if command_name == "switch":
            click.echo("Or use: source <(workstack switch root --script)")
        else:
            click.echo(f"Or use: source <(workstack {command_name} --script)")
    raise SystemExit(0)


def _activate_worktree(
    repo: RepoContext, target_path: Path, script: bool, command_name: str
) -> None:
    """Activate a worktree and exit.

    Args:
        repo: Repository context
        target_path: Path to the target worktree directory
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation and debug logging)

    Raises:
        SystemExit: If worktree not found, or after successful activation
    """
    wt_path = target_path

    if not wt_path.exists():
        click.echo(f"Worktree not found: {wt_path}", err=True)
        raise SystemExit(1)

    worktree_name = wt_path.name

    if script:
        activation_script = render_activation_script(worktree_path=wt_path)
        script_path = write_script_to_temp(
            activation_script,
            command_name=command_name,
            comment=f"activate {worktree_name}",
        )

        debug_log(f"{command_name.capitalize()}: Generated script at {script_path}")
        debug_log(f"{command_name.capitalize()}: Script content:\n{activation_script}")
        debug_log(f"{command_name.capitalize()}: File exists? {script_path.exists()}")

        click.echo(str(script_path), nl=False)
    else:
        click.echo(
            "Shell integration not detected. "
            "Run 'workstack init --shell' to set up automatic activation."
        )
        if command_name == "switch":
            click.echo(f"\nOr use: source <(workstack switch {worktree_name} --script)")
        else:
            click.echo(f"\nOr use: source <(workstack {command_name} --script)")
    raise SystemExit(0)


def _resolve_up_navigation(
    ctx: WorkstackContext, repo: RepoContext, current_branch: str, worktrees: list[WorktreeInfo]
) -> str:
    """Resolve --up navigation to determine target branch name.

    Args:
        ctx: Workstack context
        repo: Repository context
        current_branch: Current branch name
        worktrees: List of worktrees from git_ops.list_worktrees()

    Returns:
        Target branch name to switch to

    Raises:
        SystemExit: If navigation fails (at top of stack or target has no worktree)
    """
    # Navigate up to child branch
    children = ctx.graphite_ops.get_child_branches(ctx.git_ops, repo.root, current_branch)
    if not children:
        click.echo("Already at the top of the stack (no child branches)", err=True)
        raise SystemExit(1)

    # Fail explicitly if multiple children exist
    if len(children) > 1:
        children_list = ", ".join(f"'{child}'" for child in children)
        click.echo(
            f"Error: Branch '{current_branch}' has multiple children: {children_list}.\n"
            f"Please create worktree for specific child: workstack create <branch-name>",
            err=True,
        )
        raise SystemExit(1)

    # Use the single child
    target_branch = children[0]

    # Check if target branch has a worktree
    target_wt_path = ctx.git_ops.find_worktree_for_branch(repo.root, target_branch)
    if target_wt_path is None:
        click.echo(
            f"Branch '{target_branch}' is the next branch up in the stack "
            f"but has no worktree.\n"
            f"To create a worktree for it, run:\n"
            f"  workstack create {target_branch}",
            err=True,
        )
        raise SystemExit(1)

    return target_branch


def _resolve_down_navigation(
    ctx: WorkstackContext,
    repo: RepoContext,
    current_branch: str,
    worktrees: list[WorktreeInfo],
    trunk_branch: str | None,
) -> str:
    """Resolve --down navigation to determine target branch name.

    Args:
        ctx: Workstack context
        repo: Repository context
        current_branch: Current branch name
        worktrees: List of worktrees from git_ops.list_worktrees()
        trunk_branch: Configured trunk branch name, or None for auto-detection

    Returns:
        Target branch name or 'root' to switch to

    Raises:
        SystemExit: If navigation fails (at bottom of stack or target has no worktree)
    """
    # Navigate down to parent branch
    parent_branch = ctx.graphite_ops.get_parent_branch(ctx.git_ops, repo.root, current_branch)
    if parent_branch is None:
        # Check if we're already on trunk
        detected_trunk = ctx.git_ops.detect_default_branch(repo.root, trunk_branch)
        if current_branch == detected_trunk:
            click.echo(
                f"Already at the bottom of the stack (on trunk branch '{detected_trunk}')",
                err=True,
            )
            raise SystemExit(1)
        else:
            click.echo(
                "Error: Could not determine parent branch from Graphite metadata",
                err=True,
            )
            raise SystemExit(1)

    # Check if parent is the trunk - if so, switch to root
    detected_trunk = ctx.git_ops.detect_default_branch(repo.root, trunk_branch)
    if parent_branch == detected_trunk:
        # Check if trunk is checked out in root (repo.root path)
        trunk_wt_path = ctx.git_ops.find_worktree_for_branch(repo.root, detected_trunk)
        if trunk_wt_path is not None and trunk_wt_path == repo.root:
            # Trunk is in root repository, not in a dedicated worktree
            return "root"
        else:
            # Trunk has a dedicated worktree
            if trunk_wt_path is None:
                click.echo(
                    f"Branch '{parent_branch}' is the parent branch but has no worktree.\n"
                    f"To switch to the root repository, run:\n"
                    f"  workstack switch root",
                    err=True,
                )
                raise SystemExit(1)
            return parent_branch
    else:
        # Parent is not trunk, check if it has a worktree
        target_wt_path = ctx.git_ops.find_worktree_for_branch(repo.root, parent_branch)
        if target_wt_path is None:
            click.echo(
                f"Branch '{parent_branch}' is the parent branch but has no worktree.\n"
                f"To create a worktree for it, run:\n"
                f"  workstack create {parent_branch}",
                err=True,
            )
            raise SystemExit(1)
        return parent_branch


def complete_worktree_names(
    ctx: click.Context, param: click.Parameter | None, incomplete: str
) -> list[str]:
    """Shell completion for worktree names. Includes 'root' for the repository root.

    This is a shell completion function, which is an acceptable error boundary.
    Exceptions are caught to provide graceful degradation - if completion fails,
    we return an empty list rather than breaking the user's shell experience.

    Args:
        ctx: Click context
        param: Click parameter (unused, but required by Click's completion protocol)
        incomplete: Partial input string to complete
    """
    try:
        # During shell completion, ctx.obj may be None if the CLI group callback
        # hasn't run yet. Create a default context in this case.
        workstack_ctx = ctx.find_root().obj
        if workstack_ctx is None:
            workstack_ctx = create_context(dry_run=False)

        repo = discover_repo_context(workstack_ctx, workstack_ctx.cwd)

        names = ["root"] if "root".startswith(incomplete) else []

        if repo.workstacks_dir.exists():
            names.extend(
                p.name
                for p in repo.workstacks_dir.iterdir()
                if p.is_dir() and p.name.startswith(incomplete)
            )

        return names
    except Exception:
        # Shell completion error boundary: return empty list for graceful degradation
        return []


@click.command("switch")
@click.argument("name", metavar="NAME", required=False, shell_complete=complete_worktree_names)
@click.option(
    "--script", is_flag=True, help="Print only the activation script without usage instructions."
)
@click.option(
    "--up", is_flag=True, help="Move to child branch in Graphite stack (requires Graphite)."
)
@click.option(
    "--down", is_flag=True, help="Move to parent branch in Graphite stack (requires Graphite)."
)
@click.pass_obj
def switch_cmd(ctx: WorkstackContext, name: str | None, script: bool, up: bool, down: bool) -> None:
    """Switch to a worktree and activate its environment.

    With shell integration (recommended):
      workstack switch NAME
      workstack switch --up
      workstack switch --down

    The shell wrapper function automatically activates the worktree.
    Run 'workstack init --shell' to set up shell integration.

    Without shell integration:
      source <(workstack switch NAME --script)

    NAME can be a worktree name, or 'root' to switch to the root repo.
    Use --up to navigate to the child branch in the Graphite stack.
    Use --down to navigate to the parent branch in the Graphite stack.
    This will cd to the worktree, create/activate .venv, and load .env variables.
    """

    # Validate command arguments
    if up and down:
        click.echo("Error: Cannot use both --up and --down", err=True)
        raise SystemExit(1)

    if name and (up or down):
        click.echo("Error: Cannot specify NAME with --up or --down", err=True)
        raise SystemExit(1)

    if not name and not up and not down:
        click.echo("Error: Must specify NAME, --up, or --down", err=True)
        raise SystemExit(1)

    # Check Graphite requirement for --up/--down
    if up or down:
        _ensure_graphite_enabled(ctx)

    repo = discover_repo_context(ctx, ctx.cwd)
    trunk_branch = read_trunk_from_pyproject(repo.root)

    # Check if user is trying to switch to main/master (should use root instead)
    if name and name.lower() in ("main", "master"):
        click.echo(
            f'Error: "{name}" cannot be used as a worktree name.\n'
            f"To switch to the {name} branch in the root repository, use:\n"
            f"  workstack switch root",
            err=True,
        )
        raise SystemExit(1)

    # Determine target name based on command arguments
    target_name: str
    if up or down:
        # Get current branch
        current_branch = ctx.git_ops.get_current_branch(ctx.cwd)
        if current_branch is None:
            click.echo("Error: Not currently on a branch (detached HEAD)", err=True)
            raise SystemExit(1)

        # Get all worktrees for checking if target has a worktree
        worktrees = ctx.git_ops.list_worktrees(repo.root)

        if up:
            target_name = _resolve_up_navigation(ctx, repo, current_branch, worktrees)
        else:  # down
            target_name = _resolve_down_navigation(
                ctx, repo, current_branch, worktrees, trunk_branch
            )

        # Check if target_name refers to 'root' which means root repo
        if target_name == "root":
            _activate_root_repo(repo, script, "switch")

        # Resolve to actual worktree path
        target_wt_path = ctx.git_ops.find_worktree_for_branch(repo.root, target_name)
        if target_wt_path is None:
            click.echo(
                f"Error: Branch '{target_name}' has no worktree. This should not happen.",
                err=True,
            )
            raise SystemExit(1)

        _activate_worktree(repo, target_wt_path, script, "switch")
    else:
        # NAME argument was provided (validated earlier)
        target_name = name if name else ""  # This branch is unreachable due to validation

        # Check if target_name refers to 'root' which means root repo
        if target_name == "root":
            _activate_root_repo(repo, script, "switch")

        # For explicit name, use worktree_path_for since user provided the worktree name
        workstacks_dir = ensure_workstacks_dir(repo)
        wt_path = worktree_path_for(workstacks_dir, target_name)

        _activate_worktree(repo, wt_path, script, "switch")
