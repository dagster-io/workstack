"""Tests for retry decorator with exponential backoff."""

from erk.cli.commands.land_stack.retry import retry_with_backoff
from erk.core.context import ErkContext


def test_retry_succeeds_on_first_attempt() -> None:
    """Test that retry decorator returns immediately on success."""
    ctx = ErkContext.for_test()
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.01, ctx=ctx)
    def successful_function() -> str:
        nonlocal call_count
        call_count += 1
        return "success"

    result = successful_function()

    assert result == "success"
    assert call_count == 1  # Should only call once


def test_retry_succeeds_on_second_attempt() -> None:
    """Test that retry decorator retries and succeeds on second attempt."""
    ctx = ErkContext.for_test()
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.01, ctx=ctx)
    def fails_once() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Network error")
        return "success"

    result = fails_once()

    assert result == "success"
    assert call_count == 2  # Should retry once


def test_retry_raises_after_max_attempts() -> None:
    """Test that retry decorator raises exception after exhausting retries."""
    ctx = ErkContext.for_test()
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.01, ctx=ctx)
    def always_fails() -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("Always fails")

    # Should raise after 3 attempts
    exception_raised = False
    try:
        always_fails()
    except ValueError as e:
        exception_raised = True
        assert str(e) == "Always fails"

    assert exception_raised, "Should raise ValueError after max attempts"
    assert call_count == 3  # Should try 3 times


def test_retry_with_custom_backoff_factor() -> None:
    """Test that retry decorator uses custom backoff factor."""
    ctx = ErkContext.for_test()
    call_count = 0

    @retry_with_backoff(max_attempts=3, base_delay=0.01, backoff_factor=3.0, ctx=ctx)
    def fails_twice() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("Not yet")
        return "success"

    result = fails_twice()

    assert result == "success"
    assert call_count == 3  # Should succeed on third attempt


def test_retry_preserves_function_metadata() -> None:
    """Test that retry decorator preserves function name and docstring."""
    ctx = ErkContext.for_test()

    @retry_with_backoff(max_attempts=3, ctx=ctx)
    def documented_function() -> str:
        """This is a documented function."""
        return "result"

    # Check that functools.wraps preserved metadata
    assert documented_function.__name__ == "documented_function"
    assert documented_function.__doc__ == "This is a documented function."
