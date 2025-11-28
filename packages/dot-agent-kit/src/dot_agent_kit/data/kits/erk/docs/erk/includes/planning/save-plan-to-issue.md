# Save Plan to GitHub Issue

Use the kit CLI to create the GitHub issue with proper schema v2 formatting:

```bash
# Call the kit CLI command
# This handles: metadata in body disclosure, plan in first comment disclosure
result=$(dot-agent run erk plan-save-to-issue --format json 2>&1)
```

**Parse the result:**

```bash
# Check if command succeeded
if echo "$result" | jq -e '.success' > /dev/null 2>&1; then
    # SUCCESS - extract values
    issue_number=$(echo "$result" | jq -r '.issue_number')
    issue_url=$(echo "$result" | jq -r '.issue_url')
    title=$(echo "$result" | jq -r '.title')
    enriched=$(echo "$result" | jq -r '.enriched')
else
    # FAILURE - extract error message
    error_msg=$(echo "$result" | jq -r '.error // "Unknown error"')
    echo "❌ Error: $error_msg"
fi
```

**Expected success output:**

```json
{
  "success": true,
  "issue_number": 123,
  "issue_url": "https://github.com/owner/repo/issues/123",
  "title": "Plan Title",
  "enriched": false
}
```

**What the kit CLI handles:**

- Schema v2 format (metadata in body with disclosure triangle)
- Plan content in first comment (with disclosure triangle)
- Proper `erk-plan` label creation
- GitHub username lookup for metadata

**Error handling:**

The kit CLI returns JSON with error details on failure:

```json
{
  "success": false,
  "error": "No plan found in ~/.claude/plans/"
}
```

Common error causes:

- No plan in `~/.claude/plans/` directory
- Repository has issues disabled
- Network connectivity issue
- GitHub API rate limit
