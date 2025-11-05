"""Error boundary handling for CLI commands.

This module provides decorators to catch well-known exceptions at CLI entry points
and display clean error messages without stack traces.
"""

import functools
from collections.abc import Callable
from typing import Any, TypeVar

import click

F = TypeVar("F", bound=Callable[..., Any])


def cli_error_boundary[T: Callable[..., Any]](func: T) -> T:
    """Decorator that catches well-known exceptions and displays clean error messages.

    This decorator should be applied to CLI command entry points to provide
    user-friendly error messages without stack traces for predictable error conditions.

    Catches:
        - FileExistsError: File/directory conflicts
        - FileNotFoundError: Missing files/directories
        - ValueError: Invalid input or configuration
        - PermissionError: Permission denied errors

    All other exceptions bubble up normally with full stack traces.

    Example:
        @click.command()
        @cli_error_boundary
        def my_command():
            ...
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except FileExistsError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1) from None
        except FileNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1) from None
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1) from None
        except PermissionError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1) from None

    return wrapper  # type: ignore[return-value]
