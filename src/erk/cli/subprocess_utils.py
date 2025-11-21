"""Utilities for running subprocesses with better error reporting.

This module provides CLI-layer subprocess execution with user-friendly error output.

For integration layer subprocess calls (raises RuntimeError), use:
    from erk.core.subprocess import run_subprocess_with_context

For CLI-layer subprocess calls (prints message, raises SystemExit), use:
    from erk.cli.subprocess_utils import run_with_error_reporting (this module)
"""

import subprocess
from collections.abc import Sequence
from pathlib import Path

from erk.cli.output import user_output


def run_with_error_reporting(
    cmd: Sequence[str],
    *,
    cwd: Path | None = None,
    error_prefix: str = "Command failed",
    troubleshooting: list[str] | None = None,
    show_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run subprocess command with user-friendly error reporting for CLI layer.

    This function is designed for CLI commands that need to display error messages
    directly to users and exit the program. For integration layer code that needs
    to raise exceptions with context, use run_subprocess_with_context() instead.

    Args:
        cmd: Command to run as a list of strings
        cwd: Working directory for the command
        error_prefix: Prefix for error message
        troubleshooting: Optional list of troubleshooting suggestions
        show_output: If True, show stdout/stderr in real-time (default: False)

    Returns:
        CompletedProcess if successful

    Raises:
        SystemExit: If command fails (after displaying user-friendly error)

    Example:
        >>> run_with_error_reporting(
        ...     ["gh", "pr", "view", "123"],
        ...     cwd=repo_root,
        ...     error_prefix="Failed to view PR",
        ...     troubleshooting=["Ensure gh is installed", "Run 'gh auth login'"]
        ... )

    Notes:
        - This is for CLI-layer code (commands that interact with users)
        - For integration layer code, use run_subprocess_with_context() instead
        - Uses check=False and manually handles errors for user-friendly output
        - Displays stderr/stdout to user before raising SystemExit
        - When show_output=True, output streams directly to terminal
    """
    result = subprocess.run(cmd, cwd=cwd, check=False, capture_output=not show_output, text=True)

    if result.returncode != 0:
        # When show_output=True, output already displayed, only show error context
        if show_output:
            message_parts = [
                f"Error: {error_prefix}.\n",
                f"Command: {' '.join(cmd)}",
                f"Exit code: {result.returncode}\n",
            ]
        else:
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()

            # Build error message
            message_parts = [
                f"Error: {error_prefix}.\n",
                f"Command: {' '.join(cmd)}",
                f"Exit code: {result.returncode}\n",
            ]

            if error_msg:
                message_parts.append(f"Output:\n{error_msg}\n")

        if troubleshooting:
            message_parts.append("Troubleshooting:")
            for tip in troubleshooting:
                message_parts.append(f"  • {tip}")

        user_output("\n".join(message_parts))
        raise SystemExit(1)

    return result
