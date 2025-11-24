---
description: Extract plan from conversation, fully enhance it, and create GitHub issue
---

# /erk:create-enriched-plan-issue-from-context

Extract implementation plan from conversation, enhance it for autonomous execution, and create GitHub issue directly without saving to disk.

## Goal

This command combines:

- Plan extraction from conversation (like create-plan-issue-from-context)
- Full enrichment process (like save-context-enriched-plan)
- Direct GitHub issue creation (like create-plan-issue-from-context)

**What This Command Does:**

✅ Find plan in conversation
✅ Apply optional guidance to plan
✅ Interactively enhance plan for autonomous execution
✅ Extract semantic understanding and context
✅ Structure complex plans into phases (when beneficial)
✅ Create GitHub issue with enriched content

**What This Command Does NOT Do:**

❌ No disk persistence (issue-only workflow)
❌ Cannot be used with /erk:create-planned-wt later (requires plan file on disk)

## Usage

```bash
/erk:create-enriched-plan-issue-from-context [guidance]
```

**Examples:**

- `/erk:create-enriched-plan-issue-from-context` - Create enriched issue
- `/erk:create-enriched-plan-issue-from-context "Add retry logic"` - Apply guidance first

## Prerequisites

- Plan must exist in conversation (≥100 chars with headers or lists)
- Must be in a git repository
- `gh` CLI must be installed and authenticated
- GitHub repository must be accessible

## How It Works

1. **Verify Prerequisites** - Check git repo and gh CLI
2. **Extract Plan** - Find implementation plan in conversation
   3-5. **[ENRICHMENT PROCESS]** - Apply guidance, extract understanding, enhance interactively
3. **Wrap in Metadata Block** - Use collapsible `<details>` with `erk-plan` key
4. **Extract Title** - Derive from plan content
5. **Ensure Label Exists** - Create erk-plan label if needed
6. **Create GitHub Issue** - Submit with enriched content
7. **Display Success** - Show issue URL and next steps

## Limitations

⚠️ **This workflow creates issues only (no local plan file)**

- Cannot create worktree from this issue later (requires plan file on disk)
- No local backup of plan content (exists only in GitHub issue)
- Cannot edit plan file before issue creation

**If you need worktree workflow:**

1. Use `/erk:save-context-enriched-plan` to save plan to disk
2. Use `/erk:create-planned-wt` to create worktree
3. Use `/erk:create-planned-issue` to create issue

---

## Agent Instructions

You are executing the `/erk:create-enriched-plan-issue-from-context` command.

### CRITICAL: Tool Restrictions

**ALLOWED TOOLS:**

- `Read` - For examining the conversation
- `Bash` - ONLY for `gh` commands and `git rev-parse`
- `AskUserQuestion` - For enrichment clarifications

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
- Extract as-is for now - enrichment happens in next steps

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

### Steps 3-5: Enrichment Process

@../docs/enrichment-process.md

Apply the complete enrichment process to enhance the extracted plan for autonomous execution.

**Note:** The enrichment process includes:

- Applying optional guidance (if provided as command argument)
- Extracting semantic understanding from planning discussion
- Interactive enhancement with clarifying questions

Store the enriched plan content for use in subsequent steps.

### Step 6: Create GitHub Issue (Single Command)

Use the composite kit CLI command that handles the complete workflow for enriched plans:

- Extracts title from enriched plan
- Ensures erk-plan label exists
- Creates GitHub issue with enriched plan body
- Returns structured JSON result

**Algorithm:**

1. Save enriched plan to temporary file (for clean stdin handling):

   ```bash
   temp_plan=$(mktemp)
   echo "$enriched_plan" > "$temp_plan"
   ```

2. Call the composite kit command:

   ```bash
   result=$(dot-agent kit-command erk create-enriched-plan-from-context)
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
- Creates issue with full enriched plan as body
- Returns JSON: `{"success": true, "issue_number": 123, "issue_url": "..."}`

### Step 7: Display Success Output

After successfully creating the issue, output:

**IMPORTANT:** Output each field on its own line. Preserve newlines between fields - do not concatenate into a single line.

```
✅ GitHub issue created: #<number>

🔗 <issue_url>

📋 This issue includes the enriched plan with:
   - Context & Understanding sections
   - Interactive enhancements
   - Implementation steps with linked context

Next steps:
1. Review issue content on GitHub
2. Implement manually or assign to team member
3. Track progress in GitHub issue

---

{"issue_number": <number>, "issue_url": "<url>", "status": "created", "enriched": true}
```

**Format notes:**

- Use emoji for visual clarity
- Highlight that enrichment was applied
- JSON output for potential scripting integration
- Clear next steps

## Error Handling

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
5. **Label creation failed** - See Step 8 (non-blocking warning)
6. **Issue creation failed** - See Step 9
