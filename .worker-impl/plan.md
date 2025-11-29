# Plan: Add Missing Methods to Git ABC (PR 1 of 4)

## Goal

Add 7 methods from `GitGtKit` to the canonical `Git` ABC, with implementations in `RealGit` and `FakeGit`. This is a **purely additive change** that doesn't modify any existing code paths.

## Context

The `GitGtKit` interface in `integrations/gt/abc.py` has methods that duplicate functionality in `Git` but without explicit `Path` parameters. This PR adds the missing methods to `Git` so kit commands can eventually use the canonical interface.

This is **PR 1 of 4** in an incremental consolidation strategy:
- PR 1: Add methods to Git ABC (this PR)
- PR 2: Add methods to Graphite ABC
- PR 3: Add methods to GitHub ABC
- PR 4: Migrate CLI commands and delete `integrations/gt/`

## Methods to Add

| GitGtKit Method | New Git Method | Notes |
|----------------|----------------|-------|
| `add_all()` | `add_all(cwd: Path) -> bool` | Stage all changes |
| `commit(message)` | `commit(cwd: Path, message: str) -> bool` | Create commit |
| `amend_commit(message)` | `amend_commit(cwd: Path, message: str) -> bool` | Amend commit |
| `count_commits_in_branch(parent)` | `count_commits_in_branch(cwd: Path, parent_branch: str) -> int` | Count commits since parent |
| `get_repository_root()` | `get_repository_root(cwd: Path) -> str` | Get repo root path |
| `get_diff_to_parent(parent)` | `get_diff_to_parent(cwd: Path, parent_branch: str) -> str` | Get diff since parent |
| `check_merge_conflicts(base, head)` | `check_merge_conflicts(cwd: Path, base_branch: str, head_branch: str) -> bool` | Check for conflicts |

## Implementation Steps

### Step 1: Add Abstract Methods to Git ABC

**File:** `packages/erk-shared/src/erk_shared/git/abc.py`

Add 7 abstract methods at the end of the `Git` class, following existing patterns.

### Step 2: Implement in RealGit

**File:** `packages/erk-shared/src/erk_shared/git/real.py`

Copy implementations from `RealGitGtKit` in `integrations/gt/real.py`, adding `cwd` parameter to each method.

### Step 3: Implement in FakeGit

**File:** `tests/fakes/git.py`

Add fake implementations with configurable state:
- `_commits: list[str]` - Track commit messages
- `_commit_count: int` - Configurable commit count
- `_diff_output: str` - Configurable diff output
- `_has_merge_conflicts: bool` - Configurable conflict status

### Step 4: Add Unit Tests

**File:** `tests/unit/git/test_git_abc_new_methods.py` (new file)

Test each new method using FakeGit.

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/git/abc.py` | Add 7 abstract methods |
| `packages/erk-shared/src/erk_shared/git/real.py` | Add 7 method implementations |
| `tests/fakes/git.py` | Add 7 fake implementations + 4 new fields |
| `tests/unit/git/test_git_abc_new_methods.py` | New test file |

## Validation

```bash
uv run pyright packages/erk-shared/src/erk_shared/git/
uv run pytest tests/unit/git/ -v
```

## Risk Assessment

**Low Risk** - Purely additive:
- No existing code paths change
- No behavior changes for existing callers
- New methods are unused until PR 4