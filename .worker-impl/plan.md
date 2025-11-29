# Plan: Add Missing Methods to Graphite ABC (PR 2 of 4)

## Goal

Add 4 methods from `GraphiteGtKit` to the canonical `Graphite` ABC, with implementations in `RealGraphite`, `FakeGraphite`, and `DryRunGraphite`. Also add `CommandResult` type. This is a **purely additive change**.

## Context

The `GraphiteGtKit` interface in `integrations/gt/abc.py` has methods for GT kit commands that should be in the canonical `Graphite` ABC. This PR adds them so kit commands can eventually use the canonical interface.

This is **PR 2 of 4** in an incremental consolidation strategy:
- PR 1: Add methods to Git ABC (done)
- PR 2: Add methods to Graphite ABC (this PR)
- PR 3: Add methods to GitHub ABC
- PR 4: Migrate CLI commands and delete `integrations/gt/`

## Methods to Add

| GraphiteGtKit Method | New Graphite Method | Notes |
|---------------------|---------------------|-------|
| `restack()` | `restack_with_result(repo_root: Path) -> CommandResult` | Restack with result capture |
| `squash_commits()` | `squash_commits(repo_root: Path) -> CommandResult` | Run gt squash |
| `submit(publish, restack)` | `submit(repo_root: Path, *, publish: bool, restack: bool) -> CommandResult` | Run gt submit |
| `navigate_to_child()` | `navigate_to_child(repo_root: Path) -> bool` | Run gt up |

## Implementation Steps

### Step 1: Add CommandResult to Graphite Types

**File:** `packages/erk-shared/src/erk_shared/integrations/graphite/types.py`

Add the `CommandResult` dataclass.

### Step 2: Add Abstract Methods to Graphite ABC

**File:** `packages/erk-shared/src/erk_shared/integrations/graphite/abc.py`

Add 4 abstract methods at the end of the `Graphite` class.

### Step 3: Implement in RealGraphite

**File:** `packages/erk-shared/src/erk_shared/integrations/graphite/real.py`

Copy implementations from `RealGraphiteGtKit`, adding `repo_root` parameter.

### Step 4: Implement in FakeGraphite

**File:** `tests/fakes/graphite.py`

Add fake implementations with configurable state:
- `_restack_result: CommandResult`
- `_squash_result: CommandResult`
- `_submit_result: CommandResult`
- `_navigate_to_child_success: bool`

### Step 5: Update DryRunGraphite

**File:** `packages/erk-shared/src/erk_shared/integrations/graphite/dry_run.py`

Add dry-run implementations that return success without executing.

### Step 6: Add Unit Tests

**File:** `tests/unit/integrations/graphite/test_graphite_abc_new_methods.py` (new file)

Test each new method using FakeGraphite.

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/integrations/graphite/types.py` | Add `CommandResult` dataclass |
| `packages/erk-shared/src/erk_shared/integrations/graphite/abc.py` | Add 4 abstract methods |
| `packages/erk-shared/src/erk_shared/integrations/graphite/real.py` | Add 4 method implementations |
| `packages/erk-shared/src/erk_shared/integrations/graphite/dry_run.py` | Add 4 dry-run implementations |
| `tests/fakes/graphite.py` | Add 4 fake implementations + 4 new fields |
| `tests/unit/integrations/graphite/test_graphite_abc_new_methods.py` | New test file |

## Validation

```bash
uv run pyright packages/erk-shared/src/erk_shared/integrations/graphite/
uv run pytest tests/unit/integrations/graphite/ -v
```

## Risk Assessment

**Low Risk** - Purely additive:
- No existing code paths change
- No behavior changes for existing callers
- New methods are unused until PR 4
- `CommandResult` is a new type, doesn't conflict with existing