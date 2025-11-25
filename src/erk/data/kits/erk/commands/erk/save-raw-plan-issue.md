---
description: Extract plan from conversation and save to disk (no enhancements)
---

# /erk:plan-save

Extracts an implementation plan from the conversation and saves it to disk with minimal frontmatter. This is a simplified alternative to `/erk:save-session-enriched-plan` that skips all discovery mining and enhancement steps.

## Usage

```bash
/erk:plan-save
```

## Purpose

This command provides a fast path for saving plans when you don't need session log discoveries or enhancements. It:

- Extracts the plan as-is from the conversation
- Generates a descriptive filename from the plan title
- Saves plan content as-is (no frontmatter generation)
- Saves to repository root

**What it does NOT do:**

- ❌ No session log discovery or mining
- ❌ No plan enhancement or enrichment
- ❌ No interactive clarifying questions
- ❌ No Kit CLI invocations
- ❌ No complex analysis

## How It Works

1. **Extracts the plan** from the conversation (as-is)
2. **Generates filename** from plan title using kebab-case
3. **Adds minimal frontmatter** with marker and timestamp
4. **Saves to repository root** as `<name>-plan.md`

---

## Agent Instructions

You are executing the `/erk:plan-save` command. Follow these steps carefully using ONLY the allowed tools.

### CRITICAL: Tool Restrictions

**ALLOWED TOOLS:**

- `Read` - For examining the conversation
- `Bash` - ONLY for `git rev-parse --show-toplevel`
- `Write` - ONLY for writing the plan file to repository root
- `AskUserQuestion` - ONLY if filename extraction fails

**FORBIDDEN TOOLS:**

- `Edit` - Do NOT modify any existing files
- `Glob` - Do NOT search the codebase
- `Grep` - Do NOT search the codebase
- `Task` - Do NOT launch subagents
- Any Kit CLI commands
- Any tool not explicitly listed as allowed

**CRITICAL:** If you use any forbidden tool, STOP immediately.

### Step 1: Extract Plan from Conversation

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
4. Then run /erk:plan-save
```

### Step 2: Generate Filename

Generate a descriptive filename from the plan content:

**Title Extraction (LLM semantic analysis):**

1. Extract title from first H1 (`# Title`) or H2 (`## Title`) in the plan
2. If no headers found, use the first line of content

**Filename Transformation (Kit CLI):**

Use the kit CLI command to transform the extracted title to a filename:

```bash
filename=$(dot-agent kit-command erk issue-title-to-filename "$extracted_title")
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to generate filename" >&2
    exit 1
fi
```

The kit CLI command handles:

- Lowercase conversion
- Unicode normalization (NFD)
- Emoji and special character removal
- Hyphen collapse and trimming
- Returns "plan.md" if title is empty after cleanup

**Example transformations:**

- "Create Erk Save Command" → `create-erk-save-command-plan.md`
- "API Migration (Phase 1)" → `api-migration-phase-1-plan.md`
- "Refactor Auth System" → `refactor-auth-system-plan.md`
- "🚀 Feature Launch" → `feature-launch-plan.md`

**If title extraction fails:**

```
Unable to extract title from plan.

Please provide a short name for this plan (use kebab-case):
```

Use `AskUserQuestion` to prompt for title if extraction fails.

### Step 3: Add Minimal Frontmatter

**DO NOT modify the plan content** - use it exactly as extracted from Step 1.

**Example output structure:**

```markdown
# Original Plan Title

[Original plan content unchanged...]
```

### Step 4: Write to Repository Root

Save the plan file to the repository root:

**Steps:**

1. Get repository root using: `git rev-parse --show-toplevel`
2. Construct path: `<repo-root>/<filename>` (filename already includes `-plan.md` suffix from kit CLI)
3. Check if file already exists

**If file exists:**

```
❌ Error: Plan file already exists

File exists at: <path>

Options:
1. Choose a different name
2. Delete the existing file first
3. Cancel the operation
```

**If not in git repository:**

```
❌ Error: Not in a git repository

This command must be run from within a git repository.
```

**On success:**

Write the file with frontmatter + plan content using the Write tool.

### Step 5: Output Success Message

After successfully writing the plan file, output:

```
✅ Plan saved to: <filename>-plan.md

Next steps:
1. Review the plan if needed
2. Create worktree: /erk:create-wt-from-plan-file <filename>-plan.md
3. Switch to worktree and implement
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
2. **Filename extraction failed** - Prompt user for name (Step 2)
3. **File already exists** - See Step 4
4. **Not in git repo** - See Step 4

## Important Notes

- **No enhancements**: Save the plan exactly as found in the conversation
- **No discovery mining**: No session log access or analysis
- **No Kit CLI**: This command uses only basic tools
- **Simple and fast**: Designed for quick plan saving without preprocessing
- **Compatible workflow**: Output works with `/erk:create-wt-from-plan-file` just like `/erk:save-context-enriched-plan`
