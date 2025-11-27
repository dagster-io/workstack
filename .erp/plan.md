# Plan: Convert Silent Failure to Ensure.not_none in current_cmd.py

## Target File
`src/erk/cli/commands/wt/current_cmd.py`

## Current Code (lines 26-29)
```python
wt_info = find_current_worktree(worktrees, current_dir)

if wt_info is None:
    raise SystemExit(1)
```

**Problem:** Silent failure - user gets exit code 1 with no explanation.

## Proposed Change
```python
from erk.cli.ensure import Ensure

wt_info = Ensure.not_none(
    find_current_worktree(worktrees, current_dir),
    "Not in a worktree - Run this command from within a worktree directory"
)
```

## Benefits
1. **User-friendly error** - Shows red "Error: " prefix with explanation
2. **Type narrowing** - `wt_info` is guaranteed `WorktreeInfo` (not `WorktreeInfo | None`)
3. **Consistent pattern** - Matches other CLI commands using Ensure

## Implementation Steps

1. Add import: `from erk.cli.ensure import Ensure`
2. Replace lines 26-29 with single `Ensure.not_none()` call
3. Run tests to verify behavior