---
description: Extract plan from conversation and create GitHub issue directly (no enhancements)
---

# /erk:save-plan

Extracts an implementation plan from the conversation and creates a GitHub issue directly with minimal frontmatter. This is a simplified alternative to `/erk:save-context-enriched-plan` that skips all discovery mining and enhancement steps.

## Usage

```bash
/erk:save-plan
```

## Purpose

This command provides a fast path for creating plan issues when you don't need session log discoveries or enhancements. It:

- Extracts the plan as-is from the conversation
- Adds minimal frontmatter (`erk_plan: true`, timestamp)
- Creates GitHub issue with the plan content and `erk-plan` label

**What it does NOT do:**

- ❌ No session log discovery or mining
- ❌ No plan enhancement or enrichment
- ❌ No interactive clarifying questions
- ❌ No complex analysis

## How It Works

1. **Extracts the plan** from the conversation (as-is)
2. **Adds minimal frontmatter** with marker and timestamp
3. **Creates GitHub issue** with plan content and `erk-plan` label
4. **Returns issue URL** for immediate implementation

---

## Agent Instructions

You are executing the `/erk:save-plan` command. This command uses the kit CLI to extract plans from Claude session files.

### CRITICAL: Tool Restrictions

**ALLOWED TOOLS:**

- `Read` - For examining the conversation
- `Bash` - For git commands and kit CLI commands

**FORBIDDEN TOOLS:**

- `Read` - Do NOT read conversation manually
- `Edit` - Do NOT modify any existing files
- `Write` - Do NOT write to codebase (only creating GitHub issue)
- `Glob` - Do NOT search the codebase
- `Grep` - Do NOT search the codebase
- `Task` - Do NOT launch subagents
- Any tool not explicitly listed as allowed

**CRITICAL:** If you use any forbidden tool, STOP immediately.

### Step 1: Extract Plan from Session and Save

Search backwards from recent messages in the conversation for an implementation plan.

**Where to look:**

1. `ExitPlanMode` tool results containing the plan
2. Sections like "## Implementation Plan" or "### Implementation Steps"
3. Structured markdown with numbered lists of implementation tasks

**What to extract:**

- Complete plan content (minimum 100 characters)
- Must have structure (headers, lists, or numbered steps)
- Extract as-is - NO modifications or enhancements

**Validation:**

- Plan must be ≥100 characters
- Plan must have structure (headers and/or lists)

**If no plan found:**

```
❌ Error: No implementation plan found in conversation

Please create a plan first:
1. Enter Plan mode
2. Create your implementation plan
3. Exit Plan mode
4. Then run /erk:save-plan
```

### Step 2: Add Minimal Frontmatter

Prepend YAML frontmatter to the plan content:

```yaml
---
erk_plan: true
created_at: <ISO-8601-timestamp>
---
```

**DO NOT modify the plan content** - append it exactly as extracted from Step 1.

**Example output structure:**

```markdown
---
erk_plan: true
created_at: 2025-11-21T10:00:00Z
---

# Original Plan Title

[Original plan content unchanged...]
```

### Step 3: Validate Repository and GitHub CLI

Verify we're in a git repository and GitHub CLI is available:

**Steps:**

1. Verify git repository using: `git rev-parse --show-toplevel`
2. Verify GitHub CLI is authenticated

**If not in git repository:**

```
❌ Error: Not in a git repository

This command must be run from within a git repository.
```

**If GitHub CLI not available or not authenticated:**

```
❌ Error: GitHub CLI not available or not authenticated

Suggested action:
  1. Install GitHub CLI: https://cli.github.com/
  2. Authenticate with: gh auth login
  3. Verify authentication: gh auth status
```

### Step 4: Create GitHub Issue

Create a GitHub issue with the plan content using the kit CLI command:

```bash
issue_url=$(echo "$plan_content_with_frontmatter" | dot-agent kit-command erk create-plan-issue-from-context)
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create GitHub issue" >&2
    exit 1
fi
```

The kit CLI command:

- Reads plan content from stdin
- Extracts title from plan for issue title
- Creates issue with `erk-plan` label
- Returns issue URL

**Extract issue number from URL:**

Parse the issue number from the returned URL (e.g., `https://github.com/org/repo/issues/123` → `123`)

**If issue creation fails:**

```
❌ Error: Failed to create GitHub issue

Details: [specific error from kit CLI command]

Suggested action:
  1. Verify GitHub CLI (gh) is installed and authenticated
  2. Check repository has issues enabled
  3. Verify network connectivity
  4. Check gh auth status
```

### Step 5: Output Success Message

After successfully creating the GitHub issue, output:

```
✅ GitHub issue created: #<number>
   <issue-url>

Next steps:
1. Review the issue if needed: gh issue view <number> --web
2. Implement: erk implement #<number>

---

{"issue_number": <number>, "issue_url": "<url>", "status": "created"}
```

### Error Handling

**Use this format for all errors:**

```
❌ Error: [Brief description]

[Context or details]

[Suggested action if applicable]
```

**Common error cases:**

1. **No plan found** - See Step 1
2. **GitHub auth failed** - See Step 3
3. **Issue creation failed** - See Step 4
4. **Not in git repo** - See Step 3

## Important Notes

- **No enhancements**: Create issue with the plan exactly as found in the conversation
- **No discovery mining**: No session log access or analysis
- **Simple and fast**: Designed for quick issue creation without preprocessing
- **Compatible workflow**: Output works with `erk implement #<issue>` just like `/erk:save-context-enriched-plan`
- **GitHub is source of truth**: Issue becomes immediate source of truth (no disk files involved)
