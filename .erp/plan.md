# Refactoring Plan: check_cmd.py to Use Ensure Pattern

## User Requirements
- **Scope**: Just check_cmd.py (other commands can adopt later)
- **API Error Handling**: Add new Ensure methods for GitHub API calls
- **Shared Utility**: Create shared identifier parsing utility now

## Implementation Strategy

Create infrastructure for Ensure-based error handling and shared parsing, apply to check_cmd.py, enabling future adoption by other commands.

## Phase 1: Create Shared Identifier Parsing Utility

### New File: `src/erk/cli/parse_issue_reference.py`

Following the pattern of `parse_pr_reference.py` (lines 9-50), create a focused parsing module with:
- Plain number parsing with positive validation
- GitHub URL parsing with regex (handles fragments)
- Clear error messages with expected formats
- SystemExit for CLI-aware error handling

## Phase 2: Extend Ensure Class with GitHub API Methods

### Additions to `src/erk/cli/ensure.py`

Add two new methods:

1. `parse_github_issue_reference()` - Wraps parse_issue_reference with Ensure semantics
2. `github_api_call[T]()` - Generic wrapper for GitHub API RuntimeError handling

## Phase 3: Refactor check_cmd.py

### Changes to `src/erk/cli/commands/plan/check_cmd.py`

- **Remove**: `_parse_identifier()` function (lines 18-41)
- **Add**: Import Ensure class
- **Replace**: Three try/except blocks with Ensure method calls
  - Identifier parsing: Use `Ensure.parse_github_issue_reference()`
  - Issue fetching: Use `Ensure.github_api_call(lambda: ctx.issues.get_issue(...))`
  - Comments fetching: Use `Ensure.github_api_call(lambda: ctx.issues.get_issue_comments(...))`

**Net Result**: Remove ~24 lines, replace ~15 lines with ~6 lines of Ensure calls

## Phase 4: Add Tests for New Utilities

### New File: `tests/unit/cli/test_parse_issue_reference.py`

Comprehensive tests covering:
- Plain number parsing
- GitHub URL parsing (with fragments/query strings)
- Invalid input validation (non-numbers, zero, negative)

### Update: `tests/unit/cli/test_ensure.py`

Add tests for new Ensure methods:
- `test_parse_github_issue_reference_valid()`
- `test_parse_github_issue_reference_invalid()`
- `test_github_api_call_success()`
- `test_github_api_call_runtime_error()`

## Phase 5: Update Existing Tests

Verify `tests/commands/plan/test_check.py` still passes:
- Error messages remain identical
- Behavior unchanged (SystemExit(1) on errors)
- No test modifications expected

## Summary of Changes

### Files Created (2)
1. `src/erk/cli/parse_issue_reference.py` - Shared identifier parsing (~60 lines)
2. `tests/unit/cli/test_parse_issue_reference.py` - Parsing tests (~60 lines)

### Files Modified (3)
1. `src/erk/cli/ensure.py` - Add 2 new methods (~40 lines)
2. `src/erk/cli/commands/plan/check_cmd.py` - Use Ensure (~30 lines removed, ~10 added)
3. `tests/unit/cli/test_ensure.py` - Add tests (~20 lines)

### Total Impact
- **Lines added**: ~130
- **Lines removed**: ~30
- **Net increase**: ~100 lines (infrastructure for future reuse)
- **Files touched**: 5 files
- **Risk level**: Low (functionality unchanged, well-tested)

## Benefits

1. **Consistency**: All error handling uses Ensure pattern
2. **Reusability**: Other commands can adopt utilities (close_cmd, retry_cmd)
3. **Type Safety**: `github_api_call[T]` preserves return types
4. **Maintainability**: Single source of truth for identifier parsing
5. **Better UX**: Validates positive issue numbers
6. **Testability**: Utilities independently testable

## Future Work (Not in This PR)

Commands that could benefit later:
- `close_cmd.py` - duplicate identifier parsing
- `retry_cmd.py` - duplicate identifier parsing
- `log_cmd.py` - RuntimeError handling
- `get.py` - RuntimeError handling