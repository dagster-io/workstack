---
description: Create worktree from GitHub issue with erk-plan label
---

# /erk:create-wt-from-plan-issue

Create an erk worktree from a GitHub issue containing an implementation plan.

## Usage

```bash
/erk:create-wt-from-plan-issue <issue-number-or-url> [worktree-name]
```

**Arguments:**

- `issue-number-or-url`: GitHub issue number (e.g., 123) or full URL
- `worktree-name` (optional): Pre-generated worktree name. If not provided, will be auto-generated from issue title.

**Examples:**

```bash
# Auto-generate worktree name from issue title
/erk:create-wt-from-plan-issue 123

# Use pre-generated worktree name (from plan issue comment)
/erk:create-wt-from-plan-issue 123 add-user-authentication

# Using GitHub URL with auto-generated name
/erk:create-wt-from-plan-issue https://github.com/owner/repo/issues/123

# Using GitHub URL with pre-generated name
/erk:create-wt-from-plan-issue https://github.com/owner/repo/issues/123 add-user-authentication
```

## What This Command Does

Delegates the complete worktree creation workflow to the `issue-wt-creator` agent, which handles:

1. Parse issue number from argument (number or GitHub URL)
2. Fetch issue from GitHub via gh CLI
3. Validate issue has `erk-plan` label
4. Create worktree from issue body via `erk create --from-plan`
5. Save issue reference to `.impl/issue.json`
6. Display plan location and next steps

## Prerequisites

- GitHub issue must exist with `erk-plan` label
- gh CLI must be authenticated (`gh auth login`)
- Current working directory in a git repository

## Typical Workflow

```bash
# 1. Create issue on GitHub with erk-plan label (or use existing issue)

# 2. Create worktree from issue
/erk:create-wt-from-plan-issue 123

# 3. Navigate to worktree and implement
erk checkout <branch-name>
claude --permission-mode acceptEdits "/erk:implement-plan"
```

## Comparison with Other Commands

| Command                              | Source            | Creates Worktree?      | Next Step                    |
| ------------------------------------ | ----------------- | ---------------------- | ---------------------------- |
| `/erk:create-wt-from-plan-file`      | Plan file on disk | ✅ Yes                 | Manual `/erk:implement-plan` |
| **`/erk:create-wt-from-plan-issue`** | GitHub issue      | ✅ Yes                 | Manual `/erk:implement-plan` |
| `/erk:implement-plan-issue`          | GitHub issue      | ❌ No (assumes exists) | Auto-starts implementation   |

## Implementation

When this command is invoked, delegate to the issue-wt-creator agent:

```
Task(
    subagent_type="issue-wt-creator",
    description="Create worktree from issue plan",
    prompt="Execute the complete issue worktree creation workflow for issue: {issue} [with worktree name: {worktree_name}]"
)
```

The agent handles all workflow orchestration, error handling, and result reporting.

**Note**: If worktree name is provided, include it in the prompt. The agent will use it directly instead of auto-generating from the issue title.
