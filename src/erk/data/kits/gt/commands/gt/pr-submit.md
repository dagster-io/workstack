---
description: Create git commit and submit current branch with Graphite (squashes commits and rebases stack)
argument-hint: <description>
---

# Submit PR (Graphite)

Automatically create a commit with AI-generated message and submit as PR.

**Note:** This command squashes commits and rebases the stack. If you prefer a simpler workflow that preserves your commit history, use `/git:pr-push` instead.

## Usage

```bash
/gt:pr-submit
```

The optional `<description>` argument is now deprecated (AI analyzes the full diff).

## What This Command Does

1. **Pre-analysis**: Check auth, commit uncommitted changes, squash commits
2. **Diff extraction**: Get full diff for analysis
3. **AI message generation**: Claude analyzes diff, creates commit message
4. **Submission**: Amend commit, run `gt submit`, update PR metadata

All orchestrated in Python - agent only generates the commit message.

## Implementation

Execute the Python orchestration workflow:

```
Bash(
    command="dot-agent run gt submit-pr orchestrate",
    description="Submit PR with orchestrated workflow"
)
```
