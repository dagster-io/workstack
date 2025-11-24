---
description: Simplified Graphite submit for testing
argument-hint: <description>
---

# Simplified Graphite Submit

Streamlined alternative to `/gt:submit-squashed-branch` optimized for speed (<30s typical).

## Usage

```
/gt:simple-submit [description]
```

## How It Works

1. Commits any uncommitted changes
2. Checks for `.impl/issue.json` (from erk workflows)
3. Restacks the branch
4. Gets diff and generates commit message
5. Amends commit and submits PR
6. Automatically adds "Closes #N" if issue found

## GitHub Issue Linking

When working in a worktree created from a GitHub issue:

- Reads issue number from `.impl/issue.json`
- Adds "Closes #N" to PR body and commit message
- GitHub auto-closes issue on merge

If no `.impl/issue.json`, command continues without issue linking.

## Implementation

Delegates to `gt-simple-submitter` agent using haiku model for fast execution.

## Comparison with Complex Version

| Aspect         | Simple    | Complex |
| -------------- | --------- | ------- |
| Lines of code  | ~250      | 580+    |
| Execution time | <30s      | 4+ min  |
| Error recovery | Fail-fast | Retries |

## When to Use

- Fast PR submission needed
- Branch in clean state
- Don't need detailed error recovery

## Example

```
/gt:simple-submit "Add user authentication feature"
```
