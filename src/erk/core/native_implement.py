"""Native implementation execution (non-Docker mode).

This module provides native execution of implementation plans by launching
Claude Code CLI directly on the host system (not in a container).

Follows LBYL philosophy: check conditions before acting, let exceptions bubble.
"""

from pathlib import Path

from erk.core.shell import Shell


def execute_native_implementation(shell_ops: Shell, worktree_root: Path) -> int:
    """Execute implementation plan natively on host (main entry point).

    Launches Claude Code CLI programmatically with `/erk:implement-plan` command
    in the current worktree. This runs directly on the host system without Docker.

    LBYL checks:
    - Claude Code CLI available in PATH
    - Worktree has .plan/plan.md

    Args:
        shell_ops: Shell operations interface for running commands
        worktree_root: Root directory of worktree containing plan

    Returns:
        Exit code from Claude Code CLI

    Raises:
        FileNotFoundError: If plan.md missing or claude command not found
        RuntimeError: If Claude Code CLI execution fails
    """
    # LBYL: Check plan exists before launching
    plan_file = worktree_root / ".plan" / "plan.md"
    if not plan_file.exists():
        raise FileNotFoundError(
            f"No plan found: {plan_file}\nRun /erk:persist-plan to create a plan first."
        )

    # LBYL: Check Claude Code CLI available
    claude_path = shell_ops.get_installed_tool_path("claude")
    if claude_path is None:
        raise FileNotFoundError(
            "Claude Code CLI not found in PATH.\nInstall from: https://claude.ai/download"
        )

    # Build command to execute
    command = [
        "claude",
        "--permission-mode",
        "acceptEdits",
        "/erk:implement-plan",
    ]

    # Execute Claude Code CLI via shell ops
    # Don't use check=True - we want to return the actual exit code
    exit_code = shell_ops.run_command(command, cwd=worktree_root)

    return exit_code
