"""Utilities for running subprocesses with better error reporting."""

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
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command with improved error reporting.

    Args:
        cmd: Command to run as a list of strings
        cwd: Working directory for the command
        error_prefix: Prefix for error message
        troubleshooting: Optional list of troubleshooting suggestions

    Returns:
        CompletedProcess if successful

    Raises:
        SystemExit: If command fails (after displaying user-friendly error)
    """
    result = subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)

    if result.returncode != 0:
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
