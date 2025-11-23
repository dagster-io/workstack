"""Retry logic with exponential backoff for transient failures.

This module provides a retry decorator for handling transient failures in
network operations, particularly GitHub API calls that may fail due to:
- Network timeouts
- Rate limiting
- Temporary API unavailability
- Connection issues

The decorator implements exponential backoff to avoid overwhelming services
with rapid retries.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import click

# Type variable for decorated function return type
T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    *,
    backoff_factor: float = 2.0,
    ctx: Any = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry function with exponential backoff for transient failures.

    Retries the decorated function up to max_attempts times with exponentially
    increasing delays between attempts. On the final attempt, the exception
    is re-raised to the caller.

    Supports two usage patterns:
    1. Function with ctx parameter: Decorator extracts ctx.time from first arg
    2. Closure function: Pass ctx explicitly to decorator

    Delay calculation: delay = base_delay * (backoff_factor ** attempt)
    Example with defaults: 1s, 2s, 4s for attempts 0, 1, 2

    Args:
        max_attempts: Maximum number of attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
        ctx: Optional ErkContext for closure functions (default: None)

    Returns:
        Decorator function that wraps the target function with retry logic

    Example (function with ctx parameter):
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        def fetch_pr_base(ctx: ErkContext, pr_number: int) -> str:
            return github_api.get_pr_base(pr_number)

    Example (closure function):
        def outer(ctx: ErkContext) -> None:
            @retry_with_backoff(max_attempts=3, base_delay=1.0, ctx=ctx)
            def inner() -> str:
                return ctx.github.get_pr_base(123)

    Raises:
        Exception: Re-raises the last exception after max_attempts exhausted
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Extract ErkContext - either from decorator parameter or first argument
            # Inline import: Avoid circular dependency with context module
            from erk.core.context import ErkContext

            context: ErkContext
            if ctx is not None:
                # Closure function: ctx provided to decorator
                context = ctx
            elif len(args) > 0 and isinstance(args[0], ErkContext):
                # Function with ctx parameter: extract from first arg
                context = args[0]
            else:
                msg = (
                    f"Function {func.__name__} must either take ErkContext "
                    "as first parameter or decorator must receive ctx"
                )
                raise TypeError(msg)

            last_exception: Exception | None = None

            for attempt in range(max_attempts):
                # Add delay before retry (skip on first attempt)
                if attempt > 0:
                    # Calculate delay with exponential backoff
                    delay = base_delay * (backoff_factor ** (attempt - 1))
                    click.echo(
                        f"Retrying after {delay:.1f}s (attempt {attempt + 1}/{max_attempts})...",
                        err=True,
                    )
                    context.time.sleep(delay)

                # Attempt to execute the function
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    # Check if this is the last attempt
                    is_last_attempt = attempt == max_attempts - 1
                    if is_last_attempt:
                        # Re-raise on last attempt
                        raise

                    # Not the last attempt - log and continue to retry
                    click.echo(
                        f"Operation failed: {last_exception}",
                        err=True,
                    )

            # Should never reach here due to raise in loop, but satisfy type checker
            if last_exception is not None:
                raise last_exception
            msg = f"Function {func.__name__} completed without result or exception"
            raise RuntimeError(msg)

        return wrapper

    return decorator
