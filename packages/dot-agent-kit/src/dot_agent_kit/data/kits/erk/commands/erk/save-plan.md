---
description: Extract plan from Claude session and save to disk (no enhancements)
---

# /erk:save-plan

Extracts the latest implementation plan from Claude session files and saves it to disk with minimal frontmatter. This command uses deterministic session file parsing instead of conversation context searching.

## Usage

```bash
/erk:save-plan
```

## Purpose

This command provides a fast, deterministic path for saving plans. It:

- Extracts the latest `ExitPlanMode` plan from Claude session files
- Generates a descriptive filename from the plan title
- Adds minimal frontmatter (`erk_plan: true`, timestamp)
- Saves to repository root

**What it does NOT do:**

- ❌ No session log discovery or mining
- ❌ No plan enhancement or enrichment
- ❌ No interactive clarifying questions
- ❌ No complex analysis

## How It Works

1. **Searches Claude session files** for the latest ExitPlanMode plan
2. **Generates filename** from plan title using kebab-case
3. **Adds minimal frontmatter** with marker and timestamp
4. **Saves to repository root** as `<name>-plan.md`

---

## Agent Instructions

You are executing the `/erk:save-plan` command. This command uses the kit CLI to extract plans from Claude session files.

### CRITICAL: Tool Restrictions

**ALLOWED TOOLS:**

- `Bash` - For calling kit CLI command
- `AskUserQuestion` - ONLY for error recovery if needed

**FORBIDDEN TOOLS:**

- `Read` - Do NOT read conversation manually
- `Edit` - Do NOT modify any existing files
- `Write` - Do NOT write files manually (kit CLI handles this)
- `Glob` - Do NOT search the codebase
- `Grep` - Do NOT search the codebase
- `Task` - Do NOT launch subagents

**CRITICAL:** If you use any forbidden tool, STOP immediately.

### Step 1: Extract Plan from Session and Save

Use the kit CLI command to extract the latest plan from Claude session files and save it:

```bash
result=$(dot-agent kit-command erk save-plan-from-session)
```

This command:

- Searches Claude session files for the latest ExitPlanMode plan
- Extracts the plan text
- Generates filename from plan title
- Adds minimal frontmatter
- Saves to repository root
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
file_path=$(echo "$result" | jq -r '.file_path')
filename=$(echo "$result" | jq -r '.filename')
title=$(echo "$result" | jq -r '.title')
```

**Common errors:**

- **No plan found**: No ExitPlanMode found in session files
- **File already exists**: Plan file already exists at target path
- **Not in git repository**: Current directory is not in a git repo

### Step 2: Display Success Output

After successfully saving the plan file, output:

```
✅ Plan saved to: <filename>

📋 Title: <title>
📁 Path: <file_path>

Next steps:
1. Review the plan if needed
2. Create worktree: /erk:create-wt-from-plan-file
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

1. **No plan found in session files**

```
❌ Error: No plan found in Claude session files

Details: No ExitPlanMode tool uses found in session history

Suggested action:
1. Create a plan first (enter Plan mode, create plan, exit Plan mode)
2. Ensure you exited Plan mode with ExitPlanMode tool
3. Try again after creating a plan
```

2. **File already exists**

```
❌ Error: Plan file already exists

Details: File exists at <path>

Suggested action:
1. Review existing plan file
2. Delete it if you want to replace: rm <path>
3. Choose a different plan title
```

3. **Not in git repository**

```
❌ Error: Not in a git repository

Details: Current directory is not within a git repository

Suggested action:
1. Navigate to your git repository
2. Run the command from within the repository
```

## Important Notes

- **Deterministic**: Searches session files, not conversation context
- **No enhancements**: Saves plan exactly as found in ExitPlanMode
- **Fast**: No additional processing or analysis
- **Latest plan**: Automatically finds the most recent plan by timestamp
- **Compatible workflow**: Output works with `/erk:create-wt-from-plan-file`

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

**Filename generation:**

- Extracts title from plan (H1 → H2 → first line)
- Converts to kebab-case
- Removes emojis and special characters
- Appends `-plan.md` suffix
