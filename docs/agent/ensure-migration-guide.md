# Ensure Methods Migration Guide

This guide documents the systematic migration of direct `SystemExit` calls to the `Ensure` class methods for consistent error handling across the erk CLI.

## Overview

**Status:** In Progress (Phase 4 of 5)

**Scope:** Migrate 181 `raise SystemExit(1)` calls across 40 files to use `Ensure` methods

**Completed:**

- ✅ Error message standardization guidelines
- ✅ Domain-specific Ensure methods implemented
- ✅ Complex validation patterns documented
- 🔄 Sample migrations completed (core.py, status.py)

## Migration Principles

1. **One file at a time** - Complete each file before moving to the next
2. **Test after each file** - Run tests to ensure no regressions
3. **Preserve behavior** - Error messages should remain user-friendly
4. **Update imports** - Add `from erk.cli.ensure import Ensure` to each file
5. **Follow patterns** - Use examples in this guide as templates

## Common Migration Patterns

### Pattern 1: Empty/Null Checks

**Before:**

```python
if not name or not name.strip():
    user_output("Error: Worktree name cannot be empty")
    raise SystemExit(1)
```

**After:**

```python
Ensure.not_empty(name.strip() if name else "", "Worktree name cannot be empty")
```

### Pattern 2: Boolean Invariants

**Before:**

```python
if name in (".", ".."):
    user_output(f"Error: Cannot delete '{name}' - directory references not allowed")
    raise SystemExit(1)
```

**After:**

```python
Ensure.invariant(
    name not in (".", ".."),
    f"Cannot delete '{name}' - Directory references not allowed"
)
```

### Pattern 3: Path Existence Checks

**Before:**

```python
if not ctx.git.path_exists(wt_path):
    user_output(f"Error: Worktree not found: {wt_path}")
    raise SystemExit(1)
```

**After:**

```python
Ensure.path_exists(ctx, wt_path, f"Worktree not found: {wt_path}")
# Or use domain-specific method:
Ensure.git_worktree_exists(ctx, wt_path, name="feature-123")
```

### Pattern 4: Git Worktree Validation

**Before:**

```python
if current_worktree_path is None:
    user_output("Error: Not in a git worktree")
    raise SystemExit(1)
```

**After:**

```python
Ensure.in_git_worktree(ctx, current_worktree_path)
```

### Pattern 5: Branch Existence Checks

**Before:**

```python
if not ctx.git.branch_exists(repo.root, branch):
    user_output(click.style("Error: ", fg="red") + f"Branch '{branch}' does not exist")
    raise SystemExit(1)
```

**After:**

```python
Ensure.git_branch_exists(ctx, repo.root, branch)
```

### Pattern 6: Configuration Field Validation

**Before:**

```python
if ctx.local_config.github_token is None:
    user_output("Error: GitHub token not configured - Run 'erk config set github_token <token>'")
    raise SystemExit(1)
```

**After:**

```python
Ensure.config_field_set(
    ctx.local_config,
    "github_token",
    "GitHub token not configured - Run 'erk config set github_token <token>'"
)
```

### Pattern 7: Argument Count Validation

**Before:**

```python
if len(args) != 1:
    user_output(f"Error: Expected 1 argument, got {len(args)}")
    raise SystemExit(1)
```

**After:**

```python
Ensure.argument_count(args, 1, "Expected exactly 1 branch name")
```

### Pattern 8: Path Must Not Exist

**Before:**

```python
if ctx.git.path_exists(new_path):
    user_output(f"Error: Destination already exists: {new_path}")
    raise SystemExit(1)
```

**After:**

```python
Ensure.path_not_exists(
    ctx,
    new_path,
    f"Destination already exists: {new_path} - Choose a different name or delete the existing path"
)
```

## Example Migrations

### Example 1: core.py - validate_worktree_name_for_deletion

**Before (5 SystemExit calls):**

```python
def validate_worktree_name_for_deletion(name: str) -> None:
    if not name or not name.strip():
        user_output("Error: Worktree name cannot be empty")
        raise SystemExit(1)

    if name in (".", ".."):
        user_output(f"Error: Cannot delete '{name}' - directory references not allowed")
        raise SystemExit(1)

    if name == "root":
        user_output("Error: Cannot delete 'root' - root worktree name not allowed")
        raise SystemExit(1)

    if name.startswith("/"):
        user_output(f"Error: Cannot delete '{name}' - absolute paths not allowed")
        raise SystemExit(1)

    if "/" in name:
        user_output(f"Error: Cannot delete '{name}' - path separators not allowed")
        raise SystemExit(1)
```

**After (5 Ensure calls):**

```python
def validate_worktree_name_for_deletion(name: str) -> None:
    Ensure.not_empty(name.strip() if name else "", "Worktree name cannot be empty")
    Ensure.invariant(
        name not in (".", ".."),
        f"Cannot delete '{name}' - Directory references not allowed"
    )
    Ensure.invariant(
        name != "root",
        "Cannot delete 'root' - Root worktree name not allowed"
    )
    Ensure.invariant(
        not name.startswith("/"),
        f"Cannot delete '{name}' - Absolute paths not allowed"
    )
    Ensure.invariant(
        "/" not in name,
        f"Cannot delete '{name}' - Path separators not allowed"
    )
```

### Example 2: status.py - Git Worktree Check

**Before:**

```python
if current_worktree_path is None:
    user_output("Error: Not in a git worktree")
    raise SystemExit(1)
```

**After:**

```python
Ensure.in_git_worktree(ctx, current_worktree_path)
```

## Migration Checklist

For each file being migrated:

- [ ] Add `from erk.cli.ensure import Ensure` to imports
- [ ] Identify all `raise SystemExit(1)` calls in the file
- [ ] For each SystemExit call:
  - [ ] Determine which Ensure method to use (see decision tree below)
  - [ ] Extract error message (remove "Error: " prefix if present)
  - [ ] Replace with appropriate Ensure call
  - [ ] Verify error message follows guidelines (actionable, user-friendly)
- [ ] Remove now-unused imports (e.g., `user_output` if only used for errors)
- [ ] Run type checker: `pyright src/erk/cli/commands/<file>.py`
- [ ] Run tests: `pytest tests/cli/commands/test_<file>.py`
- [ ] Verify error messages in tests still match

## Decision Tree: Which Ensure Method?

1. **Is it checking if a path exists?**
   - General path → `Ensure.path_exists(ctx, path, message)`
   - Worktree path → `Ensure.git_worktree_exists(ctx, path, name)`
   - Directory path → `Ensure.path_is_dir(ctx, path, message)`

2. **Is it checking if a path must NOT exist?**
   - → `Ensure.path_not_exists(ctx, path, message)`

3. **Is it checking if currently in a worktree?**
   - → `Ensure.in_git_worktree(ctx, current_path)`

4. **Is it checking if a git branch exists?**
   - → `Ensure.git_branch_exists(ctx, repo_root, branch)`

5. **Is it checking if a value is empty/null?**
   - → `Ensure.not_empty(value, message)`

6. **Is it checking if a config field is set?**
   - → `Ensure.config_field_set(config, field_name, message)`

7. **Is it checking argument count?**
   - → `Ensure.argument_count(args, expected, message)`

8. **Is it any other boolean condition?**
   - → `Ensure.invariant(condition, message)`

9. **Does it need to return a value if truthy?**
   - → `Ensure.truthy(value, message)`

## File Priority Order

Migrate files in this order (high-impact first):

### Phase 4a: Core CLI Validation (5 files)

- [x] `src/erk/cli/core.py` - Foundation layer
- [x] `src/erk/cli/commands/status.py` - High-use status command
- [ ] `src/erk/cli/subprocess_utils.py` - Subprocess error handling
- [ ] `src/erk/cli/commands/navigation_helpers.py` - Navigation utilities
- [ ] `src/erk/cli/commands/wt/current_cmd.py` - Worktree detection

### Phase 4b: Worktree Commands (8 files)

- [ ] `src/erk/cli/commands/wt/delete_cmd.py` - Worktree deletion
- [ ] `src/erk/cli/commands/wt/create_cmd.py` - Worktree creation
- [ ] `src/erk/cli/commands/wt/rename_cmd.py` - Worktree renaming
- [ ] `src/erk/cli/commands/wt/goto_cmd.py` - Worktree navigation
- [ ] `src/erk/cli/commands/wt/list_cmd.py` - Worktree listing
- [ ] `src/erk/cli/commands/checkout.py` - Branch checkout
- [ ] `src/erk/cli/commands/up.py` - Stack navigation up
- [ ] `src/erk/cli/commands/down.py` - Stack navigation down

### Phase 4c: Stack/Config Commands (10 files)

- [ ] `src/erk/cli/commands/stack/move_cmd.py` - Branch stack moves
- [ ] `src/erk/cli/commands/stack/consolidate_cmd.py` - Branch consolidation
- [ ] `src/erk/cli/commands/stack/land_old/validation.py` - Land validation
- [ ] `src/erk/cli/commands/stack/land_old/command.py` - Land command
- [ ] `src/erk/cli/commands/stack/land_old/display.py` - Land display
- [ ] `src/erk/cli/commands/stack/split_old/command.py` - Split command
- [ ] `src/erk/cli/commands/stack/split_old/plan.py` - Split planning
- [ ] `src/erk/cli/commands/stack/split_old/display.py` - Split display
- [ ] `src/erk/cli/commands/config.py` - Config management
- [ ] `src/erk/cli/commands/init.py` - Initialization

### Phase 4d: Remaining Commands (17 files)

- [ ] `src/erk/cli/commands/submit.py` - PR submission
- [ ] `src/erk/cli/commands/implement.py` - Plan implementation
- [ ] `src/erk/cli/commands/admin.py` - Admin operations
- [ ] `src/erk/cli/commands/runs.py` - CI run display
- [ ] `src/erk/cli/commands/shell_integration.py` - Shell activation
- [ ] `src/erk/cli/commands/plan/retry_cmd.py` - Plan retry
- [ ] `src/erk/cli/commands/plan/get.py` - Plan retrieval
- [ ] `src/erk/cli/commands/plan/close_cmd.py` - Plan closure
- [ ] `src/erk/cli/commands/plan/list_cmd.py` - Plan listing
- [ ] `src/erk/data/kits/erk/kit_cli_commands/erk/post_workflow_started_comment.py`
- [ ] `src/erk/data/kits/erk/kit_cli_commands/erk/post_completion_comment.py`
- [ ] `src/erk/data/kits/erk/kit_cli_commands/erk/post_progress_comment.py`
- [ ] `src/erk/data/kits/gt/kit_cli_commands/gt/submit_branch.py`
- [ ] `src/erk/data/kits/gt/kit_cli_commands/gt/land_branch.py`
- [ ] `src/erk/core/user_feedback.py` - User feedback utilities
- [ ] `src/erk/core/context.py` - Context validation
- [ ] `src/erk/core/git/fake.py` - Test fake validation

## Testing Strategy

### Unit Tests

Create/update tests for each migrated file:

```python
def test_validate_worktree_name_empty():
    """Test that empty names are rejected with clear error."""
    with pytest.raises(SystemExit) as exc_info:
        validate_worktree_name_for_deletion("")
    assert exc_info.value.code == 1
    # Verify error message was displayed (check captured output)
```

### Integration Tests

Verify that commands still work end-to-end:

- Run manual smoke tests for migrated commands
- Check that error messages display correctly in terminal
- Verify exit codes are still 1 for validation failures

## Progress Tracking

**Total SystemExit calls:** 181 across 40 files

**Migrated so far:** 6 calls in 2 files

- core.py: 5 calls → 5 Ensure calls ✅
- status.py: 1 call → 1 Ensure call ✅

**Remaining:** 175 calls in 38 files

**Estimated breakdown:**

- Phase 4a (Core): ~15 calls
- Phase 4b (Worktrees): ~40 calls
- Phase 4c (Stack/Config): ~60 calls
- Phase 4d (Remaining): ~60 calls

## Phase 5: Advanced Features

### Implemented

✅ **Error Recovery Suggestions**: Integrated into error message format guidelines. All Ensure method error messages are encouraged to include actionable recovery steps.

Example:

```python
Ensure.config_field_set(
    ctx.local_config,
    "github_token",
    "GitHub token not configured - Run 'erk config set github_token <token>'"  # ← Recovery suggestion
)
```

### Deferred to Future Work

The following Phase 5 features are deferred:

- **Validation Logging/Telemetry**: Would require infrastructure for tracking validation failures. Defer until data collection needs are identified.

- **Localization Support (i18n)**: Not currently required. Error messages are designed to be clear in English. If internationalization becomes a requirement, the Ensure system is structured to support it.

- **Validation Result Objects**: Would conflict with LBYL (Look Before You Leap) philosophy. The current approach (fail fast with SystemExit) is more appropriate for CLI validation.

- **Ensure Plugin System**: Over-engineering for current needs. The existing Ensure methods cover all common validation patterns. If custom validators are needed, they can be added as methods to the Ensure class.

## Next Steps

1. Complete Phase 4a (Core CLI Validation)
2. Write tests for migrated functions
3. Begin Phase 4b (Worktree Commands)
4. Document any new patterns discovered during migration
5. Update this guide with lessons learned

## Lessons Learned

### Don't Remove "Error: " Prefix in Messages

The Ensure methods add the "Error: " prefix automatically with red styling. Migration should remove any manual "Error: " prefix from messages.

### Preserve Error Message Quality

During migration, improve error messages to be more actionable if they're vague. This is an opportunity to enhance UX.

### Watch for user_output Removal

If a file only used `user_output()` for error messages, the import can be removed after migration to Ensure methods (unless used for non-error output).

## Related Documentation

- [cli-output-styling.md](cli-output-styling.md) - Error message guidelines
- [ensure.py](../../src/erk/cli/ensure.py) - Ensure class implementation
- [dignified-python-313 skill](.claude/skills/dignified-python-313.md) - LBYL coding standards
