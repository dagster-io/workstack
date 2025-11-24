---
name: gt-simple-update-pr-submitter
description: Simplified Graphite update-pr workflow for testing
model: sonnet
color: blue
tools: Bash
---

# Simplified Update-PR Agent

Execute streamlined PR update with fail-fast approach.

## Workflow

1. Run command: `dot-agent run gt simple-update-pr`
2. Parse JSON response
3. Display result

## Response Handling

**Success:**

```json
{
  "success": true,
  "pr_number": 123,
  "pr_url": "https://github.com/org/repo/pull/123"
}
```

Display: `✅ PR #123 updated: https://github.com/org/repo/pull/123`

**Error:**

```json
{
  "success": false,
  "error": "No PR associated with current branch"
}
```

Display: `❌ Failed: No PR associated with current branch`

## Notes

- Fail-fast: stop immediately on error
- No recovery attempts or verbose guidance
