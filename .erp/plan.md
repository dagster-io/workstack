# Plan: Implement `Ensure.not_none[T]` Method

## Overview

Add a new `Ensure.not_none[T](value: T | None, error_message: str) -> T` method that provides type-narrowing None checks with consistent error handling, then apply it across the codebase.

## Implementation

### Step 1: Add `not_none[T]` to Ensure class

**File:** `src/erk/cli/ensure.py`

Add after the existing `truthy[T]` method (after line 62):

```python
@staticmethod
def not_none[T](value: T | None, error_message: str) -> T:
    """Ensure value is not None, otherwise output styled error and exit.

    This method provides type narrowing: if the input is T | None,
    the return type is T (guaranteed non-None).

    Args:
        value: Value to check for None
        error_message: Error message to display if value is None.
                      "Error: " prefix will be added automatically in red.

    Returns:
        The value unchanged if not None (type-narrowed to T)

    Raises:
        SystemExit: If value is None (with exit code 1)

    Example:
        >>> # Type narrows from str | None to str
        >>> branch = Ensure.not_none(
        ...     ctx.git.get_current_branch(ctx.cwd),
        ...     "HEAD is detached (not on a branch)"
        ... )
    """
    if value is None:
        user_output(click.style("Error: ", fg="red") + error_message)
        raise SystemExit(1)
    return value
```

### Step 2: Add Unit Test

**File:** `tests/cli/test_ensure.py` (new file)

```python
"""Tests for Ensure class validation methods."""

import pytest
from erk.cli.ensure import Ensure


def test_not_none_returns_value_when_not_none() -> None:
    """not_none returns the value unchanged when it's not None."""
    result = Ensure.not_none("hello", "should not fail")
    assert result == "hello"


def test_not_none_preserves_type() -> None:
    """not_none preserves the type of the input value."""
    value: int | None = 42
    result = Ensure.not_none(value, "should not fail")
    # Type checker should see result as int, not int | None
    assert result + 1 == 43


def test_not_none_raises_system_exit_when_none() -> None:
    """not_none raises SystemExit(1) when value is None."""
    with pytest.raises(SystemExit) as exc_info:
        Ensure.not_none(None, "value was None")
    assert exc_info.value.code == 1
```

### Step 3: Apply to Codebase

Replace inline None checks with `Ensure.not_none()` in these locations:

#### `src/erk/cli/commands/up.py`
- Line 48-50: `current_branch` check
- Line 78-83: `current_worktree_path` check
- Line 103-109: `target_wt_path` check

#### `src/erk/cli/commands/down.py`
- Line 51-53: `current_branch` check
- Line 60-65: `current_worktree_path` check
- Line 118-124: `target_wt_path` check

#### `src/erk/cli/commands/wt/create_cmd.py`
- Line 609-612: `current_branch` check (--from-current-branch)
- Line 762-765: `current_branch` check

#### `src/erk/cli/commands/navigation_helpers.py`
- Line 246-254: `parent_branch` check

#### `src/erk/cli/commands/runs.py`
- Line 97-100: `current_branch` check

## Example Transformation

**Before:**
```python
current_branch = ctx.git.get_current_branch(ctx.cwd)
if current_branch is None:
    user_output("Error: Not currently on a branch (detached HEAD)")
    raise SystemExit(1)
```

**After:**
```python
current_branch = Ensure.not_none(
    ctx.git.get_current_branch(ctx.cwd),
    "Not currently on a branch (detached HEAD)"
)
```

## Files to Modify

1. `src/erk/cli/ensure.py` - Add method
2. `tests/cli/test_ensure.py` - Add tests (new file)
3. `src/erk/cli/commands/up.py` - 3 replacements
4. `src/erk/cli/commands/down.py` - 3 replacements
5. `src/erk/cli/commands/wt/create_cmd.py` - 2 replacements
6. `src/erk/cli/commands/navigation_helpers.py` - 1 replacement
7. `src/erk/cli/commands/runs.py` - 1 replacement

## Verification

1. Run `uv run pyright` to verify type narrowing works correctly
2. Run `uv run pytest tests/cli/test_ensure.py` for new tests
3. Run `uv run pytest` for full test suite
