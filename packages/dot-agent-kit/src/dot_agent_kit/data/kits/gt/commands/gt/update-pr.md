---
description: Update PR by staging changes, committing, restacking, and submitting
---

# Update PR

Streamlines updating an existing PR in a Graphite stack by auto-staging and committing changes, restacking the stack, and submitting updates.

## What This Command Does

1. **Check PR exists**: Verifies current branch has an associated PR
2. **Auto-stage and commit**: Commits any uncommitted changes with default message
3. **Restack**: Restacks the branch with conflict detection
4. **Submit**: Updates the existing PR

## Usage

```bash
/gt:update-pr
```

## Implementation

This command delegates to the `gt-update-pr-submitter` agent to handle the complete workflow:

```
Task(
    subagent_type="gt-update-pr-submitter",
    description="Update PR workflow",
    prompt="Execute the complete update-pr workflow for the current branch",
    model="haiku"
)
```

The agent will:

1. Run the `dot-agent run gt update-pr` command
2. Parse the JSON output
3. Handle any errors with clear guidance
4. Display results showing PR status

## Notes

- Uses simple default commit message: "Update changes"
- Does NOT use AI-generated commit messages (optimized for speed)
- Aborts immediately on restack conflicts - requires manual resolution
- Uses `gh` CLI to check PR existence (requires GitHub CLI authentication)
- Uses `gt` CLI for restack and submit operations
