---
description: Save an enhanced plan to disk and create a workstack worktree for implementation
---

# /workstack:create-plan-stack

⚠️ **CRITICAL: This command requires execution mode - it writes files and creates worktrees!**

## Goal

**Save an enhanced implementation plan to disk and create a workstack worktree for implementation.**

This command extracts a plan from conversation context (preferably already enhanced), saves it to disk, and creates a worktree for implementation.

**What this command does:**

- ✅ Check that we're NOT in plan mode
- ✅ Find plan in conversation (enhanced or raw)
- ✅ Generate filename from plan title
- ✅ Save plan to disk
- ✅ Create worktree with `workstack create --plan`
- ✅ Display next steps for implementation

**What this command does NOT do:**

- ❌ Enhance or modify the plan (use `/workstack:enhance-plan` for that)
- ❌ Implement any code
- ❌ Switch to the new worktree

## What Happens

When you run this command, these steps occur:

1. **Check Plan Mode** - If in plan mode, inform user to exit and rerun
2. **Verify Scope** - Confirm we're in a git repository with workstack
3. **Detect Plan** - Search for plan in conversation (enhanced preferred)
4. **Generate Filename** - Derive filename from plan title
5. **Detect Root** - Find worktree root directory
6. **Save Plan** - Write plan to disk as markdown file
7. **Create Worktree** - Run `workstack create --plan` command
8. **Display Next Steps** - Show commands to switch and implement

## Usage

```bash
/workstack:create-plan-stack
```

**Workflow:**

1. First enhance plan (optional): `/workstack:enhance-plan`
2. Exit plan mode if active
3. Run this command: `/workstack:create-plan-stack`
4. Switch and implement: `workstack switch <name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`

## Prerequisites

- An implementation plan must exist in conversation (enhanced or raw)
- Must NOT be in plan mode (this command writes files)
- Current working directory must be in a workstack repository
- The plan should not already be saved to disk at repository root

## Plan Detection Priority

This command searches for plans in the following order:

1. **Enhanced plans** - Plans with "Context & Understanding" sections (output from `/workstack:enhance-plan`)
2. **Raw plans** - Original implementation plans without enhancement

If only a raw plan is found, the command will suggest running `/workstack:enhance-plan` first but will continue with the raw plan if the user chooses.

## Success Criteria

This command succeeds when ALL of the following are true:

**Pre-conditions:**
✅ Not in plan mode (execution mode confirmed)
✅ Implementation plan found in conversation

**File & Worktree Creation:**
✅ Plan saved to `<worktree-root>/<filename>-plan.md`
✅ Worktree created with `workstack create --plan`
✅ Worktree contains `.PLAN.md` file (moved by workstack)
✅ Worktree listed in `workstack list`

**Next Steps:**
✅ Next command displayed: `workstack switch <name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`

## Troubleshooting

### "Cannot run in plan mode"

**Cause:** Command was run while in plan mode
**Solution:**

- Exit plan mode first
- Then rerun: `/workstack:create-plan-stack`

### "No plan found in context"

**Cause:** Plan not in conversation or doesn't match detection patterns
**Solution:**

- Ensure plan is in conversation history
- Run `/workstack:enhance-plan` first to create an enhanced plan
- Or paste a plan into the conversation

### "Plan file already exists"

**Cause:** File with same name exists at repository root
**Solution:**

- Change plan title to generate different filename
- Delete existing file: `rm <worktree-root>/<filename>-plan.md`

### "Worktree already exists"

**Cause:** Worktree with derived name already exists
**Solution:**

- List worktrees: `workstack list`
- Remove existing: `workstack remove <name>`
- Or switch to existing: `workstack switch <name>`

### "Failed to parse workstack output"

**Cause:** Workstack version doesn't support --json flag
**Solution:**

- Check version: `workstack --version`
- Update if needed: `uv pip install --upgrade workstack`

---

## Agent Instructions

You are executing the `/workstack:create-plan-stack` command. Follow these steps carefully:

### Step 1: Check Plan Mode and Abort if Active

**CRITICAL: This command CANNOT run in plan mode because it writes files.**

**How to detect plan mode:**

Check for this **exact system reminder tag** in the **MOST RECENT system reminders** (those appearing immediately before/with the user's current request):

```
<system-reminder>
Plan mode is active. The user indicated that they do not want you to execute yet...
</system-reminder>
```

**Detection logic:**

- If this system reminder tag appears in the CURRENT message context → Plan mode is ACTIVE
- If this system reminder tag is absent from recent context → Plan mode is NOT active
- Only check reminders that appear with or immediately before the current command invocation
- Do NOT use conversation content or other heuristics to determine plan mode status

**If in plan mode:**

1. Do NOT proceed with any other steps
2. Display this message to the user:

```
⚠️ This command cannot run in plan mode.

This command needs to write files to disk and create a worktree, which requires execution mode.

Please exit plan mode first, then rerun this command:

/workstack:create-plan-stack
```

3. STOP execution immediately - do NOT continue to Step 2

**If NOT in plan mode:**

- Continue to Step 2

### Step 2: Verify Scope and Constraints

**YOUR ONLY TASKS:**

1. Extract plan from conversation (enhanced or raw)
2. Save plan to disk as markdown file
3. Run `workstack create --plan <file>`
4. Display next steps to user

**FORBIDDEN ACTIONS:**

- Writing ANY code files (.py, .ts, .js, etc.)
- Making ANY edits to existing codebase
- Enhancing or modifying the plan content
- Implementing ANY part of the plan

This command sets up the workspace. Implementation happens in the worktree via `/workstack:implement-plan`.

### Step 3: Detect Implementation Plan in Context

Search conversation history for an implementation plan, preferring enhanced plans:

**Search priority:**

1. **First pass**: Look for enhanced plans
   - Contains "### Context & Understanding" section
   - Has subsections like "#### API/Tool Quirks", "#### Architectural Insights", etc.
   - Typically output from `/workstack:enhance-plan`

2. **Second pass**: If no enhanced plan, look for raw plans
   - Basic implementation plans without Context & Understanding
   - Headers like "## Implementation Plan", numbered steps, etc.

**Search strategy:**

1. Work backwards from most recent messages
2. Check for enhanced plan markers first
3. If not found, check for raw plan patterns
4. Stop at first complete plan found

**What constitutes a complete plan:**

- Minimum 100 characters
- Contains headers (# or ##) OR numbered lists OR bulleted lists
- Has title/overview AND implementation steps

**If enhanced plan found:**

- Use the enhanced plan as-is
- Note to user: "Found enhanced plan ready for saving"

**If only raw plan found:**

- Show info message:

```
ℹ️ Found a raw implementation plan (not enhanced).

For better results, consider running `/workstack:enhance-plan` first to:
- Add clarifying questions
- Preserve semantic understanding
- Structure into phases if needed

Continue with raw plan? [Yes] [Run enhance-plan first]
```

- If user wants to enhance first, abort with:

```
Run `/workstack:enhance-plan` to enhance the plan, then run this command again.
```

- Otherwise, continue with the raw plan

**If no plan found:**

```
❌ Error: No implementation plan found in conversation

Details: Could not find a valid implementation plan in conversation history

Suggested action:
  1. Run `/workstack:enhance-plan` to create an enhanced plan
  2. Or paste an implementation plan into the conversation
  3. Then rerun this command
```

### Step 4: Generate Filename from Plan

**Filename Extraction Algorithm:**

1. **Try H1 header** - Look for `# Title` at start of document
2. **Try H2 header** - Look for `## Title` if no H1
3. **Try prefix patterns** - Look for text after "Plan:", "Implementation Plan:"
4. **Fallback to first line** - Use first non-empty line as last resort

**Validation and Cleanup:**

1. Extract raw title using above priority
2. Convert to lowercase
3. Replace spaces with hyphens
4. Remove all special characters except hyphens and alphanumeric
5. Handle Unicode: Normalize to NFC, remove emojis/special symbols
6. Strip any trailing hyphens or slashes: `base_name = base_name.rstrip('-/')`
7. Ensure at least one alphanumeric character remains

**No length restriction:** DO NOT truncate the base name. The base name is limited to 30 characters by `sanitize_worktree_name()`, but the final name (with date suffix) can exceed 30 characters.

**Resulting names:**

- Filename: `<kebab-case-base>-plan.md` (any length - no LLM truncation)
- Worktree name: `<kebab-case-base>-YY-MM-DD` (base ≤30 chars, final can be ~39 chars)
- Branch name: `<kebab-case-base>-YY-MM-DD` (matches worktree exactly)

**If extraction fails:**

If cleanup results in empty string or no alphanumeric chars, prompt the user:

```
❌ Error: Could not extract valid plan name from title

Details: Plan title contains only special characters or is empty

Suggested action:
  1. Add a clear title to your plan (e.g., # Feature Name)
  2. Or provide a name: What would you like to name this plan?
```

Use AskUserQuestion tool to get the plan name from the user if extraction fails.

**Example transformations:**

- "User Authentication System" → `user-authentication-system`
- "Fix: Database Connection Issues" → `fix-database-connection-issues`
- "🚀 Awesome Feature!!!" → `awesome-feature`
- "###" (only special chars) → Prompt user for name

### Step 5: Detect Worktree Root

Execute: `git rev-parse --show-toplevel`

This returns the absolute path to the root of the current worktree. Store this as `<worktree-root>` for use in subsequent steps.

**If the command fails:**

```
❌ Error: Could not detect worktree root

Details: Not in a git repository or git command failed

Suggested action:
  1. Ensure you are in a valid git repository
  2. Run: git status (to verify git is working)
  3. Check if .git directory exists
```

### Step 6: Save Plan to Disk

**Pre-save validation:**

1. **Verify filename base length** (CRITICAL):
   - Extract base name from `<derived-filename>` (remove `-plan.md` suffix)
   - MUST be ≤ 30 characters
   - If > 30 characters, this is an implementation bug

```
❌ Error: Internal error - filename base exceeds 30 characters

Details: Generated base name '<base>' is <length> characters (max: 30)

This is a bug in the filename generation algorithm. The base should have been
truncated to 30 characters in Step 4.

Suggested action:
  1. Report this as a bug in /workstack:create-plan-stack
  2. Manually truncate the plan title and rerun the command
```

2. **Check if file already exists** at `<worktree-root>/<derived-filename>`:

```
❌ Error: Plan file already exists

Details: File exists at: <worktree-root>/<derived-filename>

Suggested action:
  1. Change plan title to generate different filename
  2. Or delete existing: rm <worktree-root>/<derived-filename>
  3. Or choose different plan name
```

**Save the plan:**

Use the Write tool to save:

- Path: `<worktree-root>/<derived-filename>`
- Content: Full plan markdown content (enhanced or raw)
- Verify file creation

**If save fails:**

```
❌ Error: Failed to save plan file

Details: [specific write error from tool]

Suggested action:
  1. Check file permissions in repository root
  2. Verify available disk space
  3. Ensure path is valid: <worktree-root>/<derived-filename>
```

### Step 7: Create Worktree with Plan

Execute: `workstack create --plan <worktree-root>/<filename> --json --stay`

**Parse JSON output:**

Expected JSON structure:

```json
{
  "worktree_name": "feature-name",
  "worktree_path": "/path/to/worktree",
  "branch_name": "feature-branch",
  "plan_file": "/path/to/.PLAN.md",
  "status": "created"
}
```

**Validate all required fields exist:**

- `worktree_name` (string, non-empty)
- `worktree_path` (string, valid path)
- `branch_name` (string, non-empty)
- `plan_file` (string, path to .PLAN.md)
- `status` (string: "created" or "exists")

**Handle errors:**

**Missing fields in JSON:**

```
❌ Error: Invalid workstack output - missing required fields

Details: Missing: [list of missing fields]

Suggested action:
  1. Check workstack version: workstack --version
  2. Update if needed: uv pip install --upgrade workstack
  3. Report issue if version is current
```

**JSON parsing fails:**

```
❌ Error: Failed to parse workstack create output

Details: [parse error message]

Suggested action:
  1. Check workstack version: workstack --version
  2. Ensure --json flag is supported (v0.2.0+)
  3. Try running manually: workstack create --plan <file> --json
```

**Worktree already exists (status = "exists"):**

```
❌ Error: Worktree already exists: <worktree_name>

Details: A worktree with this name already exists from a previous plan

Suggested action:
  1. View existing: workstack status <worktree_name>
  2. Switch to it: workstack switch <worktree_name>
  3. Or remove it: workstack remove <worktree_name>
  4. Or modify plan title to generate different name
```

**Command execution fails:**

```
❌ Error: Failed to create worktree

Details: [workstack error message from stderr]

Suggested action:
  1. Check git repository health: git fsck
  2. Verify workstack is installed: workstack --version
  3. Check plan file exists: ls -la <plan-file>
```

**CRITICAL: Claude Code Directory Behavior**

🔴 **Claude Code CANNOT switch directories.** After `workstack create` runs, you will remain in your original directory. This is **NORMAL and EXPECTED**. The JSON output gives you all the information you need about the new worktree.

**Do NOT:**

- ❌ Try to verify with `git branch --show-current` (shows the OLD branch)
- ❌ Try to `cd` to the new worktree (will just reset back)
- ❌ Run any commands assuming you're in the new worktree

**Use the JSON output directly** for all worktree information.

### Step 8: Display Next Steps

After successful worktree creation, provide clear instructions:

**IMPORTANT:** You have NOT implemented any code. Implementation happens after the user switches to the worktree.

```markdown
✅ Worktree created: **<worktree-name>**

Plan saved to: `<worktree-root>/<derived-filename>`
Branch: `<branch-name>`
Location: `<worktree-path>`

**Next step:**

`workstack switch <worktree_name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`

This will:

1. Switch to the new worktree
2. Start implementation with automatic edit acceptance
```

**Note:** The final output the user sees should be the single copy-pasteable command above. No additional text after that command.

## Important Notes

- 🔴 **REQUIRES execution mode** - Cannot run in plan mode
- 🔴 **This command does NOT write code** - only creates workspace
- Prefers enhanced plans but accepts raw plans
- Filename derived from plan title, prompts user if extraction fails
- All errors follow consistent template with details and suggested actions
- This command does NOT switch directories or execute the plan
- User must manually run `workstack switch` and `/workstack:implement-plan` to begin implementation
- The `--permission-mode acceptEdits` flag is included to automatically accept edits during implementation
- Works best with plans created by `/workstack:enhance-plan`
