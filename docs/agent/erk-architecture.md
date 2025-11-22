# Erk Architecture Patterns

This document describes the core architectural patterns specific to the erk codebase.

## Dry-Run via Dependency Injection

**This codebase uses dependency injection for dry-run mode, NOT boolean flags.**

🔴 **MUST**: Use DryRun wrappers for dry-run mode
🔴 **MUST NOT**: Pass dry_run flags through business logic functions
🟡 **SHOULD**: Keep dry-run UI logic at the CLI layer only

### Wrong Pattern

```python
# ❌ WRONG: Passing dry_run flag through business logic
def execute_plan(plan, git, dry_run=False):
    if not dry_run:
        git.add_worktree(...)
```

### Correct Pattern

```python
# ✅ CORRECT: Rely on injected integration implementation
def execute_plan(plan, git):
    # Always execute - behavior depends on git implementation
    git.add_worktree(...)  # DryRunGit does nothing, RealGit executes

# At the context creation level:
if dry_run:
    git = DryRunGit(real_git)  # or PrintingGit(DryRunGit(...))
else:
    git = real_git  # or PrintingGit(real_git)
```

### Rationale

- Keeps business logic pure and testable
- Dry-run behavior is determined by dependency injection
- No conditional logic scattered throughout the codebase
- Single responsibility: business logic doesn't know about UI modes

## Context Regeneration

**When to regenerate context:**

After filesystem mutations that invalidate `ctx.cwd`:

- After `os.chdir()` calls
- After worktree removal (if removed current directory)
- After switching repositories

### How to Regenerate

Use `regenerate_context()` from `erk.core.context`:

```python
from erk.core.context import regenerate_context

# After os.chdir()
os.chdir(new_directory)
ctx = regenerate_context(ctx, repo_root=repo.root)

# After worktree removal
if removed_current_worktree:
    os.chdir(safe_directory)
    ctx = regenerate_context(ctx, repo_root=repo.root)
```

### Why Regenerate

- `ctx.cwd` is captured once at CLI entry point
- After `os.chdir()`, `ctx.cwd` becomes stale
- Stale `ctx.cwd` causes `FileNotFoundError` in operations that use it
- Regeneration creates NEW context with fresh `cwd` and `trunk_branch`

## Subprocess Execution Wrappers

Erk uses a two-layer pattern for subprocess execution to provide consistent error handling:

- **Integration layer**: `run_subprocess_with_context()` - Raises RuntimeError for business logic
- **CLI layer**: `run_with_error_reporting()` - Prints user-friendly message and raises SystemExit

**Full guide**: See [subprocess-wrappers.md](subprocess-wrappers.md) for complete documentation and examples.

## Design Principles

These patterns reflect erk's core design principles:

1. **Dependency Injection over Configuration** - Behavior determined by what's injected, not flags
2. **Explicit Context Management** - Context must be regenerated when environment changes
3. **Layered Error Handling** - Different error handling at different architectural boundaries
4. **Testability First** - Patterns enable easy testing with fakes and mocks
