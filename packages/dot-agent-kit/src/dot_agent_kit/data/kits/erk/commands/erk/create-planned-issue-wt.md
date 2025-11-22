---
description: Create GitHub issue and worktree from persistent plan
---

# /erk:create-planned-issue-wt

Create both a GitHub issue and a worktree from an existing plan file on disk, linking them together.

## Usage

```bash
/erk:create-planned-issue-wt
```

## What This Command Does

Delegates the complete workflow to the `planned-issue-wt-creator` agent, which handles:

1. Auto-detect most recent `*-plan.md` file at repository root
2. Validate plan file (exists, readable, not empty)
3. Create worktree using `erk create --plan <file> --json --stay`
4. Create GitHub issue with plan content and `erk-plan` label
5. Link issue to worktree's `.plan/` folder
6. Display combined results with next steps

## Prerequisites

- At least one `*-plan.md` file at repository root
- Current working directory in a git repository
- `gh` CLI installed and authenticated
- Typically run after `/erk:save-context-enriched-plan`

## Optional Flags

- `--json` - Return structured JSON output instead of human-readable format

## Implementation

When this command is invoked, delegate to the planned-issue-wt-creator agent:

```
Task(
    subagent_type="planned-issue-wt-creator",
    model="haiku",
    description="Create issue and worktree",
    prompt="Execute the complete planned issue and worktree creation workflow. Parse arguments: --json flag if present. Return structured output."
)
```

The agent handles all workflow orchestration, error handling, and result reporting.
