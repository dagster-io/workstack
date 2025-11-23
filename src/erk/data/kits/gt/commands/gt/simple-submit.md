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
2. Restacks the branch
3. Gets diff for analysis
4. Generates a commit message
5. Amends commit and submits PR

The entire workflow is handled by the `gt-simple-submitter` agent which prioritizes speed and simplicity over comprehensive error handling.

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
2. Restack the branch to ensure clean state
3. Get the diff for analysis
4. Generate a simple, direct commit message based on the changes
5. Amend the commit with the final message
6. Submit the PR using Graphite's squash and restack

All gt commands run non-interactively with appropriate flags. The agent prioritizes speed and directness over complex error recovery.

## Comparison with Complex Version

| Aspect         | Simple Version   | Complex Version           |
| -------------- | ---------------- | ------------------------- |
| Lines of code  | ~200             | 580+                      |
| Agent size     | ~100 lines       | 520+ lines                |
| Error types    | Natural messages | 10+ categorized types     |
| Execution time | <30 seconds      | 4+ minutes                |
| Token usage    | Minimal          | Extensive                 |
| Error recovery | None (fail fast) | Multiple retry strategies |

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
2. Restack the branch
3. Generate a proper commit message based on the diff
4. Submit the PR with the final message

## Notes

- This is an experimental implementation for testing
- Designed to coexist with the existing complex implementation
- Focuses on the happy path with minimal error handling
- Helps determine if complex error handling adds value
