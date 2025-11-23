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

### 1. Create a Plan

Start by creating an enriched plan from your conversation:

```bash
/erk:save-context-enriched-plan
```

This creates a `.impl/` folder in the current directory with the implementation plan.

### 2. Create Worktree from Plan

Create a dedicated worktree for implementing the plan:

```bash
/erk:create-wt-from-plan-file
```

This creates a new worktree with the `.impl/` folder copied into it.

### 3. Switch to Worktree

Navigate to the newly created worktree:

```bash
erk checkout <branch-name>
```

### 4. Execute the Plan

Run the implementation command:

```bash
/erk:implement-plan
```

The agent reads `.impl/plan.md`, executes each phase, and updates `.impl/progress.md` as steps complete.

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

- `/erk:save-context-enriched-plan` - Create enriched plan from conversation
- `/erk:create-wt-from-plan-file` - Create worktree from plan on disk
- `/erk:implement-plan` - Execute plan in current worktree
