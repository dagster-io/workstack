# Shared Plan-Save Workflow

This document contains workflow steps shared between `/erk:plan-save` (enriched mode) and `/erk:plan-save-raw` (raw mode). Both commands use the same agent-based architecture with structural enforcement.

## Shared Step: Validate Prerequisites

Check that prerequisites are met:

```bash
# Verify we're in a git repository
git rev-parse --is-inside-work-tree

# Verify GitHub CLI is authenticated
gh auth status
```

**Error handling:**

If `git rev-parse` fails:

```
❌ Error: Not in a git repository

This command must be run from within a git repository.
```

If `gh auth status` fails:

```
❌ Error: GitHub CLI not authenticated

Run: gh auth login
```

## Shared Step: Parse Agent Response

The agent returns markdown in this format:

```markdown
# Plan: [title extracted from plan]

## Enrichment Details

### Process Summary

- **Mode**: enriched | raw
- **Guidance applied**: yes/no
- **Questions asked**: N
- **Context categories extracted**: N of 8

---

[Full plan content...]
```

**Parse markdown response:**

```bash
# Check for error
if echo "$result" | grep -q "^## Error:"; then
    # Extract error message
    error_msg=$(echo "$result" | sed -n 's/^## Error: //p')
    echo "❌ Error: $error_msg"
    exit 1
fi

# Extract title from first heading
plan_title=$(echo "$result" | grep -m1 "^# Plan:" | sed 's/^# Plan: //')

# Use full content for issue
plan_content="$result"
```

**Validation:**

- Check for `## Error:` prefix (indicates error)
- Ensure `# Plan:` heading exists
- Verify content is non-empty

**Error handling:**

If error prefix found:

```
❌ Error: [error message from markdown]
```

If no `# Plan:` heading:

```
❌ Error: Agent returned invalid markdown (missing # Plan: heading)

[Display agent response for debugging]
```

## Shared Step: Save Plan to Temporary File

Write plan content to a temporary file for kit CLI:

```bash
# Create temp file
temp_plan=$(mktemp)

# Write plan content
cat > "$temp_plan" <<'PLAN_EOF'
[plan_content from agent]
PLAN_EOF
```

**Why temp file:** Kit CLI command expects `--plan-file` option for clean separation of concerns.

## Shared Step: Create GitHub Issue via Kit CLI

Call the kit CLI command to create the issue:

```bash
# Call kit CLI with plan file
result=$(dot-agent run erk create-enriched-plan-from-context --plan-file "$temp_plan")

# Clean up temp file
rm "$temp_plan"

# Parse JSON result
echo "$result" | jq .
```

**Expected output:**

```json
{
  "success": true,
  "issue_number": 123,
  "issue_url": "https://github.com/owner/repo/issues/123"
}
```

**Error handling:**

If command fails:

```
❌ Error: Failed to create GitHub issue

[Display kit CLI error output]
```

## Shared Step: Display Issue URL and Next Steps

Show the user the issue URL and copy-pastable commands:

```
✅ Plan saved to GitHub issue

**Issue:** [issue_url]

**Next steps:**

View the plan:
    gh issue view [issue_number]

Implement directly:
    erk implement [issue_number]

Implement with auto-confirmation (yolo mode):
    erk implement [issue_number] --yolo

Implement and auto-submit PR (dangerous mode):
    erk implement [issue_number] --dangerous

Submit plan to erk queue:
    erk submit [issue_number]
```

**Formatting requirements:**

- Use `✅` for success indicator
- Bold `**Issue:**` and `**Next steps:**`
- Show actual issue URL (clickable)
- Show actual issue number in commands (not `<issue-number>`)
- Each command should be on its own line with proper indentation
- Commands should be copy-pastable (no markdown formatting inside)

## Shared Architecture Benefits

| Aspect         | Previous Design       | Current Design                   |
| -------------- | --------------------- | -------------------------------- |
| Enforcement    | Text warnings         | Structural (tool restrictions)   |
| Implementation | Inline command logic  | Dedicated agent                  |
| Safety         | Behavioral compliance | Physically impossible to violate |
| Bypass-safe    | No                    | Yes                              |

**Key Innovation:** The agent has **tool restrictions** in YAML front matter that make it **structurally impossible** to accidentally edit files, even with bypass permissions enabled.

## Shared Error Scenarios

### GitHub CLI Not Authenticated

```
❌ Error: GitHub CLI not authenticated

To use this command, authenticate with GitHub:

    gh auth login

Then try again.
```

### Kit CLI Error

```
❌ Error: Failed to create GitHub issue

[Full kit CLI error output]

Common causes:
- Repository has issues disabled
- Network connectivity issue
- GitHub API rate limit
```

## Shared Troubleshooting

### "Agent returned error"

**Cause:** Agent encountered issue during extraction/enrichment
**Solution:**

- Check agent error message for details
- Ensure plan is in conversation context or session logs
- Verify plan has clear structure

### "Invalid markdown from agent"

**Cause:** Agent output malformed or unexpected
**Solution:**

- Check agent output for debugging
- Retry command
- Report issue if persistent

### "Temp file error"

**Cause:** Cannot create temporary file (permissions, disk space)
**Solution:**

- Check temporary directory permissions
- Ensure disk space available
- Check `mktemp` command availability
