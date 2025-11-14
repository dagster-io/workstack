"""Error boundary handling for CLI commands.

This module provides decorators to catch well-known exceptions at CLI entry points
and display clean error messages without stack traces.
"""

import functools
import traceback
from collections.abc import Callable
from typing import Any, TypeVar

import click

from dot_agent_kit.cli.output import user_output
from dot_agent_kit.sources.exceptions import DotAgentNonIdealStateException

F = TypeVar("F", bound=Callable[..., Any])


def cli_error_boundary[T: Callable[..., Any]](func: T) -> T:
    """Decorator that catches all exceptions and displays appropriate error messages.

    This decorator should be applied to CLI command entry points to provide
    user-friendly error messages. It distinguishes between:
    - DotAgentNonIdealStateException and subclasses: Shows clean error messages
    - External/unexpected exceptions: Shows "internal error" with hint to use --debug
    - Debug mode: Shows full stack traces for any exception

    The debug flag is accessed from the Click context object.

    Example:
        @click.command()
        @cli_error_boundary
        def my_command():
            ...
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Get the current Click context to check debug flag
        ctx = click.get_current_context(silent=True)
        debug = False
        if ctx and ctx.obj and "debug" in ctx.obj:
            debug = ctx.obj["debug"]

        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Check if debug mode is enabled
            if debug:
                # In debug mode, show full traceback for any exception
                user_output(traceback.format_exc())
                raise SystemExit(1) from None

            # Check if this is a custom DotAgentNonIdealStateException
            if isinstance(e, DotAgentNonIdealStateException):
                # Custom exceptions get clean error messages
                user_output(f"Error: {e}")
            else:
                # External/unexpected exceptions show internal error hint
                user_output(
                    f"Internal error: {type(e).__name__}. Run with --debug for full details."
                )

            raise SystemExit(1) from None

    return wrapper  # type: ignore[return-value]
