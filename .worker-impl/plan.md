# Fix Branch Naming Inconsistency in `erk submit`

## Problem

`erk submit` creates branches without date suffix (e.g., `plan-delete-dead-code-simple-s`), while `erk implement` creates branches with date suffix (e.g., `remove-authorplan-headers-from-25-11-29-0632`). They should use the same canonical naming.

## Root Cause

Two separate code paths:
- `submit.py:157` uses `derive_branch_name_from_title()` - no date suffix
- `implement.py` / `create_cmd.py` use `ensure_unique_worktree_name_with_date()` - has date suffix

## Solution

Create a unified function for generating branch names with date suffix, and update all callers.

## Implementation Steps

### Step 1: Add new function to naming.py

Add `derive_branch_name_with_date(title: str) -> str` to `packages/erk-shared/src/erk_shared/naming.py`:
- Calls `derive_branch_name_from_title(title)` to get sanitized base name
- Appends datetime suffix using `WORKTREE_DATE_SUFFIX_FORMAT`
- Returns complete branch name

### Step 2: Update submit.py

In `src/erk/cli/commands/submit.py`:
- Change import from `derive_branch_name_from_title` to `derive_branch_name_with_date`
- Update line 157 to call the new function

### Step 3: Update dot-agent kit command

In `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/derive_branch_name.py`:
- Change to use `derive_branch_name_with_date`
- Update docstring examples to show date suffix

### Step 4: Update tests

- Add unit tests for `derive_branch_name_with_date()` in `tests/core/utils/test_naming.py`
- Update `tests/commands/test_submit.py` to expect branch names with date suffix

## Files to Modify

1. `packages/erk-shared/src/erk_shared/naming.py` - Add new function
2. `src/erk/cli/commands/submit.py` - Use new function
3. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/derive_branch_name.py` - Use new function
4. `tests/core/utils/test_naming.py` - Add tests
5. `tests/commands/test_submit.py` - Update expected branch names