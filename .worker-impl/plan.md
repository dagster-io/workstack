# Plan: Make PR/Checks Columns Opt-in and Add --all Flag

## Summary

Modify `erk plan list` to only display `pr` and `chks` columns when explicitly requested via `--prs/-P`, and add an `--all/-a` flag that enables both `--runs` and `--prs`.

## Changes

### File: `src/erk/cli/commands/plan/list_cmd.py`

#### 1. Add `--all/-a` option to `plan_list_options` (after line 183)

```python
f = click.option(
    "--all",
    "-a",
    is_flag=True,
    default=False,
    help="Show all columns (equivalent to --runs --prs)",
)(f)
```

#### 2. Update function signatures to accept `all` parameter

- `_list_plans_impl()` - add `all_columns: bool` parameter
- `list_plans()` - add `all: bool` parameter

#### 3. Resolve `all` flag at start of `_list_plans_impl()`

```python
# Resolve --all flag
if all_columns:
    runs = True
    prs = True
```

#### 4. Make `pr` and `chks` columns conditional (lines 289-290)

Move from unconditional:

```python
table.add_column("pr", no_wrap=True)
table.add_column("chks", no_wrap=True)
```

To conditional (similar to `runs` pattern):

```python
if prs:
    table.add_column("pr", no_wrap=True)
    table.add_column("chks", no_wrap=True)
```

#### 5. Update table row construction (lines 378-398)

Current code has two branches (`if runs` / `else`). Need to expand to handle all combinations:

```python
# Build row values
row_values = [issue_id, title, worktree_name_cell, local_run_cell]

# Insert PR columns after title if enabled
if prs:
    row_values.insert(2, pr_cell)
    row_values.insert(3, checks_cell)

# Append run columns if enabled
if runs:
    row_values.extend([run_id_cell, run_outcome_cell])

table.add_row(*row_values)
```

#### 6. Update column order definition

Reorder column additions to match the dynamic row building:

```python
table.add_column("plan", style="cyan", no_wrap=True)
table.add_column("title", no_wrap=True)
if prs:
    table.add_column("pr", no_wrap=True)
    table.add_column("chks", no_wrap=True)
table.add_column("local-wt", no_wrap=True)
table.add_column("local-run", no_wrap=True)
if runs:
    table.add_column("run-id", no_wrap=True)
    table.add_column("run-state", no_wrap=True, width=12)
```

## Testing

Update tests in `tests/commands/test_plan_list.py` to verify:

1. Default output has no `pr`/`chks` columns
2. `--prs` adds `pr` and `chks` columns
3. `--all` adds both PR and run columns
4. `-a` short form works
