# Plan: Add Ensure usage to retry_cmd.py

## Goal
Refactor `retry_cmd.py` to use `Ensure.invariant()` for issue validation checks.

## Current Code (lines 74-81)
```python
# Validate issue state (LBYL pattern)
if issue.state != "OPEN":
    user_output(click.style("Error: ", fg="red") + "Cannot retry closed plan")
    raise SystemExit(1)

if ERK_PLAN_LABEL not in issue.labels:
    user_output(click.style("Error: ", fg="red") + "Issue is not an erk plan")
    raise SystemExit(1)
```

## Changes

### 1. Add import for Ensure
Add `from erk.cli.ensure import Ensure` to imports.

### 2. Replace manual checks with Ensure.invariant()
Replace lines 74-81 with:
```python
# Validate issue state (LBYL pattern)
Ensure.invariant(issue.state == "OPEN", "Cannot retry closed plan")
Ensure.invariant(ERK_PLAN_LABEL in issue.labels, "Issue is not an erk plan")
```

## Files to modify
- `src/erk/cli/commands/plan/retry_cmd.py`

## Benefits
- Consistent error handling style matching the rest of the codebase
- Reduces boilerplate (6 lines → 3 lines)
- Uses established `Ensure` pattern already used elsewhere (e.g., `goto_cmd.py:82-84`)