# Refactor plan check_cmd.py to Extract Reusable Helpers

**Issue:** [#1289](https://github.com/dagster-io/erk/issues/1289)

## Summary

Extract the `_parse_identifier()` function from `check_cmd.py` into a shared module, then update `close_cmd.py` and `retry_cmd.py` to use it. This eliminates code duplication across 3 plan commands.

## Background

The identifier parsing logic (parsing issue numbers from strings like "123" or GitHub URLs like "https://github.com/org/repo/issues/123") is duplicated in:

1. `check_cmd.py` - as `_parse_identifier()` (lines 18-41)
2. `close_cmd.py` - inline logic (lines 32-46)
3. `retry_cmd.py` - inline logic (lines 39-61)

Existing codebase pattern: `pr/parse_pr_reference.py` already does this for PR commands.

## Implementation Steps

### Step 1: Create plan_helpers.py module

Create `/Users/schrockn/code/erk/src/erk/cli/commands/plan/plan_helpers.py`:

```python
"""Shared helpers for plan CLI commands."""

from urllib.parse import urlparse


def parse_plan_identifier(identifier: str) -> int:
    """Parse plan identifier from issue number or GitHub URL.

    Args:
        identifier: Either a numeric string ("123") or GitHub issue URL

    Returns:
        The issue number as an integer

    Raises:
        ValueError: If identifier cannot be parsed
    """
    if identifier.isdigit():
        return int(identifier)

    parsed = urlparse(identifier)
    if parsed.hostname != "github.com":
        raise ValueError(f"Invalid GitHub URL: {identifier}")

    if not parsed.path:
        raise ValueError(f"Invalid GitHub URL (no path): {identifier}")

    parts = parsed.path.rstrip("/").split("/")
    if len(parts) < 2 or parts[-2] != "issues":
        raise ValueError(f"Invalid GitHub issue URL: {identifier}")

    try:
        return int(parts[-1])
    except ValueError as e:
        raise ValueError(f"Invalid issue number in URL: {identifier}") from e
```

### Step 2: Update check_cmd.py

- Remove `_parse_identifier()` function (lines 18-41)
- Add import: `from erk.cli.commands.plan.plan_helpers import parse_plan_identifier`
- Update call site to use `parse_plan_identifier(identifier)`

### Step 3: Update close_cmd.py

- Remove inline parsing logic (lines 32-46)
- Add import: `from erk.cli.commands.plan.plan_helpers import parse_plan_identifier`
- Replace inline logic with `parse_plan_identifier(identifier)`

### Step 4: Update retry_cmd.py

- Remove inline parsing logic (lines 39-61)
- Add import: `from erk.cli.commands.plan.plan_helpers import parse_plan_identifier`
- Replace inline logic with `parse_plan_identifier(identifier)`

### Step 5: Add tests

Create `/Users/schrockn/code/erk/tests/unit/cli/commands/plan/test_plan_helpers.py`:

- Test numeric string parsing: `"123"` → `123`
- Test GitHub URL parsing: `"https://github.com/org/repo/issues/456"` → `456`
- Test error cases: invalid URLs, non-GitHub hosts, missing issue number

## Files to Modify

| File | Action |
|------|--------|
| `src/erk/cli/commands/plan/plan_helpers.py` | Create (new module) |
| `src/erk/cli/commands/plan/check_cmd.py` | Remove `_parse_identifier()`, add import |
| `src/erk/cli/commands/plan/close_cmd.py` | Remove inline parsing, add import |
| `src/erk/cli/commands/plan/retry_cmd.py` | Remove inline parsing, add import |
| `tests/unit/cli/commands/plan/test_plan_helpers.py` | Create (new test file) |

## Validation

- Run `uv run pytest tests/unit/cli/commands/plan/` - all tests pass
- Run `uv run pyright src/erk/cli/commands/plan/` - no type errors
- Manual test: `erk plan check 1289` and `erk plan check https://github.com/dagster-io/erk/issues/1289` both work