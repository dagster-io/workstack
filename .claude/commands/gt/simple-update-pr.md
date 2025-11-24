---
description: Simplified Graphite update-pr for testing
---

# Simplified Update-PR

Streamlined alternative to `/gt:update-pr` with fail-fast execution and natural error messages.

## Usage

```bash
/gt:simple-update-pr
```

## Comparison

| Aspect      | Simple  | Standard |
| ----------- | ------- | -------- |
| Python code | ~70 LOC | 173 LOC  |
| Agent docs  | ~80 LOC | 175 LOC  |
| Error types | Natural | 4 types  |
| Token usage | -60%    | Baseline |

## Output

**Success:**

```json
{
  "success": true,
  "pr_number": 123,
  "pr_url": "https://github.com/org/repo/pull/123"
}
```

**Error:**

```json
{
  "success": false,
  "error": "No PR associated with current branch"
}
```

## When to Use

- Standard update workflows
- Prefer faster Claude interaction
- Natural error messages sufficient
