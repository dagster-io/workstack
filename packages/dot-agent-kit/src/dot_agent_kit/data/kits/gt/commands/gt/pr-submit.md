---
description: Create git commit and submit current branch with Graphite (squashes commits and rebases stack)
argument-hint: <description>
---

# Submit PR

Automatically create a git commit with a helpful summary message and submit the current branch as a pull request.

**Note:** This command squashes commits and rebases the stack. If you prefer a simpler workflow that preserves your commit history, use `/git:pr-push` instead.

## Usage

```bash
# Invoke the command (description argument is optional but recommended)
/gt:pr-submit "Add user authentication feature"

# Without argument (will analyze changes automatically)
/gt:pr-submit
```

## What This Command Does

Executes the complete submit-branch workflow via Python kit CLI, which handles:

1. Check for uncommitted changes and commit them if needed
2. Run pre-analysis phase (squash commits, get branch info)
3. Analyze all changes and generate commit message via AI
4. Run post-analysis phase (amend commit, submit branch, update PR)
5. Report results

## Implementation

When this command is invoked, call the Python orchestration command:

```bash
dot-agent run gt pr-submit orchestrate
```

The Python CLI handles all workflow orchestration:

1. **Pre-analysis** (Python): Auth checks, commit uncommitted changes, squash commits
2. **Get diff context** (Python): Extract full diff vs parent branch
3. **Generate commit message** (AI): Invoke Claude via `claude --print` with Task delegation to commit-message-generator agent
4. **Post-analysis** (Python): Amend commit with message, submit via Graphite, update PR metadata

All phases are orchestrated in Python for testability and error handling. Only the commit message generation uses AI (via Claude CLI invocation).
