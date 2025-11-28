# Plan: Convert error check in current_cmd.py to use Ensure

## Target
Convert the None check at `src/erk/cli/commands/wt/current_cmd.py:28-29` to use `Ensure.not_none`.

## Current Code
```python
wt_info = find_current_worktree(worktrees, current_dir)

if wt_info is None:
    raise SystemExit(1)
```

## New Code
```python
wt_info = Ensure.not_none(
    find_current_worktree(worktrees, current_dir),
    "Not in an erk worktree"
)
```

## Changes Required

1. **Add import** at top of file:
   ```python
   from erk.cli.ensure import Ensure
   ```

2. **Replace lines 26-29** with the `Ensure.not_none` pattern

## Benefits
- Adds a user-friendly error message (currently exits silently)
- Consistent error styling with red "Error:" prefix
- Follows the established pattern in the codebase