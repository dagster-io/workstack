# Split Command

The split command creates individual worktrees for each branch in a Graphite stack, implementing the ephemeral worktree pattern. It's the inverse of the consolidate command.

## Overview

Split takes a consolidated worktree (where multiple branches exist in one worktree via `gt stack checkout`) and creates individual worktrees for each branch. This allows parallel development across multiple branches in a stack.

## Module Structure

- `command.py` - CLI entry point, validation, and orchestration
- `plan.py` - Models, planning logic, and worktree creation
- `display.py` - Output formatting and user interaction

## Key Concepts

### Exclusions

The split command automatically excludes:

- **Trunk branch** (main/master) - stays in the root worktree
- **Current branch** - already checked out, can't have duplicate worktrees
- **Existing worktrees** - idempotent operation, preserves existing worktrees

### Stack Filtering

- `--up` - Split only upstack (current branch to leaf)
- `--down` - Split only downstack (trunk to current branch)
- Default - Split entire stack (trunk to leaf)

## Workflow Phases

1. **Validation** - Check flags, trunk availability, uncommitted changes
2. **Discovery** - Get Graphite stack branches
3. **Filtering** - Apply --up/--down filters
4. **Planning** - Identify branches needing worktrees
5. **Preview** - Show what will be created
6. **Confirmation** - User approval (unless --force or --dry-run)
7. **Execution** - Create worktrees
8. **Results** - Display what was created

## Usage Examples

```bash
# Split full stack into worktrees
workstack split

# Split only upstack branches
workstack split --up

# Preview without creating
workstack split --dry-run

# Skip confirmation
workstack split --force
```

## Integration

The split command integrates with:

- **Graphite** - Uses gt to determine stack structure
- **Git worktrees** - Creates standard git worktrees
- **Workstacks directory** - Places worktrees in `.workstacks/`
