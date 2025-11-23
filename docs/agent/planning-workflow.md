# Planning Workflow

This guide explains the `.impl/` folder protocol used in erk for managing implementation plans.

## Overview

Erk uses `.impl/` folders to track implementation progress for plans executed locally by agents.

## .impl/ Folders

**Purpose**: Track implementation progress for plans executed locally.

**Characteristics**:

- NOT tracked in git (in `.gitignore`)
- Created by planning commands
- Contains `plan.md`, `progress.md`, and optional `issue.json`
- Lives in worktree directory during implementation
- Never committed to repository

**Structure**:

```
.impl/
├── plan.md         # Immutable implementation plan
├── progress.md     # Mutable progress tracking (checkboxes)
└── issue.json      # Optional GitHub issue reference
```

## Local Implementation Workflow

### 1. Create a Plan and GitHub Issue

Start by creating an enriched plan from your conversation, which creates a GitHub issue directly:

```bash
/erk:save-context-enriched-plan
```

This creates a GitHub issue with the enhanced plan content and the `erk-plan` label. The issue becomes the source of truth.

### 2. Implement from Issue

Use the unified `erk implement` command to create a worktree and start implementation:

```bash
erk implement <issue-number>
```

This command:

- Creates a dedicated worktree for the issue
- Sets up the `.impl/` folder with plan content from the issue
- Links the worktree to the GitHub issue for progress tracking
- Automatically switches to the new worktree

### 3. Execute the Plan (if not auto-implemented)

If you didn't use `erk implement` (which auto-implements), run the implementation command manually:

```bash
/erk:implement-plan
```

The agent reads `.impl/plan.md`, executes each phase, and updates `.impl/progress.md` as steps complete.

## Alternative: File-Based Workflow (Deprecated)

For backward compatibility with existing plan files on disk, you can still use:

```bash
/erk:create-wt-from-plan-file  # Deprecated - use erk implement <issue> instead
```

This workflow is deprecated and will be removed in a future version.

## Progress Tracking

The `.impl/progress.md` file tracks completion status:

```markdown
---
completed_steps: 3
total_steps: 5
---

# Progress Tracking

- [x] 1. First step (completed)
- [x] 2. Second step (completed)
- [x] 3. Third step (completed)
- [ ] 4. Fourth step
- [ ] 5. Fifth step
```

The front matter enables progress indicators in `erk status` output.

## Important Notes

- **Never commit `.impl/` folders** - They're in `.gitignore` for a reason
- **Safe to delete after implementation** - Once the work is committed, `.impl/` can be removed
- **One plan per worktree** - Each worktree has its own `.impl/` folder

## .worker-impl/ Folders (Future)

`.worker-impl/` folders are purposely meant to be checked into git (not covered in this guide).

## Commands Reference

### Primary Workflow (Issue-Based)

- `/erk:save-context-enriched-plan` - Create GitHub issue with enriched plan from conversation
- `/erk:save-plan` - Create GitHub issue with basic plan (no enrichment)
- `/erk:save-session-enriched-plan` - Create GitHub issue with plan enhanced by session discoveries
- `erk implement <issue>` - Create worktree and implement plan from GitHub issue
- `/erk:implement-plan` - Execute plan in current worktree (called by `erk implement`)

### Deprecated Commands (File-Based)

- `/erk:create-wt-from-plan-file` - Create worktree from plan on disk (use `erk implement <issue>` instead)
- `/erk:create-plan-issue-from-plan-file` - Create issue from plan file (use save commands instead)
