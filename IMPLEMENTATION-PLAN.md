# Implementation Plan: Fix Category 2 Test Failures

**Branch**: `fix-category-2-test-failures-25-11-10`
**Date**: 2025-11-10
**Status**: ✅ Phase 1 Complete - See IMPLEMENTATION-PROGRESS.md for details

---

## ✅ COMPLETION NOTICE

**Phase 1 has been completed successfully.**

**For detailed progress and results, see**: [`IMPLEMENTATION-PROGRESS.md`](IMPLEMENTATION-PROGRESS.md)

**Quick Summary**:
- ✅ Fixed 14 occurrences across 2 test files
- ✅ All 16 targeted tests now passing (3 in test_root_filtering.py, 13 in test_stacks.py)
- ✅ Overall test suite improved from 621 passing to 631 passing (10 test improvement)
- ⚠️ Note: Original estimate of ~135 fixes was incorrect; remaining failures have different root causes

**Next Steps**: See Phase 2 in IMPLEMENTATION-PROGRESS.md for investigation of workspace command failures.

---

## Root Cause Analysis

### The Problem

Tests create `RealGraphiteOps()` instances but don't pass them to `WorkstackContext.for_test()`, causing contexts to default to empty `FakeGraphiteOps()`. When `list --stacks` command calls `ctx.graphite_ops.get_branch_stack()`, it returns `None`, causing the `_display_branch_stack()` function to exit early without rendering branch lines.

### Why This Breaks So Many Tests

1. **Direct failures**: 19 display layer tests expecting branch lines in output
2. **Cascading failures**: ~135 tests that validate operations by checking list output
   - Workspace commands (create, move, rename)
   - Navigation commands (switch, jump)
   - Setup commands (init, setup)

### Origin of Bug

Introduced during Phase 3a refactoring (commit `e56363ef`):
- Test files updated to use new `GlobalConfig` pattern
- `RealGraphiteOps()` instantiation pattern not updated correctly
- Lines like `RealGraphiteOps()` left orphaned without assignment
- Missing `graphite_ops=` parameter in `WorkstackContext.for_test()` calls

---

## Implementation Strategy

### Phase 1: Fix Test Setup ✅ COMPLETED

**Target**: Fix 14 broken occurrences across 2 test files (11 initially identified + 3 additional found)

**Files Modified**:

1. **`tests/commands/display/list/test_root_filtering.py`** ✅ (3 fixes complete)
   - ✅ Line ~97: `test_root_on_trunk_shows_only_trunk()`
   - ✅ Line ~203: `test_root_on_non_trunk_shows_ancestors_only()`
   - ✅ Line ~320: `test_non_root_worktree_shows_descendants_with_worktrees()`

2. **`tests/commands/display/list/test_stacks.py`** ✅ (11 fixes complete)
   - ✅ Initial 8 fixes with orphaned `RealGraphiteOps()`
   - ✅ Additional 3 fixes for tests completely missing graphite_ops
   - **Note**: Line ~716 in `test_list_with_stacks_corrupted_cache()` was already correct and used as reference

### Pattern to Apply

**Before (broken)**:
```python
RealGraphiteOps()  # ← Orphaned, not assigned

test_ctx = WorkstackContext.for_test(
    git_ops=git_ops,
    global_config=global_config_ops,
    cwd=env.cwd,
    # ← Missing graphite_ops parameter
)
```

**After (fixed)**:
```python
graphite_ops = RealGraphiteOps()  # ← Assign to variable

test_ctx = WorkstackContext.for_test(
    git_ops=git_ops,
    global_config=global_config_ops,
    graphite_ops=graphite_ops,  # ← Pass to context
    cwd=env.cwd,
)
```

---

## Detailed Changes ✅ COMPLETED

### File 1: `tests/commands/display/list/test_root_filtering.py` ✅

#### Change 1: Line ~97 in `test_root_on_trunk_shows_only_trunk()` ✅

**Find**:
```python
RealGraphiteOps()

test_ctx = WorkstackContext.for_test(
    git_ops=git_ops,
    global_config=global_config_ops,
    cwd=env.cwd,
)
```

**Replace with**:
```python
graphite_ops = RealGraphiteOps()

test_ctx = WorkstackContext.for_test(
    git_ops=git_ops,
    global_config=global_config_ops,
    graphite_ops=graphite_ops,
    cwd=env.cwd,
)
```

#### Change 2: Line ~203 in `test_root_on_non_trunk_shows_ancestors_only()` ✅

Applied same pattern as Change 1.

#### Change 3: Line ~320 in `test_non_root_worktree_shows_descendants_with_worktrees()` ✅

Applied same pattern as Change 1.

---

### File 2: `tests/commands/display/list/test_stacks.py` ✅

#### Changes: 11 occurrences total (preserved line ~716 - already correct) ✅

**Initial 8 fixes** - Tests with orphaned `RealGraphiteOps()`:
- ✅ Line ~82: `test_list_with_stacks_flag()`
- ✅ Line ~154: `test_list_with_stacks_graphite_disabled()`
- ✅ Line ~187: `test_list_with_stacks_no_graphite_cache()`
- ✅ Line ~287: `test_list_with_stacks_highlights_current_branch_not_worktree_branch()`
- ✅ Line ~370: `test_list_with_stacks_root_repo_does_not_duplicate_branch()`
- ✅ Line ~453: `test_list_with_stacks_shows_descendants_with_worktrees()`
- ✅ Line ~544: `test_list_with_stacks_hides_descendants_without_worktrees()`
- ✅ Line ~633: `test_list_with_stacks_shows_descendants_with_gaps()`

**Additional 3 fixes** - Tests completely missing graphite_ops:
- ✅ Line ~794: `test_list_with_stacks_shows_plan_summary()`
- ✅ Line ~909: `test_list_with_stacks_no_plan_file()`
- ✅ Line ~969: `test_list_with_stacks_plan_without_frontmatter()`

Find all instances of the broken pattern and apply the fix.

**Reference (correct pattern)**: Line ~716 in `test_list_with_stacks_corrupted_cache()`:
```python
graphite_ops = RealGraphiteOps()

test_ctx = WorkstackContext.for_test(
    git_ops=git_ops,
    global_config=global_config_ops,
    graphite_ops=graphite_ops,
    github_ops=FakeGitHubOps(),
    shell_ops=FakeShellOps(),
    cwd=env.cwd,
    dry_run=False,
)
```

---

## Verification Steps ✅ COMPLETED

### 1. Verify Individual Files ✅

```bash
# Test root_filtering.py (3 tests should pass)
$ uv run pytest tests/commands/display/list/test_root_filtering.py -v
# Result: ✅ 3 passed in 0.05s

# Test stacks.py (13 tests should pass)
$ uv run pytest tests/commands/display/list/test_stacks.py -v
# Result: ✅ 13 passed, 1 warning in 0.07s
```

### 2. Verify Display Layer Category ⚠️ PARTIAL

```bash
# Display tests - not all pass (some failures in test_tree.py remain)
uv run pytest tests/commands/display/ -v
```

### 3. Run Full Test Suite ✅

```bash
# Check overall improvement
$ uv run pytest tests/ -v --tb=no -q
# Result: 164 failed, 631 passed, 2 skipped in 10.44s
# Improvement: 621 → 631 passing (10 tests fixed)
```

### Expected Output

**Before fix**:
```
root      (main) [no PR] [no plan] ← (cwd)
                                      ← Branch line MISSING
```

**After fix**:
```
root      (main) [no PR] [no plan] ← (cwd)
  ◉  main                             ← Branch line appears
```

---

## Expected Impact vs Actual Results

### Test Health Metrics

**Before Fix**:
- Pass Rate: 77.9% (621/797)
- Failure Rate: 21.8% (174/797)
- Skip Rate: 0.3% (2/797)

**After Fix (Projected)**: ⚠️ PROJECTION WAS INCORRECT
- Pass Rate: ~95% (~756/797)
- Failure Rate: ~5% (~39/797)
- Skip Rate: 0.3% (2/797)
- **Projected Fixed**: ~135 tests (85% of all failures)

**After Fix (Actual Results)**: ✅
- Pass Rate: 79.3% (631/795 collected)
- Failure Rate: 20.6% (164/795)
- Skip Rate: 0.3% (2/795)
- **Actually Fixed**: 10 tests (5.7% of failures)

### Why Projection Was Incorrect

**Original assumption** (proven wrong):
- Fixes 19 direct display layer tests
- Cascades to fix ~115-130 indirect tests:
  - Workspace commands validate via list output
  - Navigation commands verify location via list output
  - Setup commands check initialization via list output

**Actual findings**:
- Only 16 display layer tests were affected by graphite_ops issue
- Other test categories have **independent** root causes
- Tests don't primarily validate via list output as assumed
- Remaining 164 failures require separate investigation

---

## Important Notes

### No Production Code Changes Needed

The `list` command implementation in `src/workstack/cli/commands/list.py` is **correct**:
- `_display_branch_stack()` properly checks for `None` stack
- Early return behavior is appropriate
- Bug is purely in test setup, not production code

### Reference Files

**Working examples** (for verification):
- `tests/commands/display/list/test_stacks.py` line ~716 (correct pattern)
- `tests/commands/navigation/test_switch.py` (passes `graphite_ops=RealGraphiteOps()`)

**Core implementation** (no changes needed):
- `src/workstack/cli/commands/list.py` - List command implementation
- `src/workstack/core/context.py` - `WorkstackContext.for_test()` method
- `src/workstack/core/graphite_ops.py` - `RealGraphiteOps.get_branch_stack()`

---

## Risk Assessment

### Risk: LOW

- Simple, mechanical change (11 identical fixes)
- Well-understood root cause
- No production code changes
- Large test coverage validates the fix
- Can verify incrementally (file by file)

### Rollback Strategy

If issues arise, simply revert the changes (all changes are in test files only).

---

## Next Steps After Phase 1 ✅ UPDATED

**For detailed next steps, see**: [`IMPLEMENTATION-PROGRESS.md`](IMPLEMENTATION-PROGRESS.md)

With 164 failures remaining, address by priority:

### Phase 2: Workspace Command Failures (Priority: HIGH) 🔄 TODO

**Target**: ~50 failures in workspace commands
- `tests/commands/workspace/test_create.py`
- `tests/commands/workspace/test_move.py`
- `tests/commands/workspace/test_rename.py`

**Action**: Investigate if similar graphite_ops injection issues exist

### Phase 3: Hook Tests (Priority: MEDIUM) 🔄 TODO

**Target**: 19 failures in `tests/hooks/test_suggest_dignified_python.py`
- Independent issue (not related to display layer)
- Requires separate investigation

### Phase 4: Navigation/Setup/Other (Priority: MEDIUM-LOW) 🔄 TODO

**Target**: Remaining ~95 failures across various categories
- Navigation commands: ~20 failures
- Setup commands: ~48 failures
- Display/Tree: 9 failures
- Graphite: 7 failures
- Integration/Unit: 3+ failures

---

## Success Criteria ✅ ACHIEVED (Phase 1)

✅ All 3 tests in `test_root_filtering.py` pass
✅ All 13 tests in `test_stacks.py` pass
⚠️ Overall pass rate increased from 78% to 79.3% (not ~95% as projected)
✅ No new test failures introduced
✅ List output shows branch lines under worktree headers (in fixed tests)

---

## Related Documentation

- **Progress**: [`IMPLEMENTATION-PROGRESS.md`](IMPLEMENTATION-PROGRESS.md) ✨ **START HERE** - Detailed progress tracking and results
- **Analysis**: `test-failure-analysis.md` - Original failure analysis and root cause investigation
- **Testing Guide**: `docs/agent/testing.md` - Test isolation patterns and best practices
- **Context API**: `src/workstack/core/context.py` - WorkstackContext.for_test implementation
