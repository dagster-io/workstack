# CLI Command Architecture

This document explains the ops layer architecture pattern used in workstack CLI commands, particularly how dry-run mode is implemented through wrapper classes.

## Overview

Workstack CLI commands follow a layered wrapper architecture that automatically handles dry-run behavior, output formatting, and operation simulation. Understanding this pattern is critical to implementing CLI commands correctly.

## The Wrapper Pattern

### Architecture Layers

Commands use a three-layer wrapper pattern:

```
CLI Command
    ↓
WorkstackContext (ctx)
    ↓
Printing Wrapper (PrintingGitOps, PrintingGraphiteOps)
    ↓
Noop Wrapper (NoopGitOps, NoopGraphiteOps) [if dry_run=True]
    ↓
Real Operations (GitOps, GraphiteOps)
```

**Key insight:** Each layer transparently wraps the next, so command code just calls `ctx.git_ops.method()` and the wrappers handle everything else.

### Layer Responsibilities

1. **Real Operations Layer** (`GitOps`, `GraphiteOps`)
   - Executes actual git/graphite commands
   - Interacts with filesystem and subprocess

2. **Noop Wrapper Layer** (`NoopGitOps`, `NoopGraphiteOps`)
   - Active only when `dry_run=True`
   - Prevents all mutations by intercepting operations
   - Returns simulated results
   - Makes operations safe to call in dry-run mode

3. **Printing Wrapper Layer** (`PrintingGitOps`, `PrintingGraphiteOps`)
   - Wraps all operations to add output formatting
   - Automatically adds dry-run indicators when `self._dry_run=True`
   - Provides consistent command output format
   - Uses bright cyan "(dry run)" markers with bold styling

4. **Context Layer** (`WorkstackContext`)
   - Exposes wrapped ops through `ctx.git_ops` and `ctx.graphite_ops`
   - Commands interact only with this layer
   - Abstracts all wrapper complexity

## How Dry-Run Works

### Setup (in command.py)

The wrapper setup happens once at command entry:

```python
# From src/workstack/cli/commands/land_stack/command.py:100-118
if dry_run:
    ctx = ctx.with_git_ops(NoopGitOps(ctx.git_ops, ctx.cwd))
    ctx = ctx.with_graphite_ops(NoopGraphiteOps(ctx.graphite_ops))

# Wrap with printing layer
ctx = ctx.with_git_ops(PrintingGitOps(ctx.git_ops, dry_run=dry_run))
ctx = ctx.with_graphite_ops(PrintingGraphiteOps(ctx.graphite_ops, dry_run=dry_run))
```

**After this setup, commands never need to check `dry_run` flag manually.**

### Automatic Dry-Run Indicators

The `PrintingOpsBase._format_command()` method automatically adds dry-run markers:

```python
# From src/workstack/ops/printing_ops_base.py:45-54
def _format_command(self, command: str) -> str:
    styled = click.style(f"  {command}", dim=True)
    if self._dry_run:
        dry_run_marker = click.style(" (dry run)", fg="bright_cyan", bold=True)
        styled += dry_run_marker
    checkmark = click.style(" ✓", fg="green")
    return styled + checkmark
```

When `dry_run=True`, output automatically shows:

```
  git checkout main (dry run) ✓
```

## Command Implementation Pattern

### ✅ CORRECT: Use Wrapped Ops

Commands should trust the wrapper architecture and call ops methods directly:

```python
# From src/workstack/cli/commands/land_stack/execution.py:42
ctx.git_ops.checkout_branch(repo_root, branch)
```

**Why this works:**

- If `dry_run=False`: Executes real checkout and prints formatted output
- If `dry_run=True`: Noop prevents mutation, printing adds "(dry run)" marker
- No manual `dry_run` checks needed in command code

### ❌ WRONG: Manual Dry-Run Checks

The land-stack cleanup bug was caused by bypassing the wrapper architecture:

```python
# BEFORE (buggy code from cleanup.py:58-60)
if not dry_run:
    ctx.git_ops.checkout_branch(repo_root, trunk_branch)
_emit(_format_cli_command(f"git checkout {trunk_branch}", check), script_mode=script_mode)
```

**Why this was wrong:**

1. Manual `if not dry_run` check duplicates wrapper logic
2. Direct `_emit()` call bypasses PrintingOps formatting
3. No automatic dry-run marker in output
4. Violates the abstraction layer

**After fix (cleanup.py:58-59):**

```python
ctx.git_ops.checkout_branch(repo_root, trunk_branch)
```

Single line - the wrappers handle everything.

## When Subprocess Is Necessary

### Edge Case: Calling Other Workstack Commands

Some operations need to call other workstack commands via subprocess (e.g., `workstack sync`). These can't use the ops wrapper because they're separate CLI invocations.

**Pattern for subprocess with dry-run:**

```python
# From src/workstack/cli/commands/land_stack/cleanup.py:66-71
if dry_run:
    # Manual formatting to match PrintingOps pattern
    styled_cmd = click.style(f"  {base_cmd}", dim=True)
    dry_run_marker = click.style(" (dry run)", fg="bright_cyan", bold=True)
    checkmark = click.style(" ✓", fg="green")
    _emit(styled_cmd + dry_run_marker + checkmark, script_mode=script_mode)
else:
    subprocess.run(cmd, check=True, ...)
    _emit(_format_cli_command(base_cmd, check), script_mode=script_mode)
```

**When to use this pattern:**

- Only when calling external commands (other workstack commands, non-git tools)
- Never for operations that have corresponding ctx.ops methods
- Must manually replicate PrintingOps formatting for consistency

## Common Mistakes

### 1. Bypassing the Ops Layer

**Problem:** Directly checking `dry_run` and calling ops or skipping operations

**Example:**

```python
# ❌ WRONG
if not dry_run:
    ctx.git_ops.do_something()
```

**Solution:** Trust the wrappers

```python
# ✅ CORRECT
ctx.git_ops.do_something()
```

### 2. Custom Output Formatting

**Problem:** Using `_emit()` or `click.echo()` to print command output manually

**Example:**

```python
# ❌ WRONG
ctx.git_ops.checkout_branch(repo_root, branch)
_emit(f"Checked out {branch}")  # Custom formatting
```

**Solution:** Let PrintingOps handle output

```python
# ✅ CORRECT
ctx.git_ops.checkout_branch(repo_root, branch)
# PrintingOps automatically prints formatted output with dry-run marker
```

### 3. Inconsistent Dry-Run Markers

**Problem:** When subprocess is necessary, forgetting dry-run marker or using wrong style

**Example:**

```python
# ❌ WRONG
if dry_run:
    _emit(f"  {cmd} (dry-run) ✓")  # Wrong color, wrong marker text
```

**Solution:** Match PrintingOps pattern exactly

```python
# ✅ CORRECT
if dry_run:
    styled_cmd = click.style(f"  {cmd}", dim=True)
    dry_run_marker = click.style(" (dry run)", fg="bright_cyan", bold=True)
    checkmark = click.style(" ✓", fg="green")
    _emit(styled_cmd + dry_run_marker + checkmark, script_mode=script_mode)
```

## Testing Dry-Run Behavior

When implementing or testing dry-run functionality:

1. **Test both modes:** Verify command works correctly with and without `--dry-run`
2. **Verify no mutations:** In dry-run mode, check that no actual changes occur
3. **Check output markers:** Ensure all operations show bright cyan "(dry run)" marker
4. **Use existing tests:** See `tests/commands/land_stack/test_land_stack_dry_run.py` for examples

## Design Principles

1. **Trust the abstraction:** Once wrappers are set up, never manually check `dry_run`
2. **Use ctx.ops methods:** Always call operations through the context layer
3. **Consistent formatting:** Dry-run markers must always be bright cyan + bold
4. **Subprocess sparingly:** Only use direct subprocess for external commands
5. **Test thoroughly:** Both real and dry-run paths must be validated

## Reference Implementations

### Good Examples

- `src/workstack/cli/commands/land_stack/execution.py` - Correctly uses wrapped ops throughout
- `src/workstack/cli/commands/land_stack/command.py:100-118` - Proper wrapper setup
- `src/workstack/ops/printing_ops_base.py:45-54` - Automatic dry-run marker formatting

### Cautionary Example

- `src/workstack/cli/commands/land_stack/cleanup.py` (before fix) - Shows what happens when bypassing the abstraction

## Related Documentation

- [Testing patterns](testing.md) - How to test CLI commands with dry-run
- [Project glossary](glossary.md) - Term definitions
- [Documentation guide](guide.md) - Navigation
