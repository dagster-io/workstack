# Convert SystemExit to Ensure Call

## Task
Find one SystemExit check in `src/erk/cli/commands/` and convert it to use the appropriate `Ensure` method.

## Selected Candidate
**File**: `src/erk/cli/commands/wt/current_cmd.py:28-29`

**Current code**:
```python
wt_info = find_current_worktree(worktrees, current_dir)

if wt_info is None:
    raise SystemExit(1)
```

## Analysis
This check verifies that the user is currently in a git worktree. When `find_current_worktree()` returns `None`, it means the current directory is not within any worktree.

The `Ensure` class already has a method designed for exactly this scenario:
- `Ensure.in_git_worktree(ctx, current_path)` at line 199-218
- Takes a `Path | None` parameter
- Exits with a user-friendly error: "Not in a git worktree - Run this command from within a worktree directory"

## Implementation Plan

### Step 1: Add Ensure import
Add `from erk.cli.ensure import Ensure` to the imports section.

### Step 2: Replace the check using Option A
The current code structure is:
```python
wt_info = find_current_worktree(worktrees, current_dir)
if wt_info is None:
    raise SystemExit(1)
```

Use the existing pattern with `get_worktree_path()`:
```python
current_wt_path = ctx.git.get_worktree_path(repo.root, current_dir)
Ensure.in_git_worktree(ctx, current_wt_path)
wt_info = find_current_worktree(worktrees, current_dir)
```

### Rationale for Option A
1. Uses the dedicated `Ensure.in_git_worktree()` method designed for this validation
2. Consistent with the semantic meaning of the check - it validates being in a worktree
3. Leverages the Ensure class's standard error messaging
4. The additional `get_worktree_path()` call is negligible overhead

## Files to Modify
- `src/erk/cli/commands/wt/current_cmd.py`
  - Line 7: Add `Ensure` import
  - Lines 24-29: Add `get_worktree_path()` call and replace the None check with `Ensure.in_git_worktree()`