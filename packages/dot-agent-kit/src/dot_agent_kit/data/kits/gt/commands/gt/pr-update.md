---
description: Update PR by staging changes, committing, restacking, and submitting
---

# Update PR

Streamlined workflow to update an existing PR with fail-fast execution and natural error messages.

## Usage

```bash
/gt:pr-update
```

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

- Update an existing PR with new changes
- Quick iteration on PR feedback
