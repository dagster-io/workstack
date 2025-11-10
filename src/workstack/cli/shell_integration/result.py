"""Shell integration result helpers for command completion.

This module provides centralized activation helpers that encapsulate:
- Script generation (activation or simple cd)
- Temp file writing
- Output routing (script path in script mode, instructions in normal mode)
- Success exit (SystemExit(0))

These helpers eliminate boilerplate across shell-integrated commands.
"""

from pathlib import Path

import click

from workstack.cli.activation import render_activation_script
from workstack.cli.debug import debug_log
from workstack.cli.shell_utils import render_cd_script, write_script_to_temp
from workstack.core.repo_discovery import RepoContext


def activate_root_repo(repo: RepoContext, script: bool, command_name: str) -> None:
    """Activate the root repository and exit successfully.

    Generates activation script for root repo, outputs script path in script mode
    or usage instructions in normal mode, then exits with success (SystemExit(0)).

    Args:
        repo: Repository context
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation)

    Raises:
        SystemExit: Always (successful exit code 0 after activation)
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


def activate_worktree(
    repo: RepoContext, target_path: Path, script: bool, command_name: str
) -> None:
    """Activate a worktree and exit successfully.

    Verifies worktree exists, generates activation script, outputs script path
    in script mode or usage instructions in normal mode, then exits with
    success (SystemExit(0)).

    Args:
        repo: Repository context
        target_path: Path to the target worktree directory
        script: Whether to output script path or user message
        command_name: Name of the command (for script generation and debug logging)

    Raises:
        SystemExit: If worktree not found (exit code 1), or after successful
                   activation (exit code 0)
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


def finish_with_cd(
    target_path: Path, script: bool, command_name: str, *, success_message: str
) -> None:
    """Finish command by changing directory (without full activation).

    Generates simple cd script (no venv activation, no .env loading),
    outputs script path in script mode, then exits successfully.

    Used by commands like 'create' that just need to cd to the worktree
    without full activation setup.

    Args:
        target_path: Path to target directory
        script: Whether to output script path
        command_name: Name of the command (for script generation)
        success_message: Message to display after cd

    Raises:
        SystemExit: Always (successful exit code 0)
    """
    if script:
        script_content = render_cd_script(
            target_path,
            comment=f"cd to {target_path.name}",
            success_message=success_message,
        )
        script_path = write_script_to_temp(
            script_content,
            command_name=command_name,
            comment=f"cd to {target_path.name}",
        )
        click.echo(str(script_path), nl=False)
    raise SystemExit(0)


def finish_with_activation(
    target_path: Path,
    script: bool,
    command_name: str,
    *,
    final_message: str,
) -> None:
    """Finish command with full worktree activation.

    Generates activation script (cd + venv + .env), outputs script path
    in script mode, then exits successfully.

    Used by commands like 'jump' that need full activation when completing.

    Args:
        target_path: Path to target worktree
        script: Whether to output script path
        command_name: Name of the command (for script generation)
        final_message: Shell command for final echo message

    Raises:
        SystemExit: Always (successful exit code 0)
    """
    if script:
        script_content = render_activation_script(
            worktree_path=target_path,
            final_message=final_message,
        )
        script_path = write_script_to_temp(
            script_content,
            command_name=command_name,
            comment=f"activate {target_path.name}",
        )
        click.echo(str(script_path), nl=False)
    raise SystemExit(0)


def emit_activation_script(
    worktree_path: Path,
    command_name: str,
    *,
    final_message: str = "",
    comment: str = "",
) -> None:
    """Generate activation script, write to temp file, and emit path.

    This helper encapsulates the common pattern of:
    1. Generating activation script with render_activation_script()
    2. Writing it to a temp file with write_script_to_temp()
    3. Emitting the path with emit_script_path()

    Used by long-running commands (sync, consolidate, land-stack) that need to
    generate and emit activation scripts after completing their work.

    Args:
        worktree_path: Path to the worktree to activate
        command_name: Name of the command (for script generation)
        final_message: Shell command for final echo message (optional)
        comment: Comment for script metadata (optional)

    Example:
        >>> emit_activation_script(
        ...     worktree_path=repo.root,
        ...     command_name="sync",
        ...     final_message='echo "✓ Switched to root"',
        ...     comment="return to root",
        ... )
        # Outputs: /tmp/workstack-sync-abc123.sh (no trailing newline)
    """
    script_content = render_activation_script(
        worktree_path=worktree_path,
        final_message=final_message,
        comment=comment,
    )
    script_path = write_script_to_temp(
        script_content,
        command_name=command_name,
        comment=comment or f"activate {worktree_path.name}",
    )
    emit_script_path(script_path)


def emit_script_path(script_path: Path) -> None:
    """Emit script path to stdout without newline for shell wrapper capture.

    This function standardizes the pattern of outputting a script path so that
    the shell wrapper can capture it cleanly. The absence of a newline (nl=False)
    is critical for proper shell wrapper functionality.

    Used by long-running commands (consolidate, sync, land-stack) that generate
    activation scripts at the end of their execution.

    Args:
        script_path: Path to the temp script file to emit

    Example:
        >>> script_path = write_script_to_temp(...)
        >>> emit_script_path(script_path)
        # Outputs: /tmp/workstack-sync-abc123.sh (no trailing newline)
    """
    click.echo(str(script_path), nl=False)
