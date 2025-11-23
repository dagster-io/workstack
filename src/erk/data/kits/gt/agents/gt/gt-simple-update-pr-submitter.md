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

1. Run the command to update PR
2. Parse JSON response
3. Display result

## Execution

Run the simplified update-pr command:

```bash
dot-agent run gt simple-update-pr
```

## Response Handling

Parse the JSON response and display appropriate message:

**Success response:**
```json
{
  "success": true,
  "pr_number": 123,
  "pr_url": "https://github.com/org/repo/pull/123"
}
```

Display: `✅ PR #123 updated: https://github.com/org/repo/pull/123`

**Error response:**
```json
{
  "success": false,
  "error": "No PR associated with current branch"
}
```

Display: `❌ Failed: No PR associated with current branch`

## Complete Example

```bash
# Execute command
result=$(dot-agent run gt simple-update-pr)

# Check success
if echo "$result" | jq -e '.success' > /dev/null; then
  pr_number=$(echo "$result" | jq -r '.pr_number')
  pr_url=$(echo "$result" | jq -r '.pr_url')
  echo "✅ PR #${pr_number} updated: ${pr_url}"
else
  error=$(echo "$result" | jq -r '.error')
  echo "❌ Failed: ${error}"
fi
```

## Notes

- No error categorization needed
- No state tracking or conditional messages
- Natural error messages bubble up
- Fail-fast approach matches user preference