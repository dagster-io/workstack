"""Type definitions for GT kit operations."""

from typing import NamedTuple


class CommandResult(NamedTuple):
    """Result from running a subprocess command.

    Attributes:
        success: True if command exited with code 0, False otherwise
        stdout: Standard output from the command
        stderr: Standard error from the command
    """

    success: bool
    stdout: str
    stderr: str
