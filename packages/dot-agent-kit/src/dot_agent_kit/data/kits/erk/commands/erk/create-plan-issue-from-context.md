---
description: Create GitHub issue directly from plan in conversation (no disk file)
---

# /erk:create-plan-issue-from-context

Extract implementation plan from the current conversation and create a GitHub issue directly, without saving a plan file to disk. This provides a streamlined workflow for quick issue creation from conversational context.

## Usage

```bash
/erk:create-plan-issue-from-context
```

**No arguments accepted** - This command automatically extracts the plan from the conversation.

## Purpose

This command provides a fast path for creating GitHub issues when you don't need a local plan file. It:

- Extracts the plan as-is from the conversation
- Wraps plan in collapsible metadata block
- Creates GitHub issue with `erk-plan` label
- Displays issue URL

**What it does NOT do:**

- ❌ No disk persistence (issue-only workflow)
- ❌ No plan enhancement or enrichment
- ❌ No interactive clarifying questions
- ❌ No worktree creation (use `/erk:create-planned-wt` separately)
- ❌ Cannot be used with `/erk:create-planned-wt` later (requires plan file)

## How It Works

1. **Extracts plan** from conversation (minimum 100 chars, must have structure)
2. **Wraps in metadata block** using collapsible `<details>` with `erk-plan` key
3. **Extracts title** from plan (H1 → H2 → first line)
4. **Ensures label exists** (creates `erk-plan` label if needed)
5. **Creates GitHub issue** with plan body and label
6. **Displays result** with issue number and URL

## Prerequisites

- Plan must exist in conversation (≥100 chars with headers or lists)
- Must be in a git repository
- `gh` CLI must be installed and authenticated
- GitHub repository must be accessible

## Limitations

⚠️ **This workflow creates issues only (no local plan file)**

- Cannot create worktree from this issue later (requires plan file on disk)
- No local backup of plan content (exists only in GitHub issue)
- Cannot edit plan file before issue creation

**If you need worktree workflow:**

1. Use `/erk:save-plan` or `/erk:save-context-enriched-plan` to save plan to disk
2. Use `/erk:create-wt-from-plan-file` to create worktree
3. Use `/erk:create-plan-issue-from-plan-file` to create issue

---

## Agent Instructions

You are executing the `/erk:create-plan-issue-from-context` command. Follow these steps carefully using ONLY the allowed tools.

### CRITICAL: Tool Restrictions

**ALLOWED TOOLS:**

- `Read` - For examining the conversation
- `Bash` - ONLY for `gh` commands and `git rev-parse`
- `AskUserQuestion` - ONLY for error recovery

**FORBIDDEN TOOLS:**

- `Edit` - Do NOT modify any existing files
- `Write` - Do NOT write any files (issue-only workflow)
- `Glob` - Do NOT search the codebase
- `Grep` - Do NOT search the codebase
- `Task` - Do NOT launch subagents
- Any tool not explicitly listed as allowed

**CRITICAL:** If you use any forbidden tool, STOP immediately.

### Step 1: Verify Prerequisites

Check that required tools are available:

1. Verify we're in a git repository:

   ```bash
   git rev-parse --git-dir
   ```

   If fails:

   ```
   ❌ Error: Not in a git repository

   This command must be run from within a git repository.
   ```

   Exit with error.

2. Check if gh CLI is available:

   ```bash
   gh --version
   ```

   If fails:

   ```
   ❌ Error: gh CLI not found

   Install gh CLI:
   - macOS: brew install gh
   - See: https://cli.github.com

   After installation, authenticate:
   gh auth login
   ```

   Exit with error.

3. Check gh authentication:

   ```bash
   gh auth status
   ```

   If fails:

   ```
   ❌ Error: gh CLI not authenticated

   Run: gh auth login
   Follow prompts to authenticate with GitHub.
   ```

   Exit with error.

### Step 2: Extract Plan from Conversation

Search backwards from recent messages in the conversation for an implementation plan.

**Where to look:**

1. `ExitPlanMode` tool results containing the plan
2. Sections like "## Implementation Plan" or "### Implementation Steps"
3. Structured markdown with numbered lists of implementation tasks
4. Any substantial markdown content with headers and lists

**What to extract:**

- Complete plan content (minimum 100 characters)
- Must have structure (headers, lists, or numbered steps)
- Extract as-is - NO modifications or enhancements

**Validation criteria:**

- Plan must be ≥100 characters
- Plan must have structure:
  - Contains headers (# or ##) OR
  - Contains numbered lists (1. 2. 3.) OR
  - Contains bulleted lists (- or \*)

**If no valid plan found:**

```
❌ Error: No implementation plan found in conversation

Details: Could not find valid plan with structure (headers or lists) and ≥100 characters

Suggested action:
1. Ensure plan is in conversation
2. Plan should have headers or numbered/bulleted lists
3. Re-paste plan in conversation if needed
```

Exit with error.

### Step 3: Create GitHub Issue (Single Command)

Use the new composite kit CLI command that handles the complete workflow:

- Extracts title from plan
- Ensures erk-plan label exists
- Creates GitHub issue with plan body
- Returns structured JSON result

**Algorithm:**

1. Save plan to temporary file (for clean stdin handling):

   ```bash
   temp_plan=$(mktemp)
   echo "$plan_content" > "$temp_plan"
   ```

2. Call the composite kit command:

   ```bash
   result=$(cat "$temp_plan" | dot-agent kit-command erk create-plan-issue-from-context)
   rm "$temp_plan"

   # Parse JSON output
   if ! echo "$result" | jq -e '.success' > /dev/null; then
       echo "❌ Error: Failed to create GitHub issue" >&2
       exit 1
   fi

   issue_number=$(echo "$result" | jq -r '.issue_number')
   issue_url=$(echo "$result" | jq -r '.issue_url')
   ```

3. If command fails:

   ```
   ❌ Error: Failed to create GitHub issue

   Suggested action:
   1. Check authentication: gh auth status
   2. Verify repository access: gh repo view
   3. Check network connectivity
   ```

   Exit with error.

**What this command does internally:**

- Extracts title (H1 → H2 → first line fallback)
- Ensures erk-plan label exists (creates if needed)
- Creates issue with full plan as body
- Returns JSON: `{"success": true, "issue_number": 123, "issue_url": "..."}`

### Step 4: Display Success Output

After successfully creating the issue, output:

```
✅ GitHub issue created: #<number>

🔗 <issue_url>

📝 Note: This issue was created without a local plan file. To create a worktree, first save the plan with `/erk:save-plan` or `/erk:save-context-enriched-plan`.

Next steps:
1. Review issue content on GitHub
2. Implement manually or assign to team member
3. Track progress in GitHub issue

---

{"issue_number": <number>, "issue_url": "<url>", "status": "created"}
```

**Format notes:**

- Use emoji for visual clarity
- Include limitation note (brief, as requested)
- JSON output for potential scripting integration
- Clear next steps

### Error Handling

**Use this format for all errors:**

```
❌ Error: [Brief description]

[Context or details]

[Suggested action if applicable]
```

**Common error cases:**

1. **Not in git repository** - See Step 1
2. **gh CLI not found** - See Step 1
3. **gh not authenticated** - See Step 1
4. **No plan found** - See Step 2
5. **Issue creation failed** - See Step 3 (kit command handles label creation internally)

## Important Notes

- **No disk persistence**: Plan exists only in GitHub issue
- **No enhancement**: Extract plan as-is from conversation
- **Manual label only**: Always uses `erk-plan` label
- **Issue-only workflow**: Cannot create worktree from this issue later
- **Speed over reusability**: Trade-off for streamlined workflow
