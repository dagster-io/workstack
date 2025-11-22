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
- Adds YAML front matter with `erk_plan` marker
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
2. **Adds YAML front matter** with erk_plan marker and timestamp
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

### Step 3: Add YAML Front Matter

Prepend YAML front matter to the extracted plan content.

**Algorithm:**

1. Get current timestamp in ISO8601 format (e.g., `2025-11-22T09:00:00Z`)
2. Construct front matter:

   ```yaml
   ---
   erk_plan: true
   created_at: <timestamp>
   ---
   ```

3. Prepend to plan content with double newline after closing `---`

**CRITICAL:** YAML delimiters must be on separate lines with newlines before and after.

**Example output structure:**

```markdown
---
erk_plan: true
created_at: 2025-11-22T09:00:00Z
---

# Original Plan Title

[Original plan content unchanged...]
```

**Store this as the full issue body** for use in Step 6.

### Step 4: Extract Title from Plan

Extract title from the plan content to use as GitHub issue title.

**Algorithm (try in priority order):**

1. Check for YAML front matter `title:` field in extracted plan
2. Extract first H1 heading (`# Title`)
3. Extract first H2 heading (`## Title`)
4. Fallback: Use first non-empty line

**Title cleanup:**

- Remove markdown formatting (`#`, `##`, backticks, etc.)
- Trim leading/trailing whitespace
- Limit to 100 characters (GitHub recommendation)

**If title extraction completely fails:**

Use fallback title: `"Implementation Plan"`

### Step 5: Ensure GitHub Label Exists

Check if the `erk-plan` label exists, and create it if needed.

1. Check for label using gh CLI:

   ```bash
   gh label list --json name --jq '.[] | select(.name == "erk-plan") | .name'
   ```

2. If label doesn't exist (empty output), create it:

   ```bash
   gh label create "erk-plan" \
     --description "Implementation plan for manual execution" \
     --color "0E8A16"
   ```

   Note: Color 0E8A16 is GitHub's default green color for planning labels.

3. If label already exists: Continue silently (no output needed)

4. If label creation fails:

   ```
   ⚠️  Warning: Could not create erk-plan label

   Command output: <stderr>

   Continuing with issue creation...
   ```

   Continue to Step 6 (non-blocking warning - gh will accept the label even if not in repo's label list)

### Step 6: Create GitHub Issue

Use gh CLI to create the issue with plan content.

**CRITICAL:** Issue body must include YAML front matter from Step 3.

1. Create temporary file for issue body (use heredoc or pipe):

   ```bash
   gh issue create \
     --title "<extracted-title>" \
     --body "<full-body-with-yaml-frontmatter>" \
     --label "erk-plan"
   ```

   Note: Use shell heredoc or proper escaping for body content

2. Parse issue URL from output (gh returns URL like `https://github.com/owner/repo/issues/123`)

3. Extract issue number from URL

4. If gh command fails:

   ```
   ❌ Error: Failed to create GitHub issue

   Details: <stderr>

   Suggested action:
   1. Check authentication: gh auth status
   2. Verify repository access: gh repo view
   3. Check network connectivity
   ```

   Exit with error.

### Step 7: Display Success Output

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
5. **Label creation failed** - See Step 5 (non-blocking warning)
6. **Issue creation failed** - See Step 6

## Important Notes

- **No disk persistence**: Plan exists only in GitHub issue
- **No enhancement**: Extract plan as-is from conversation
- **Manual label only**: Always uses `erk-plan` label
- **Issue-only workflow**: Cannot create worktree from this issue later
- **Speed over reusability**: Trade-off for streamlined workflow
