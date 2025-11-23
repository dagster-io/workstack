---
description: Extract plan from Claude session and save to disk (no enhancements)
---

# /erk:save-plan

Extracts the latest implementation plan from Claude session files and saves it to disk. This command uses deterministic session file parsing instead of conversation context searching.

## Usage

```bash
/erk:save-plan
```

## Purpose

This command provides a fast, deterministic path for saving plans. It:

- Extracts the latest `ExitPlanMode` plan from Claude session files
- Generates a descriptive filename from the plan title
- Saves plan content as-is (no frontmatter generation)
- Saves to repository root

**What it does NOT do:**

- ❌ No session log discovery or mining
- ❌ No plan enhancement or enrichment
- ❌ No interactive clarifying questions
- ❌ No complex analysis

## How It Works

1. **Searches Claude session files** for the latest ExitPlanMode plan
2. **Generates filename** from plan title using kebab-case
3. **Saves plan content as-is** (no frontmatter added)
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

Use the kit CLI command with display format to extract the latest plan from Claude session files and save it:

```bash
dot-agent kit-command erk save-plan-from-session --format display
```

This command:

- Searches Claude session files for the latest ExitPlanMode plan
- Extracts the plan text
- Generates filename from plan title
- Saves plan content as-is (no frontmatter)
- Saves to repository root
- Displays formatted output (or errors) directly

**That's it!** The Python command handles all error checking, formatting, and output. No JSON parsing needed.

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
