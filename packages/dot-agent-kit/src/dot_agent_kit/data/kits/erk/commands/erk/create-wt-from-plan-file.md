---
description: Create worktree from existing plan file on disk
---

# /erk:create-wt-from-plan-file

⚠️ **DEPRECATED**: This command is deprecated. Use `erk implement <issue>` instead, which creates worktrees directly from GitHub issues.

This command remains functional for backward compatibility with existing plan files on disk.

Create an erk worktree from an existing plan file on disk.

## Usage

```bash
/erk:create-wt-from-plan-file
```

## What This Command Does

Delegates the complete worktree creation workflow to the `planned-wt-creator` agent, which handles:

1. Auto-detect most recent `*-plan.md` file at repository root
2. Validate plan file (exists, readable, not empty)
3. Run `erk create --from-plan <file>` with JSON output
4. Display plan location and next steps

## Prerequisites

- At least one `*-plan.md` file at repository root
- Current working directory in a git repository
- Typically run after `/erk:save-context-enriched-plan`

## Implementation

When this command is invoked, delegate to the planned-wt-creator agent:

```
Task(
    subagent_type="planned-wt-creator",
    description="Create worktree from plan",
    prompt="Execute the complete planned worktree creation workflow"
)
```

The agent handles all workflow orchestration, error handling, and result reporting.
