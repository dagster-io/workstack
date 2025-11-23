---
description: Extract plan from Claude session and create GitHub issue
---

# /erk:create-plan-issue-from-context

Extract the latest implementation plan from Claude session files and create a GitHub issue directly, without saving a plan file to disk. This provides a streamlined workflow for quick issue creation using deterministic session file parsing.

## Usage

```bash
/erk:create-plan-issue-from-context
```

**No arguments accepted** - This command automatically extracts the latest plan from Claude session files.

## Purpose

This command provides a fast path for creating GitHub issues. It:

- Extracts the latest `ExitPlanMode` plan from Claude session files
- Creates GitHub issue with plan content
- Adds `erk-plan` label automatically
- Displays issue URL

**What it does NOT do:**

- ❌ No disk persistence (issue-only workflow)
- ❌ No plan enhancement or enrichment
- ❌ No interactive clarifying questions
- ❌ No worktree creation (use `/erk:create-wt-from-plan-issue` separately)

## How It Works

1. **Searches Claude session files** for the latest ExitPlanMode plan
2. **Extracts title** from plan (H1 → H2 → first line)
3. **Ensures label exists** (creates `erk-plan` label if needed)
4. **Creates GitHub issue** with plan body and label
5. **Displays result** with issue number and URL

## Prerequisites

- Latest plan must exist in Claude session files
- Must be in a git repository
- `gh` CLI must be installed and authenticated
- GitHub repository must be accessible

## Limitations

⚠️ **This workflow creates issues only (no local plan file)**

- Cannot create worktree from this issue later (requires plan file on disk)
- No local backup of plan content (exists only in GitHub issue)
- Cannot edit plan before issue creation

**If you need worktree workflow:**

1. Use `/erk:save-plan` to save plan to disk
2. Use `/erk:create-wt-from-plan-file` to create worktree
3. Use `/erk:create-plan-issue-from-plan-file` to create issue

---

## Agent Instructions

You are executing the `/erk:create-plan-issue-from-context` command. This command uses the kit CLI to extract plans from Claude session files.

### CRITICAL: Tool Restrictions

**ALLOWED TOOLS:**

- `Bash` - For calling kit CLI command
- `AskUserQuestion` - ONLY for error recovery if needed

**FORBIDDEN TOOLS:**

- `Read` - Do NOT read conversation manually
- `Edit` - Do NOT modify any existing files
- `Write` - Do NOT write any files (issue-only workflow)
- `Glob` - Do NOT search the codebase
- `Grep` - Do NOT search the codebase
- `Task` - Do NOT launch subagents

**CRITICAL:** If you use any forbidden tool, STOP immediately.

### Step 1: Verify Prerequisites

Check that gh CLI is available and authenticated:

```bash
# Check gh CLI availability
if ! command -v gh &> /dev/null; then
    echo "❌ Error: gh CLI not found" >&2
    echo "" >&2
    echo "Install gh CLI:" >&2
    echo "- macOS: brew install gh" >&2
    echo "- See: https://cli.github.com" >&2
    exit 1
fi

# Check authentication
if ! gh auth status &> /dev/null; then
    echo "❌ Error: gh CLI not authenticated" >&2
    echo "" >&2
    echo "Run: gh auth login" >&2
    echo "Follow prompts to authenticate with GitHub." >&2
    exit 1
fi
```

### Step 2: Extract Plan from Session and Create Issue

Use the kit CLI command to extract the latest plan from Claude session files and create a GitHub issue:

```bash
result=$(dot-agent kit-command erk create-issue-from-session)
```

This command:

- Searches Claude session files for the latest ExitPlanMode plan
- Extracts the plan text and title
- Ensures erk-plan label exists (creates if needed)
- Creates GitHub issue with plan as body
- Returns JSON result

**Parse the JSON result:**

```bash
# Check if successful
if ! echo "$result" | jq -e '.success' > /dev/null 2>&1; then
    error_msg=$(echo "$result" | jq -r '.error')
    echo "❌ Error: $error_msg" >&2
    exit 1
fi

# Extract result fields
issue_number=$(echo "$result" | jq -r '.issue_number')
issue_url=$(echo "$result" | jq -r '.issue_url')
title=$(echo "$result" | jq -r '.title')
```

**Common errors:**

- **No plan found**: No ExitPlanMode found in session files
- **gh CLI not available**: gh command not found or not authenticated
- **GitHub API error**: Network or permission issues

### Step 3: Display Success Output

After successfully creating the issue, output:

```
✅ GitHub issue created: #<issue_number>

📋 Title: <title>
🔗 URL: <issue_url>

📝 Note: This issue was created without a local plan file.

Next steps:
1. Review issue content on GitHub
2. To create worktree, first save plan with /erk:save-plan
3. Track progress in GitHub issue
```

### Error Handling

**Use this format for all errors:**

```
❌ Error: [Brief description]

[Context or details]

[Suggested action if applicable]
```

**Common error cases:**

1. **No plan found in session files**

```
❌ Error: No plan found in Claude session files

Details: No ExitPlanMode tool uses found in session history

Suggested action:
1. Create a plan first (enter Plan mode, create plan, exit Plan mode)
2. Ensure you exited Plan mode with ExitPlanMode tool
3. Try again after creating a plan
```

2. **gh CLI not found**

```
❌ Error: gh CLI not found

Install gh CLI:
- macOS: brew install gh
- See: https://cli.github.com

After installation, authenticate:
gh auth login
```

3. **gh CLI not authenticated**

```
❌ Error: gh CLI not authenticated

Run: gh auth login
Follow prompts to authenticate with GitHub.
```

4. **GitHub API error**

```
❌ Error: Failed to create GitHub issue

Details: <specific error message>

Suggested action:
1. Check authentication: gh auth status
2. Verify repository access: gh repo view
3. Check network connectivity
```

## Important Notes

- **Deterministic**: Searches session files, not conversation context
- **No local file**: Plan exists only in GitHub issue
- **Automatic labeling**: Always uses `erk-plan` label
- **Latest plan**: Automatically finds the most recent plan by timestamp
- **Issue-only workflow**: Cannot create worktree from this issue later

## Technical Details

**Session file location:**

- Base: `~/.claude/projects/`
- Project directory: Working directory path with `/` replaced by `-` and prepended with `-`
- Example: `/Users/user/code/myproject` → `~/.claude/projects/-Users-user-code-myproject/`

**Search pattern:**

- Parses JSONL files (one JSON object per line)
- Looks for `type: "tool_use"` with `name: "ExitPlanMode"`
- Extracts `input.plan` field
- Sorts by timestamp to find latest

**Label management:**

- Automatically creates `erk-plan` label if it doesn't exist
- Label color: `0E8A16` (green)
- Label description: "Implementation plan for erk workflow"
