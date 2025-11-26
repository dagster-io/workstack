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

Create a plan using Claude's ExitPlanMode tool. This stores the plan in session logs.

### 2. (Optional) Enrich the Plan

If you want to add semantic context and clarifications to your plan:

```bash
/erk:session-plan-enrich
```

This enriches the plan with 8 categories of context and interactive clarifications. You can iterate:

```bash
/erk:session-plan-enrich "Add retry logic"
```

### 3. Save to GitHub Issue

Save the plan (raw or enriched) to a GitHub issue:

```bash
/erk:plan-save
```

This creates a GitHub issue with the plan content and the `erk-plan` label. The issue becomes the source of truth.

**Note:** `/erk:plan-save` saves whatever is in session logs - run `/erk:session-plan-enrich` first if you want enrichment.

### 4. Implement from Issue

Use the unified `erk implement` command to create a worktree and start implementation:

```bash
erk implement <issue-number>
```

This command:

- Creates a dedicated worktree for the issue
- Sets up the `.impl/` folder with plan content from the issue
- Links the worktree to the GitHub issue for progress tracking
- Automatically switches to the new worktree

### 5. Execute the Plan (if not auto-implemented)

If you didn't use `erk implement` (which auto-implements), run the implementation command manually:

```bash
/erk:plan-implement
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

## Remote Implementation via GitHub Actions

For automated implementation via GitHub Actions, use `erk submit`:

```bash
erk submit <issue-number>
```

This command:

- Validates the issue has the `erk-plan` label
- Verifies the issue is OPEN (not closed)
- Triggers the `dispatch-erk-queue.yml` GitHub Actions workflow via direct workflow dispatch
- Displays the workflow run URL

The GitHub Actions workflow will:

1. Create a dedicated branch from trunk
2. Set up the `.erp/` folder with the plan from the issue
3. Create a draft PR
4. Execute the implementation automatically
5. Mark the PR as ready for review

**Monitor workflow progress:**

```bash
# List workflow runs
gh run list --workflow=dispatch-erk-queue.yml

# Watch latest run
gh run watch
```

## Commands Reference

### Plan Enrichment (Optional)

- `/erk:session-plan-enrich [guidance]` - Enrich plan from current session with context extraction
- `/erk:plan-enrich <issue>` - Enrich plan from GitHub issue with context extraction

### Plan Saving

- `/erk:plan-save` - Save plan from session logs to GitHub issue (no enrichment - use enrich commands first)

### Implementation (Issue-Based)

- `erk implement <issue>` - Create worktree and implement plan from GitHub issue
- `/erk:plan-implement` - Execute plan in current worktree (called by `erk implement`)
