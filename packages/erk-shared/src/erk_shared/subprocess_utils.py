"""Simple subprocess utilities for erk-shared.

This module provides basic subprocess execution for GitHub CLI commands.
It's intentionally minimal to avoid pulling in complex dependencies.
"""

import subprocess
from pathlib import Path


def execute_gh_command(cmd: list[str], cwd: Path) -> str:
    """Execute a gh CLI command and return stdout.

    Args:
        cmd: Command and arguments to execute
        cwd: Working directory for command execution

    Returns:
        stdout from the command

    Raises:
        RuntimeError: If command fails with enriched error context
        FileNotFoundError: If gh is not installed
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        cmd_str = " ".join(cmd)
        error_msg = f"Failed to execute gh command '{cmd_str}'"
        if e.stderr:
            error_msg += f": {e.stderr.strip()}"
        raise RuntimeError(error_msg) from e
    except FileNotFoundError as e:
        cmd_str = " ".join(cmd)
        error_msg = f"Command not found: {cmd_str}"
        raise RuntimeError(error_msg) from e
