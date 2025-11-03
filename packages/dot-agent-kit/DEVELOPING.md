# Kit Development Workflow

Guide for workstack repository developers editing bundled kits.

## Overview

This document describes the workflow for editing kit files that are bundled with dot-agent-kit. This workflow is **only relevant for developers working in the workstack repository** who are modifying the kits in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`.

For creating new kits from scratch, see [README.md](README.md).

## Quick Reference

| Step | Action                                          | Command                          |
| ---- | ----------------------------------------------- | -------------------------------- |
| 1    | Edit `.claude/` files directly in your worktree | _(use your editor)_              |
| 2    | Test and iterate on changes                     | _(use kit artifacts normally)_   |
| 3    | Commit your changes                             | `git add .claude/ && git commit` |
| 4    | Sync changes back to kit source                 | `workstack-dev kit-sync-back`    |

⚠️ **DO NOT** run `dot-agent kit sync` during active development - it will overwrite your `.claude/` edits!

## The Development Workflow

When editing bundled kits in the workstack repository, follow this workflow:

### 1. Edit .claude Files Directly

Edit the kit files in `.claude/` within your worktree. These are the installed artifacts:

```bash
# Example: Edit a skill file
vim .claude/skills/gt-graphite/SKILL.md

# Example: Edit a hook
vim .claude/hooks/dignified-python/suggest-dignified-python.py
```

### 2. Test and Iterate

Use the artifacts normally to test your changes. Claude Code reads from `.claude/`, so your edits take effect immediately.

### 3. Commit Your Changes

Commit the edited `.claude/` files to git:

```bash
git add .claude/
git commit -m "Update gt-graphite skill with new examples"
```

**Important**: Commit your `.claude/` changes before running `kit-sync-back`. This ensures you have a git history of your edits before they're copied to the kit source.

### 4. Sync Back to Kit Source

Run `workstack-dev kit-sync-back` to copy your changes from `.claude/` back to the kit source in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`:

```bash
workstack-dev kit-sync-back
```

This copies your `.claude/` edits back to the authoritative source location so they're included in the next kit distribution.

## kit-sync-back Command Reference

### What It Does

`kit-sync-back` syncs files from `.claude/` back to their source location:

```
.claude/skills/gt-graphite/SKILL.md
  ↓
packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/skills/gt-graphite/SKILL.md
```

This includes:

- Main artifact files (SKILL.md, AGENT.md, command files)
- Subdirectories (`references/`, `scripts/`)
- All files in artifact directories

### Command Options

```bash
workstack-dev kit-sync-back [OPTIONS]
```

| Option       | Description                                         |
| ------------ | --------------------------------------------------- |
| `--kit TEXT` | Sync only a specific kit (e.g., `--kit gt`)         |
| `--dry-run`  | Preview what would be synced without making changes |
| `--verbose`  | Show detailed output for each file                  |

### Examples

**Sync all kits:**

```bash
workstack-dev kit-sync-back
```

**Sync only the gt kit:**

```bash
workstack-dev kit-sync-back --kit gt
```

**Preview changes without syncing:**

```bash
workstack-dev kit-sync-back --dry-run
```

**Sync with detailed output:**

```bash
workstack-dev kit-sync-back --verbose
```

## ⚠️ Critical Warning: DO NOT Use `dot-agent kit sync`

**NEVER run `dot-agent kit sync` while actively developing kit files.**

```bash
# ❌ WRONG - This will OVERWRITE your .claude/ edits!
dot-agent kit sync
```

### Why This Matters

- `dot-agent kit sync` copies FROM kit source TO `.claude/`
- It will overwrite any uncommitted changes you made in `.claude/`
- You'll lose your work if you haven't run `kit-sync-back` first

### The Correct Direction

```
During development:
  .claude/ → packages/  (using kit-sync-back)

During distribution/installation:
  packages/ → .claude/  (using dot-agent kit sync)
```

### When Is `dot-agent kit sync` Safe?

Only run `dot-agent kit sync` when:

- You've already run `kit-sync-back` and all changes are in kit source
- You want to test a fresh installation from kit source
- You're intentionally discarding `.claude/` changes

## When This Workflow Matters

This workflow is **only necessary for workstack repository developers** editing bundled kits.

**You need this workflow if:**

- You're working in the workstack repository
- You're editing kits in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`
- You're modifying bundled skills, agents, or commands

**You don't need this workflow if:**

- You're a user installing kits from packages
- You're creating new kits from scratch (see [README.md](README.md))
- You're editing project-local `.claude/` files that aren't from kits

## Related Documentation

- [README.md](README.md) - Kit structure and creation guide
- [../../docs/WORKSTACK_DEV.md](../../docs/WORKSTACK_DEV.md) - workstack-dev CLI architecture
