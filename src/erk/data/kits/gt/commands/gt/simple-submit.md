---
description: Simplified Graphite submit for testing
argument-hint: <description>
---

# Simplified Graphite Submit

A drastically simplified version of the Graphite submission workflow designed for speed and comparison testing against the complex implementation.

## Usage

```
/gt:simple-submit [description]
```

## Purpose

This command provides a streamlined alternative to `/gt:submit-squashed-branch` with:

- Single-phase execution (no pre/post analysis separation)
- Direct error messages (no categorized JSON error types)
- Minimal token usage (concise agent responses)
- Fast execution (<30 seconds typical)

## How It Works

1. Commits any uncommitted changes
2. Checks for .impl/issue.json (created by erk worktree workflows)
3. Restacks the branch
4. Gets diff for analysis
5. Generates a commit message with issue linking
6. Amends commit and submits PR with "Closes #N" in body

The entire workflow is handled by the `gt-simple-submitter` agent which prioritizes speed and simplicity over comprehensive error handling.

## GitHub Issue Linking

When working in a worktree created from a GitHub issue (via `erk create` or related commands), this command automatically links the PR to the original issue:

- Reads issue number from `.impl/issue.json`
- Adds "Closes #<issue-number>" to both PR body and commit message
- GitHub will auto-close the issue when PR is merged

If `.impl/issue.json` doesn't exist, the command continues normally without issue linking.

## Implementation

This command delegates to the `gt-simple-submitter` agent to handle the complete workflow:

```
Task(
    subagent_type="gt-simple-submitter",
    description="Simple Graphite submit",
    prompt=f"Execute simplified Graphite submit workflow. Description: {description or 'Submit changes'}",
    model="haiku"
)
```

The agent will:

1. Commit any uncommitted changes with the provided description
2. Check for linked GitHub issue in .impl/issue.json
3. Restack the branch to ensure clean state
4. Get the diff for analysis
5. Generate a simple, direct commit message based on the changes
6. Add "Closes #N" to commit message if issue found
7. Amend the commit with the final message
8. Submit the PR using Graphite's squash and restack
9. Update PR body with "Closes #N" if issue found

All gt commands run non-interactively with appropriate flags. The agent prioritizes speed and directness over complex error recovery.

## Comparison with Complex Version

| Aspect         | Simple Version   | Complex Version           |
| -------------- | ---------------- | ------------------------- |
| Lines of code  | ~250             | 580+                      |
| Agent size     | ~150 lines       | 520+ lines                |
| Error types    | Natural messages | 10+ categorized types     |
| Execution time | <30 seconds\*    | 4+ minutes                |
| Token usage    | Minimal          | Extensive                 |
| Error recovery | Fail fast        | Multiple retry strategies |
| Issue linking  | ✅ Yes           | ✅ Yes                    |

\*Note: Execution time may increase slightly (~1s) when validating GitHub issues

## When to Use

Use this simplified version when:

- You want fast PR submission
- The branch is in a clean state
- You don't need detailed error recovery guidance
- You're testing or comparing implementations

## Example

```
/gt:simple-submit "Add user authentication feature"
```

This will:

1. Commit any changes with initial message
2. Check for linked GitHub issue and validate it
3. Restack the branch
4. Generate a proper commit message based on the diff
5. Add "Closes #N" if issue found
6. Submit the PR with issue linking

## Notes

- Automatically links to GitHub issues when working in erk-created worktrees
- Issue linking is transparent - no user action required if .impl/issue.json exists
- If issue.json is missing or malformed, command continues without issue linking
- This is an experimental implementation for testing
- Designed to coexist with the existing complex implementation
- Focuses on the happy path with minimal error handling
