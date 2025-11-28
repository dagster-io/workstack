# Plan: Replace manual error check with Ensure.invariant

## Summary

Replace the manual `--json`/`--script` mutual exclusivity check with `Ensure.invariant` for consistency and improved styling.

## File to Modify

`src/erk/cli/commands/wt/create_cmd.py`

## Change

**Lines 563-566** - Replace:
```python
# Validate --json and --script are mutually exclusive
if output_json and script:
    user_output("Error: Cannot use both --json and --script")
    raise SystemExit(1)
```

**With:**
```python
# Validate --json and --script are mutually exclusive
Ensure.invariant(not (output_json and script), "Cannot use both --json and --script")
```

## Verification

- `Ensure` import already exists at line 22
- No new imports needed
- Run existing tests to confirm behavior unchanged