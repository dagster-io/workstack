---
description: Extract plan from context, create GitHub issue, and setup implementation worktree
---

# /erk:implement-plan-in-context

Extract implementation plan from the current conversation, create a GitHub issue with the `erk-plan` label, and provide the shell activation command to automatically create a worktree and begin implementation.

## Usage

```bash
/erk:implement-plan-in-context
```

**No arguments accepted** - This command automatically extracts the plan from the conversation.

## Purpose

This command provides an end-to-end workflow from plan to implementation in one step. It:

- Extracts the plan as-is from the conversation
- Creates GitHub issue with `erk-plan` label
- Provides shell activation one-liner for automatic worktree creation and implementation

**What it does:**

- ✅ Extract plan from conversation context
- ✅ Create GitHub issue with `erk-plan` label
- ✅ Output shell activation command for implementation

**What it does NOT do:**

- ❌ No plan enhancement or enrichment (use `/erk:save-context-enriched-plan` for that)
- ❌ No disk persistence (issue-only workflow)
- ❌ No automatic worktree creation (requires running the provided command)

## How It Works

1. **Extracts plan** from conversation (minimum 100 chars, must have structure)
2. **Creates GitHub issue** with plan body and `erk-plan` label
3. **Outputs command**: `erk implement <issue-number>`

Running `erk implement <issue-number>` will:

- Create new worktree with auto-generated branch name
- Set up `.impl/` folder with plan content
- Save `.impl/issue.json` for PR linking
- Provide activation instructions

## Prerequisites

- Plan must exist in conversation (≥100 chars with headers or lists)
- Must be in a git repository
- `gh` CLI must be installed and authenticated
- GitHub repository must be accessible

## When to Use This Command

**Use this command when:**

- You have a plan in conversation and want immediate implementation
- You want automatic worktree creation and activation
- You're ready to start implementing right away

**Use `/erk:save-context-enriched-plan` instead when:**

- You want to enhance the plan with clarifying questions
- You need to review/edit the plan before creating worktree
- You prefer file-based workflow

---

## Agent Instructions

You are executing the `/erk:implement-plan-in-context` command. Follow these steps carefully using ONLY the allowed tools.

### CRITICAL: Tool Restrictions

**ALLOWED TOOLS:**

- `Read` - For examining the conversation
- `Bash` - ONLY for `dot-agent kit-command` and git validation
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

### Step 3: Create GitHub Issue

Use the composite kit CLI command that handles the complete workflow:

1. Save plan to temporary file (for clean stdin handling):

   ```bash
   temp_plan=$(mktemp)
   cat > "$temp_plan" << 'EOF'
   [plan content here]
   EOF
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

### Step 4: Display Success Output with Implementation Command

After successfully creating the issue, output:

```
✅ GitHub issue created: #<number>

🔗 <issue_url>

To create worktree and begin implementation:

  erk implement <number>

---

{"issue_number": <number>, "issue_url": "<url>", "status": "created"}
```

**Format notes:**

- Use emoji for visual clarity
- Show simple `erk implement` command
- Include JSON output for potential scripting integration

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
5. **Issue creation failed** - See Step 3

## Important Notes

- **Streamlined workflow**: Plan → Issue → Implementation command in one step
- **No disk persistence**: Plan exists only in GitHub issue
- **No enhancement**: Extract plan as-is from conversation
- **Simple output**: Just displays `erk implement <issue-number>` command to run
