"""CLI error handling utilities with styled output.

This module provides the Ensure class for asserting invariants in CLI commands
with consistent, user-friendly error messages. All errors use red "Error:" prefix
for visual consistency.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import click

from erk.cli.output import user_output

if TYPE_CHECKING:
    from erk.core.context import ErkContext


class Ensure:
    """Helper class for asserting invariants with consistent error handling."""

    @staticmethod
    def invariant(condition: bool, error_message: str) -> None:
        """Ensure condition is true, otherwise output styled error and exit.

        Args:
            condition: Boolean condition to check
            error_message: Error message to display if condition is false.
                          "Error: " prefix will be added automatically in red.

        Raises:
            SystemExit: If condition is false (with exit code 1)
        """
        if not condition:
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)

    @staticmethod
    def truthy[T](value: T, error_message: str) -> T:
        """Ensure value is truthy, otherwise output styled error and exit.

        Args:
            value: Value to check for truthiness
            error_message: Error message to display if value is falsy.
                          "Error: " prefix will be added automatically in red.

        Returns:
            The value unchanged if truthy

        Raises:
            SystemExit: If value is falsy (with exit code 1)
        """
        if not value:
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)
        return value

    @staticmethod
    def path_exists(
        ctx: "ErkContext",
        path: Path,
        error_message: str | None = None,
    ) -> None:
        """Ensure path exists, otherwise output styled error and exit.

        This method is designed for validating git-managed paths (worktrees, repos).
        It checks path existence before any operations that would fail on missing paths.

        Supports both real filesystem paths and sentinel paths used in tests by using
        ctx.git.path_exists, which works with both real paths and test sentinels.

        Args:
            ctx: Application context with git integration for path checking
            path: Path to check for existence
            error_message: Optional custom error message. If not provided,
                          uses default "Path not found: {path}".
                          "Error: " prefix will be added automatically in red.

        Raises:
            SystemExit: If path does not exist (with exit code 1)

        Example:
            >>> # Basic usage with default error message
            >>> Ensure.path_exists(ctx, config_path)
            >>>
            >>> # With custom error message
            >>> Ensure.path_exists(ctx, wt_path, f"Worktree not found: {wt_path}")
        """
        if not ctx.git.path_exists(path):
            if error_message is None:
                error_message = f"Path not found: {path}"
            user_output(click.style("Error: ", fg="red") + error_message)
            raise SystemExit(1)
