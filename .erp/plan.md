# Unify Terminology: `erk runs` and `erk ls` Column Names

## Summary

Standardize column naming across `erk runs` and `erk ls` commands:
1. Rename `status` → `run-state` in `erk runs`
2. Remove `state` column (issue state emoji) from `erk runs`

## Changes

### File: `src/erk/cli/commands/runs.py`

1. **Rename column** (line ~118):
   - Change `table.add_column("status", ...)` → `table.add_column("run-state", ...)`

2. **Remove column** (line ~121):
   - Delete `table.add_column("state", no_wrap=True, width=4)`

3. **Update row data** (line ~203-210):
   - Remove `state_cell` from `table.add_row()` call

### File: `tests/commands/test_runs.py`

1. Update any test assertions that check for `status` column → `run-state`
2. Remove assertions for `state` column

## Result

**Before (`erk runs`):**
```
┃ run-id ┃ status   ┃ submitted ┃ plan ┃ sta… ┃ title ┃ pr ┃ chks ┃
```

**After (`erk runs`):**
```
┃ run-id ┃ run-state ┃ submitted ┃ plan ┃ title ┃ pr ┃ chks ┃
```

Now consistent with `erk ls` which uses `run-id` and `run-state`.