# Forest Commands

Unified stack management for erk worktrees.

## Overview

Forests are named collections of worktrees belonging to the same Graphite stack. They enable:

- **Split**: Convert single worktree into forest of individual worktrees
- **Merge**: Consolidate forest into single worktree
- **Reroot**: Conflict-preserving rebase for entire stack
- **Automatic lifecycle**: Creation, cleanup, and membership management

## Requirements

- Graphite must be enabled: `erk config set use-graphite true`
- All branches must have worktrees (for reroot operations)
- Clean working directory (no uncommitted changes for reroot)

## Commands

### Query Commands

#### `erk forest`

Show forest for current worktree with tree structure.

```bash
$ erk forest
Forest: auth (3 worktrees)
├── auth-redesign [auth-redesign] ← you are here
├── add-oauth [add-oauth]
└── add-2fa [add-2fa]
```

#### `erk forest list`

List all forests in repository with creation dates.

```bash
$ erk forest list
Forests in my-project:
• auth-redesign (3 worktrees) - created 2024-01-15
• perf-work (2 worktrees) - created 2024-01-16
```

#### `erk forest show [NAME]`

Show specific forest (defaults to current worktree's forest).

#### `erk forest rename OLD NEW`

Rename forest (label only, paths unchanged).

**Important**: Renaming changes only the metadata label. Worktree paths remain stable.

### Split Operation

Convert single worktree containing multiple branches into forest with individual worktrees.

```bash
$ erk forest split [FOREST_NAME]
```

**Options**:

- `--up`: Only split upstack branches (toward leaves)
- `--down`: Only split downstack branches (toward trunk)
- `--force`: Skip confirmation
- `--dry-run`: Preview without executing

**Example**:

```bash
$ erk forest split
Current worktree 'auth' contains 3 branches.
Forest 'auth' will contain 3 worktrees:
  • auth-redesign [auth-redesign] (current)
  • add-oauth [add-oauth] (new)
  • add-2fa [add-2fa] (new)

Continue? [y/N]: y
```

### Merge Operation

Consolidate forest into single worktree by removing all worktrees except target.

```bash
$ erk forest merge [FOREST_NAME]
```

**Options**:

- `--into WORKTREE`: Specify target worktree to keep
- `--force`: Skip confirmation
- `--dry-run`: Preview without executing

**Default target**: Current worktree (if in forest) or first worktree.

**Example**:

```bash
$ erk forest merge auth
This will merge forest 'auth' (3 worktrees) into worktree 'auth-redesign'.
Worktrees to be removed:
  • add-oauth
  • add-2fa

Continue? [y/N]: y
```

### Reroot Operation

Conflict-preserving rebase for entire stack.

#### Starting a Rebase

```bash
$ erk forest reroot [FOREST_NAME]
```

Pre-flight checks:

1. Graphite enabled
2. Clean working directory
3. All branches have worktrees

The command displays stack preview and runs pre-flight checks before confirmation.

#### When Conflicts Occur

Reroot pauses on conflicts and prompts whether to commit conflict state:

```
⚠️  Conflicts detected in branch: feature-1

Conflicted files (3):
  - src/main.py (UU - both modified)
  - src/utils.py (UU - both modified)
  - tests/test_main.py (AU - added by us, modified by them)

Commit conflict state to preserve in history? [Y/n]: y
Creating conflict commit: [CONFLICT] Rebase conflicts from main (abc1234)
  ✅ Conflict commit created
  ✅ Progress saved

Next steps:
1. Resolve conflicts in the files listed above
2. Run: erk forest reroot --continue

ℹ️  Current worktree: /Users/you/.erk/repos/myproject/worktrees/feature-1
```

#### Resolving Conflicts

After manually resolving conflicts:

```bash
$ erk forest reroot --continue
```

This creates a `[RESOLVED]` commit and continues with remaining branches.

#### Abort Workflow

To abort an in-progress reroot:

```bash
$ erk forest reroot --abort
```

Runs `git rebase --abort` and cleans up state files.

## Automatic Lifecycle

### Auto-Creation

Forests are created silently when:

1. Creating branch from trunk: `erk create <name>` → new forest
2. Creating branch from forest member: `erk create -s <name>` → joins forest

No explicit forest creation needed.

### Auto-Cleanup

Empty forests (zero worktrees) are automatically deleted during `erk sync`.

## Git History After Rebase

Conflict commits preserve exact conflict state:

```bash
$ git log --oneline
abc1234 [RESOLVED] Fix rebase conflicts from main (abc1234)
def5678 [CONFLICT] Rebase conflicts from main (abc1234)
```

View conflict state:

```bash
$ git show def5678
```

View resolution:

```bash
$ git show abc1234
```

Compare before/after:

```bash
$ git diff def5678 abc1234
```

## Common Errors

### "This command requires Graphite"

**Solution**: `erk config set use-graphite true`

### "Uncommitted changes detected"

**Solution**: Commit or stash changes before reroot

```bash
$ git add . && git commit -m "WIP"
# or
$ git stash
```

### "The following branches do not have worktrees"

**Solution**: Create worktrees for missing branches

```bash
$ erk create feature-1
$ erk create feature-2
```

### "No rebase state found" (on --continue)

**Solution**: Start new rebase instead

```bash
$ erk forest reroot
```

## Design Rationale

### Why forests are labels not filesystem structures

Forest names are pure metadata labels. Renaming never moves worktrees because:

- Prevents breaking tools/scripts that depend on stable paths
- Separation of logical grouping from physical storage
- Simpler consistency model

### Why auto-creation is silent

Forest concept should be invisible until explicitly needed:

- Users just create branches normally
- Forests emerge naturally from stack structure
- Reduces cognitive overhead

### Why conflict commits are optional

User confirmation prompt (not automatic) because:

- Some users may prefer clean history
- Allows case-by-case decisions
- Explicit consent for history modification

## Migration from Split/Consolidate

Old commands have been replaced:

- `erk split` → `erk forest split`
- `erk consolidate` → `erk forest merge`

**Key difference**: The `--name` flag is gone. Forest names are managed automatically.
