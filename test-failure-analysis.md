# Test Failure Analysis - Category 2

**Branch**: `fix-category-2-test-failures-25-11-10`
**Date**: 2025-11-10
**Total Tests**: 797
**Failed**: 174 (21.8%)
**Passed**: 621 (77.9%)
**Skipped**: 2 (0.3%)
**Execution Time**: 11.64s

---

## Executive Summary

The test suite has 174 failures concentrated primarily in command-level tests (88% of failures). The root cause appears to be a breaking change in the `list --stacks` command output format following the recent Phase 3a refactoring. The command is no longer rendering branch lines beneath worktree headers, causing widespread test failures across all command categories that rely on list output validation.

---

## Failure Distribution

### By Test Module (High-Level)

| Module               | Failures | % of Total |
| -------------------- | -------- | ---------- |
| `tests/commands/`    | 153      | 88.0%      |
| `tests/hooks/`       | 18       | 10.3%      |
| `tests/unit/`        | 2        | 1.1%       |
| `tests/integration/` | 1        | 0.6%       |

### By Command Category (Detailed)

| Category            | Failures | Test Files Affected                                |
| ------------------- | -------- | -------------------------------------------------- |
| Workspace Commands  | 49       | `test_create.py`, `test_move.py`, `test_rename.py` |
| Setup Commands      | 48       | Various setup-related tests                        |
| Navigation Commands | 23       | Branch/worktree navigation tests                   |
| Display Commands    | 19       | `test_root_filtering.py`, list/status tests        |
| Graphite Commands   | 7        | Stack and PR-related operations                    |
| Shell Commands      | 3        | Shell integration tests                            |
| Management Commands | 2        | General management operations                      |
| Status Display      | 2        | Status rendering tests                             |

---

## Root Cause Analysis

### Primary Issue: List Command Output Format Change

**Example from first failing test** (`test_root_on_trunk_shows_only_trunk`):

**Expected Output:**

```
root      (main) [no PR] [no plan] ← (cwd)
  ◉  main
```

**Actual Output:**

```
root      (main) [no PR] [no plan] ← (cwd)
```

### Impact

The missing branch lines under worktree headers affect:

1. **Direct list command tests**: Tests that explicitly validate list output
2. **Indirect command tests**: Tests for workspace/navigation commands that verify operations by checking list output
3. **Display logic tests**: Tests that validate filtering, sorting, and display rules

### Scope

This is a **systemic issue** affecting the display layer, not isolated bugs in individual commands. The underlying command logic (create, move, rename, etc.) may be working correctly, but the validation mechanism (list output checks) is broken.

---

## Failure Categories

### Category 1: Display Layer (19 failures)

**Files**:

- `tests/commands/display/list/test_root_filtering.py`
- `tests/commands/display/list/test_stack_display.py`
- `tests/commands/display/status/test_*.py`

**Issue**: List command not rendering branches under worktrees in `--stacks` mode

**Tests Affected**:

- Root filtering logic
- Stack visibility rules
- Status display formatting
- Branch grouping under worktrees

**Fix Priority**: **CRITICAL** - This is the root cause blocking most other tests

---

### Category 2: Workspace Commands (49 failures)

**Files**:

- `tests/commands/workspace/test_create.py`
- `tests/commands/workspace/test_move.py`
- `tests/commands/workspace/test_rename.py`

**Issue**: Tests validate operations by checking list output, which is now broken

**Example failure pattern**:

```python
# Test creates a worktree
result = runner.invoke(["workspace", "create", "feat-branch"])

# Test validates by checking list output
list_result = runner.invoke(["list", "--stacks"])
assert "feat-branch" in list_result.output  # ❌ FAILS: branch line missing
```

**Fix Dependency**: Depends on fixing Category 1 (display layer)

**Fix Priority**: **HIGH** - Validates core functionality but blocked by display issue

---

### Category 3: Setup Commands (48 failures)

**Files**:

- Various setup-related test files under `tests/commands/setup/`

**Issue**: Setup operations validated through list output

**Fix Dependency**: Depends on fixing Category 1

**Fix Priority**: **HIGH** - Core setup functionality

---

### Category 4: Navigation Commands (23 failures)

**Files**:

- `tests/commands/navigation/test_*.py`

**Issue**: Navigation tests verify current location via list output

**Fix Dependency**: Depends on fixing Category 1

**Fix Priority**: **MEDIUM** - Navigation logic likely correct, validation broken

---

### Category 5: Graphite Commands (7 failures)

**Files**:

- `tests/commands/graphite/test_*.py`

**Issue**: Stack operations validated through list output

**Fix Dependency**: Depends on fixing Category 1

**Fix Priority**: **MEDIUM** - Graphite integration validation

---

### Category 6: Hook Tests (18 failures)

**Files**:

- `tests/hooks/test_suggest_dignified_python.py` (ALL 16 tests failing)
- Other hook tests

**Issue**: Likely independent from display layer issue; may be related to hook logic or test setup

**Fix Dependency**: **INDEPENDENT** - Should be investigated separately

**Fix Priority**: **MEDIUM** - Hook functionality isolated from main workflow

---

### Category 7: Unit Tests (2 failures)

**Files**:

- `tests/unit/detection/test_trunk_detection.py`

**Issue**: Trunk detection logic failures

**Fix Dependency**: Likely **INDEPENDENT**

**Fix Priority**: **LOW** - Unit-level issue, limited scope

---

### Category 8: Integration Tests (1 failure)

**Files**:

- `tests/integration/test_land_stack_worktree.py`

**Issue**: Stack landing integration test

**Fix Dependency**: May depend on display layer or may be independent

**Fix Priority**: **MEDIUM** - Integration test validating end-to-end workflow

---

## Failure Patterns

### Pattern 1: Missing Branch Lines (Dominant)

**Frequency**: ~135-150 failures (~85% of total)

**Signature**:

- Expected output contains branch lines (e.g., `  ◉  main`)
- Actual output missing these lines
- Only worktree header line present

**Root Cause**: Display rendering logic for `--stacks` mode

---

### Pattern 2: Hook Execution Failures

**Frequency**: 18 failures (~10% of total)

**Signature**:

- All failures in `test_suggest_dignified_python.py`
- Hook logic or test isolation issues

**Root Cause**: Unclear - requires investigation

---

### Pattern 3: Logic/Assertion Failures

**Frequency**: 5-10 failures (~5% of total)

**Signature**:

- Unit test assertion failures
- Integration test logic errors

**Root Cause**: Varies by test

---

## Recommended Fix Strategy

### Phase 1: Fix Display Layer (CRITICAL PATH)

**Target**: Category 1 - Display layer failures (19 direct failures)

**Action**:

1. Investigate `list --stacks` command rendering logic
2. Identify where branch lines are being suppressed/filtered
3. Restore branch rendering under worktree headers
4. Validate against `test_root_filtering.py` tests

**Expected Impact**: Should fix ~135-150 failures (85% of total) once display is corrected

**Files to Investigate**:

- `src/workstack/commands/display/list/*.py`
- Display formatting/rendering modules
- Stack display logic

---

### Phase 2: Fix Hook Tests (INDEPENDENT)

**Target**: Category 6 - Hook test failures (18 failures)

**Action**:

1. Investigate `test_suggest_dignified_python.py` failures
2. Check hook execution logic
3. Verify test isolation and setup

**Expected Impact**: Fixes 18 failures (10% of total)

**Files to Investigate**:

- `tests/hooks/test_suggest_dignified_python.py`
- `src/workstack/hooks/suggest_dignified_python.py`

---

### Phase 3: Fix Remaining Issues (CLEANUP)

**Target**: Categories 7-8 - Unit and integration test failures (3 failures)

**Action**:

1. Fix trunk detection unit tests (2 failures)
2. Fix land stack integration test (1 failure)

**Expected Impact**: Fixes remaining 3 failures (1.5% of total)

---

## Test Health Metrics

### Before Fix

- **Pass Rate**: 77.9% (621/797)
- **Failure Rate**: 21.8% (174/797)
- **Skip Rate**: 0.3% (2/797)

### After Phase 1 (Projected)

- **Pass Rate**: ~95% (~756/797)
- **Failure Rate**: ~5% (~39/797)
- **Skip Rate**: 0.3% (2/797)

### After Phase 2 (Projected)

- **Pass Rate**: ~97% (~774/797)
- **Failure Rate**: ~3% (~21/797)
- **Skip Rate**: 0.3% (2/797)

### After Phase 3 (Target)

- **Pass Rate**: 99.7%+ (~795/797)
- **Failure Rate**: <1% (~2/797 or less)
- **Skip Rate**: 0.3% (2/797)

---

## Notes

### Collection Errors (Not Counted in Failures)

The `packages/dot-agent-kit/tests/` directory has 38 test files with collection errors due to missing `__init__.py` files or import path configuration issues. These are **not included** in the 174 failure count, as pytest cannot even collect them.

**Recommendation**: Address separately as a test infrastructure issue.

---

## Appendix: Test Execution Command

```bash
make test
# or
uv run pytest --tb=short --no-header -v
```

---

## Related Documentation

- Phase 3a refactoring documentation
- Display layer architecture
- Test isolation patterns (`docs/agent/testing.md`)
