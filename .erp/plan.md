# Plan: Use Ensure in navigation_helpers.py

## Target

**File:** `src/erk/cli/commands/navigation_helpers.py`
**Function:** `ensure_graphite_enabled()` (lines 24-29)

## Current Code

```python
def ensure_graphite_enabled(ctx: ErkContext) -> None:
    if not (ctx.global_config and ctx.global_config.use_graphite):
        user_output(
            "Error: This command requires Graphite to be enabled. "
            "Run 'erk config set use_graphite true'"
        )
        raise SystemExit(1)
```

## Refactored Code

```python
def ensure_graphite_enabled(ctx: ErkContext) -> None:
    Ensure.invariant(
        ctx.global_config is not None and ctx.global_config.use_graphite,
        "This command requires Graphite to be enabled. Run 'erk config set use_graphite true'"
    )
```

## Rationale

1. `Ensure` is already imported in this file (line 10)
2. Current code is missing the red `click.style("Error: ", fg="red")` prefix - using `Ensure.invariant()` adds this automatically
3. Reduces boilerplate from 5 lines to 4 lines
4. Improves consistency with other error handling in the codebase