# Plan: Optimize `erk wt list` Performance

## Problem

`erk wt list` takes 2-5 seconds visually, but Python profiling shows only ~50ms. The disconnect is caused by **subprocess spawning overhead** not captured in Python CPU profiling.

### Root Cause Analysis

Current implementation in `list_cmd.py` makes sequential subprocess calls:

| Operation | Subprocess Calls | Per Worktree |
|-----------|-----------------|--------------|
| `list_worktrees()` | 1 | No (once) |
| `_get_sync_status()` → `get_ahead_behind()` | 2 | Yes |
| `_get_impl_issue()` → `get_current_branch()` | 1 | Yes |
| `_get_impl_issue()` → `get_branch_issue()` | 1 | Yes |

**With 5 worktrees:** 1 + (4 × 5) = **21 subprocess calls**

Each subprocess spawn on macOS takes ~100-200ms, totaling **2-4 seconds**.

## Solution: Batch Git Commands with `git for-each-ref`

Replace per-worktree `get_ahead_behind()` calls with a **single** `git for-each-ref` call that fetches all branch tracking info at once:

```bash
git for-each-ref --format='%(refname:short)	%(upstream:short)	%(upstream:track)' refs/heads/
```

Output example:
```
feature-1	origin/feature-1	[ahead 3, behind 1]
feature-2	origin/feature-2
main	origin/main
```

This parses to provide: branch name, upstream (or None), and ahead/behind counts.

### Performance Impact

| Metric | Before | After |
|--------|--------|-------|
| Sync status calls | 2 × N worktrees | **1 total** |
| Total subprocess calls (5 wt) | ~21 | ~6 |
| Expected time | 2-4s | 600ms-1s |
| **Improvement** | - | **3-5x faster** |

## Implementation Steps

### Step 1: Add `BranchSyncInfo` dataclass to Git ABC

**File:** `packages/erk-shared/src/erk_shared/git/abc.py`

Add dataclass after existing `WorktreeInfo`:

```python
@dataclass(frozen=True)
class BranchSyncInfo:
    """Sync status for a branch relative to its upstream."""
    branch: str
    upstream: str | None  # None if no tracking branch
    ahead: int
    behind: int
```

### Step 2: Add `get_all_branch_sync_info()` abstract method

**File:** `packages/erk-shared/src/erk_shared/git/abc.py`

Add after `get_ahead_behind()` method:

```python
@abstractmethod
def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
    """Get sync status for all local branches in a single git call.

    Uses git for-each-ref to batch-fetch upstream tracking information.

    Returns:
        Dict mapping branch name to BranchSyncInfo.
    """
    ...
```

### Step 3: Implement in `RealGit`

**File:** `packages/erk-shared/src/erk_shared/git/real.py`

```python
def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
    """Get sync status for all local branches via git for-each-ref."""
    result = subprocess.run(
        [
            "git", "for-each-ref",
            "--format=%(refname:short)\t%(upstream:short)\t%(upstream:track)",
            "refs/heads/",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return {}

    sync_info: dict[str, BranchSyncInfo] = {}
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        branch = parts[0]
        upstream = parts[1] if len(parts) > 1 and parts[1] else None
        track = parts[2] if len(parts) > 2 else ""

        ahead, behind = 0, 0
        if track:
            # Parse "[ahead N, behind M]" or "[ahead N]" or "[behind M]"
            ahead_match = re.search(r'ahead (\d+)', track)
            behind_match = re.search(r'behind (\d+)', track)
            if ahead_match:
                ahead = int(ahead_match.group(1))
            if behind_match:
                behind = int(behind_match.group(1))

        sync_info[branch] = BranchSyncInfo(
            branch=branch,
            upstream=upstream,
            ahead=ahead,
            behind=behind,
        )

    return sync_info
```

### Step 4: Implement in `FakeGit`

**Files:**
- `src/erk/core/git/fake.py`
- `tests/fakes/git.py`

Add configurable return value and implementation:

```python
# In __init__:
self._branch_sync_info: dict[str, BranchSyncInfo] = branch_sync_info or {}

# Method:
def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
    return self._branch_sync_info.copy()
```

### Step 5: Add pass-through in wrapper classes

**Files:**
- `src/erk/core/git/printing.py`
- `src/erk/core/git/dry_run.py`

```python
def get_all_branch_sync_info(self, repo_root: Path) -> dict[str, BranchSyncInfo]:
    return self._wrapped.get_all_branch_sync_info(repo_root)
```

### Step 6: Refactor `list_cmd.py` to use batch API

**File:** `src/erk/cli/commands/wt/list_cmd.py`

1. Add helper function:

```python
def _format_sync_from_batch(
    all_sync: dict[str, BranchSyncInfo],
    branch: str | None
) -> str:
    """Format sync status from batch-fetched data."""
    if branch is None:
        return "-"

    info = all_sync.get(branch)
    if info is None:
        return "-"

    if info.ahead == 0 and info.behind == 0:
        return "current"

    parts = []
    if info.ahead > 0:
        parts.append(f"{info.ahead}↑")
    if info.behind > 0:
        parts.append(f"{info.behind}↓")
    return " ".join(parts)
```

2. In `_list_worktrees()`, fetch all sync info once after getting worktrees:

```python
# After line 146 (worktrees = ctx.git.list_worktrees(repo.root))
all_sync_info = ctx.git.get_all_branch_sync_info(repo.root)
```

3. Replace `_get_sync_status()` calls with `_format_sync_from_batch()`:

```python
# Line 196: Replace _get_sync_status(ctx, repo.root, root_branch)
root_sync = _format_sync_from_batch(all_sync_info, root_branch)

# Line 227: Replace _get_sync_status(ctx, wt.path, branch)
sync_cell = _format_sync_from_batch(all_sync_info, branch)
```

### Step 7: Optimize `_get_impl_issue()` (bonus)

**File:** `src/erk/cli/commands/wt/list_cmd.py`

The function currently calls `get_current_branch()` even though we already know the branch. Add a `branch` parameter:

```python
def _get_impl_issue(
    ctx: ErkContext,
    worktree_path: Path,
    branch: str | None = None,  # Add parameter
) -> tuple[str | None, str | None]:
```

Then pass the known branch to avoid redundant subprocess calls.

## Files to Modify

| File | Changes |
|------|---------|
| `packages/erk-shared/src/erk_shared/git/abc.py` | Add `BranchSyncInfo` dataclass, add abstract method |
| `packages/erk-shared/src/erk_shared/git/real.py` | Implement `get_all_branch_sync_info()` |
| `src/erk/core/git/fake.py` | Add fake implementation |
| `src/erk/core/git/printing.py` | Add pass-through |
| `src/erk/core/git/dry_run.py` | Add pass-through |
| `tests/fakes/git.py` | Add fake implementation |
| `src/erk/cli/commands/wt/list_cmd.py` | Use batch API, optimize `_get_impl_issue()` |

## Testing

1. **Unit test** `_format_sync_from_batch()` with various inputs
2. **Unit test** `get_all_branch_sync_info()` parsing logic
3. **Integration test** with real git repository
4. **Manual verification**: `time erk wt list` before and after

## Edge Cases

- Branch with no upstream tracking → `upstream=None`, show "current"
- Empty repository → returns empty dict, graceful fallback
- Detached HEAD worktrees → branch is None, show "-"
- Git command failure → returns empty dict, falls back gracefully