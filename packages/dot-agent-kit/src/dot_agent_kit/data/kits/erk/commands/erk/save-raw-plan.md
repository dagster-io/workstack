---
description: Extract plan from Claude session and create GitHub issue (no enrichment)
---

# /erk:save-raw-plan

Extracts the latest implementation plan from Claude session files and creates a GitHub issue with the raw plan content. This command provides a "fast path" for creating issues with deterministic session file parsing and no enrichment.

## Usage

```bash
/erk:save-raw-plan
```

## Purpose

This command provides a **fast path** for creating GitHub issues from session plans. It:

- Extracts the latest `ExitPlanMode` plan from Claude session files (deterministic)
- Creates a GitHub issue with `erk-plan` label
- Preserves plan content exactly as found (no enrichment)
- Outputs JSON metadata with issue URL and number

**What it does NOT do:**

- ❌ No conversation context searching
- ❌ No plan enhancement or enrichment
- ❌ No interactive clarifying questions
- ❌ No semantic understanding extraction
- ❌ No disk file creation (issue is the artifact)

**Fast Path vs Enriched Path:**

- **save-raw-plan** (this command): Session files → Raw plan → GitHub issue (fast, deterministic)
- **save-plan**: Conversation context → Enriched plan → GitHub issue (interactive, comprehensive)

## How It Works

1. **Extracts plan from session files** - Searches JSONL files for latest ExitPlanMode
2. **Validates repository** - Confirms git repository and GitHub CLI availability
3. **Creates GitHub issue** - Creates issue with `erk-plan` label
4. **Outputs metadata** - Returns JSON with issue URL and number
5. **Displays next steps** - Shows four copy-pastable commands for implementation

---

## Agent Instructions

You are executing the `/erk:save-raw-plan` command. This command extracts plans from session files and creates GitHub issues.

### CRITICAL: Tool Restrictions

**ALLOWED TOOLS:**

- `Bash` - For git commands and kit CLI commands
- `AskUserQuestion` - ONLY for error recovery if needed

**FORBIDDEN TOOLS:**

- `Read` - Do NOT read conversation manually (uses session files instead)
- `Edit` - Do NOT modify any existing files
- `Write` - Do NOT write files manually (kit CLI handles temp files)
- `Glob` - Do NOT search the codebase
- `Grep` - Do NOT search the codebase
- `Task` - Do NOT launch subagents

**CRITICAL:** If you use any forbidden tool, STOP immediately.

### Step 1: Extract Plan from Session Files

Execute the kit CLI command to extract the latest plan from session files:

```bash
dot-agent kit-command erk save-plan-from-session --format json
```

This command:

- Searches Claude session JSONL files for latest ExitPlanMode plan
- Extracts plan content and title
- Returns JSON with `plan_content`, `plan_title`, or `error` fields

**Parse the JSON output:**

Extract these fields:

- `plan_content` - The raw markdown plan text
- `plan_title` - The title for the GitHub issue
- `error` - Present if extraction failed

**If error field is present:**

```bash
error_msg=$(echo "$result" | jq -r '.error')
dot-agent kit-command erk format-error \
    --brief "No plan found in session files" \
    --details "$error_msg" \
    --action "Ensure you used ExitPlanMode in the session" \
    --action "Check session files exist in ~/.claude/projects/" \
    --action "Try running /erk:save-plan with conversation context instead"
```

### Step 2: Validate Repository and GitHub CLI

@../docs/validate-git-repository.md

@../docs/validate-github-cli.md

### Step 3: Create GitHub Issue

Replace `$PLAN_CONTENT` with the `plan_content` variable extracted in Step 1:

@../docs/create-github-issue.md

### Step 4: Output Success Message

After creating the GitHub issue successfully, format the success output using the kit CLI command:

```bash
# Parse issue number from URL
issue_number=$(echo "$issue_url" | grep -oE '[0-9]+$')

# Format success output
dot-agent kit-command erk format-success-output \
    --issue-number "$issue_number" \
    --issue-url "$issue_url"
```

This will output the issue link, next steps commands, and JSON metadata in a consistent format.

## Important Notes

- **Fast Path**: No interactive questions, no enrichment, no semantic analysis
- **Deterministic**: Uses session file parsing, not conversation context
- **Raw Content**: Preserves plan exactly as found in ExitPlanMode
- **Latest Plan**: Automatically finds most recent plan by timestamp
- **Issue-First**: Creates GitHub issue directly (no disk files)
- **Command Comparison**:
  - `save-raw-plan`: Session files → Raw plan → GitHub issue (this command)
  - `save-plan`: Conversation → Enriched plan → GitHub issue (interactive)
- **Next Step**: Use `erk implement <issue>` to execute the plan

## Technical Details

@../docs/session-file-location.md

**Issue title extraction:**

- Extracts title from plan content (H1 → H2 → first line)
- Converts to title case
- Truncates to 100 characters if needed
- Falls back to "Implementation Plan" if no clear title

**GitHub issue creation:**

- Creates issue with `erk-plan` label automatically
- Uses extracted title as issue title
- Plan content becomes issue body
- Returns issue URL for next steps
