# Plan: Use Ensure in navigation_helpers.py

## Task
Add one usage of `Ensure` class in the CLI codebase.

## Selected Callsite
**File:** `src/erk/cli/commands/navigation_helpers.py`
**Function:** `check_clean_working_tree()` (lines 30-41)

## Current Code (lines 30-41)
```python
def check_clean_working_tree(ctx: ErkContext) -> None:
    """Check that working tree has no uncommitted changes.

    Raises SystemExit if uncommitted changes found.
    """
    if ctx.git.has_uncommitted_changes(ctx.cwd):
        user_output(
            click.style("Error: ", fg="red")
            + "Cannot delete current branch with uncommitted changes.\n"
            "Please commit or stash your changes first."
        )
        raise SystemExit(1)
```

## Proposed Change
```python
def check_clean_working_tree(ctx: ErkContext) -> None:
    """Check that working tree has no uncommitted changes.

    Raises SystemExit if uncommitted changes found.
    """
    Ensure.invariant(
        not ctx.git.has_uncommitted_changes(ctx.cwd),
        "Cannot delete current branch with uncommitted changes.\n"
        "Please commit or stash your changes first.",
    )
```

## Rationale
1. **Consistency**: Same file already uses `Ensure.invariant()` (line 24-27), `Ensure.truthy()` (line 191-194), and `Ensure.path_exists()` (line 146)
2. **Minimal change**: Single function, straightforward replacement
3. **Import already present**: `from erk.cli.ensure import Ensure` is on line 10
4. **Same error behavior**: `Ensure.invariant()` outputs "Error: " prefix in red and raises `SystemExit(1)`