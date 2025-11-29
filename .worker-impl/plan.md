# Reorganize CLI Command Aliases

Move `create` and `status` commands from top-level into their logical command groups.

## Summary

- **`create`** → Move into `plan` group as `plan create`
- **`status`** → Move into `wt` group as `wt status`
- **`pr`** → Already a group, no changes needed

Both commands will be completely removed from the top level (not kept as aliases).

## Implementation Steps

### Step 1: Update `plan` group to include `create`

**File:** `src/erk/cli/commands/plan/__init__.py`

- Import `create_plan` from `plan/create_cmd.py`
- Add `create_plan` to the `plan_group` as `create`

### Step 2: Update `wt` group to include `status`

**File:** `src/erk/cli/commands/wt/__init__.py`

- Import `status_cmd` from `commands/status.py`
- Add `status_cmd` to the `wt_group` as `status`

### Step 3: Remove top-level registrations from `cli.py`

**File:** `src/erk/cli/cli.py`

- Remove line: `cli.add_command(create_plan, name="create")`
- Remove line: `cli.add_command(status_cmd)`
- Remove import: `from erk.cli.commands.status import status_cmd`
- Remove import: `from erk.cli.commands.plan.create_cmd import create_plan`

### Step 4: Update help formatter categories

**File:** `src/erk/cli/help_formatter.py`

- Remove `"create"` and `"status"` from any category lists (they appear in `other_cmds` by default since they're not in any defined category)

### Step 5: Run tests to verify

- Run pytest to ensure no regressions
- Verify `erk plan create` and `erk wt status` work correctly
- Verify `erk create` and `erk status` no longer exist

## Files to Modify

1. `src/erk/cli/commands/plan/__init__.py` - Add create command
2. `src/erk/cli/commands/wt/__init__.py` - Add status command
3. `src/erk/cli/cli.py` - Remove top-level registrations
4. `src/erk/cli/help_formatter.py` - Clean up category lists (if needed)