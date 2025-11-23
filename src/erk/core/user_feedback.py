"""User-facing diagnostic output with mode awareness."""

from abc import ABC, abstractmethod

import click

from erk.cli.output import user_output


class UserFeedback(ABC):
    """Provides user-facing diagnostic output that's mode-aware.

    This abstraction eliminates the need to thread 'script' booleans through
    function signatures. Instead, functions call ctx.feedback methods which
    automatically handle output suppression based on the current mode.

    Two modes:
    - Interactive: Show all diagnostics (info, success, errors)
    - Script: Suppress diagnostics, only show errors

    Usage:
        # In command code
        ctx.feedback.info("Starting operation...")
        result = perform_operation()
        ctx.feedback.success("✓ Operation complete")

        # Errors always appear
        if not valid:
            ctx.feedback.error("Error: Invalid configuration")
            raise SystemExit(1)

    Mode behavior:
        Interactive mode (script=False):
            - info() → outputs to stderr
            - success() → outputs to stderr with green styling
            - error() → outputs to stderr with red styling

        Script mode (script=True):
            - info() → suppressed
            - success() → suppressed
            - error() → still outputs to stderr with red styling
    """

    @abstractmethod
    def info(self, message: str) -> None:
        """Show informational message (suppressed in script mode)."""

    @abstractmethod
    def success(self, message: str) -> None:
        """Show success message (suppressed in script mode)."""

    @abstractmethod
    def error(self, message: str) -> None:
        """Show error message (always shown, even in script mode)."""


class InteractiveFeedback(UserFeedback):
    """Feedback shown in interactive mode (all messages)."""

    def info(self, message: str) -> None:
        """Show informational message."""
        user_output(message)

    def success(self, message: str) -> None:
        """Show success message in green."""
        user_output(click.style(message, fg="green"))

    def error(self, message: str) -> None:
        """Show error message in red."""
        user_output(click.style(message, fg="red"))


class SuppressedFeedback(UserFeedback):
    """Feedback suppressed in script mode (only errors shown).

    Used when --script flag is active to keep output clean for
    shell integration handler to parse activation script path.
    """

    def info(self, message: str) -> None:
        """Suppress informational message in script mode."""
        pass

    def success(self, message: str) -> None:
        """Suppress success message in script mode."""
        pass

    def error(self, message: str) -> None:
        """Show error message even in script mode."""
        user_output(click.style(message, fg="red"))
