---
description: Create a workstack worktree from an implementation plan in context
---

# /workstack:create_from_plan

This command finds an implementation plan in the conversation context, saves it to disk, and creates a workstack worktree with that plan.

## Usage

```bash
/workstack:create_from_plan
```

## Prerequisites

- An implementation plan must exist in recent conversation context
- Current working directory must be in the workstack repository
- The plan should not already be saved to disk

## What Happens

When you run this command:

1. The assistant searches recent conversation for an implementation plan
2. Extracts and saves the plan as `<feature-name>-plan.md` at current worktree root
3. Creates a new workstack worktree with: `workstack create --plan <filename>-plan.md`
4. Displays instructions for switching to the worktree and implementing the plan

## Expected Outcome

- A new worktree created with your implementation plan
- Clear instructions for next steps
- No automatic execution (requires manual switch and implement command)

---

## Agent Instructions

You are executing the `/workstack:create_from_plan` command. Follow these steps carefully:

### Step 1: Detect Implementation Plan in Context

Search the recent conversation for an implementation plan. Look for:

- Markdown content with sections like "Implementation Plan:", "Overview", "Implementation Steps"
- Structured task lists or step-by-step instructions
- Headers containing words like "Plan", "Tasks", "Steps", "Implementation"

If no plan is found:

```
❌ Error: No implementation plan found in recent conversation

Please ensure an implementation plan has been presented recently in the conversation.
```

### Step 2: Extract and Process Plan Content

When a plan is found:

1. Extract the full markdown content of the plan
2. Preserve all formatting, headers, and structure
3. Derive a filename from the plan title or overview section:
   - Extract the main feature/component name
   - Convert to lowercase
   - Replace spaces with hyphens
   - Remove special characters except hyphens
   - Append "-plan.md"
   - Example: "User Authentication System" → `user-authentication-plan.md`

### Step 3: Detect Worktree Root

Execute: `git rev-parse --show-toplevel`

This returns the absolute path to the root of the current worktree. Store this as `<worktree-root>` for use in subsequent steps.

If the command fails:

```
❌ Error: Could not detect worktree root

Details: Not in a git repository or git command failed
Suggested action: Ensure you are in a valid git worktree
```

### Step 4: Save Plan to Disk

Use the Write tool to save the plan:

- Path: `<worktree-root>/<derived-filename>`
- Content: Full plan markdown content
- Verify file creation

If save fails, provide error:

```
❌ Error: Failed to save plan file

Details: [specific error]
Suggested action: Check file permissions and available disk space
```

### Step 5: Create Worktree with Plan

Execute: `workstack create --plan <worktree-root>/<filename> --json`

**Parse JSON output:**

1. Capture the command output
2. Parse as JSON to extract fields:
   - `worktree_name`: Name of the created worktree
   - `worktree_path`: Full path to worktree directory
   - `branch_name`: Git branch name
   - `plan_file`: Path to .PLAN.md file
   - `status`: Creation status

**Handle errors:**

- **JSON parsing fails**:

  ```
  ❌ Error: Failed to parse workstack create output

  Details: [error message]
  Suggested action: Ensure workstack is up to date
  ```

- **Worktree exists** (status = "exists"):

  ```
  ❌ Error: Worktree with this name already exists

  Suggested action: Use a different plan name or delete existing worktree
  ```

- **Invalid plan**: If command fails:

  ```
  ❌ Error: Failed to create worktree

  Details: [workstack error message]
  ```

**CRITICAL: Claude Code Directory Behavior**

🔴 **Claude Code CANNOT switch directories.** After `workstack create` runs, you will remain in your original directory. This is **NORMAL and EXPECTED**. The JSON output gives you all the information you need about the new worktree.

**Do NOT:**

- ❌ Try to verify with `git branch --show-current` (shows the OLD branch)
- ❌ Try to `cd` to the new worktree (will just reset back)
- ❌ Run any commands assuming you're in the new worktree

**Use the JSON output directly** for all worktree information.

### Step 6: Display Next Steps

After successful worktree creation, provide clear instructions:

```markdown
✅ Worktree created successfully!

**Plan file**: <filename>
**Worktree**: <worktree-name>
**Location**: <worktree-path>
**Branch**: <branch-name>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 **NEXT STEPS** (Required to begin implementation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**1. Switch to the worktree:**

    `workstack switch <worktree-name>`

**2. Start implementation:**

    `/workstack:implement_plan`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Other Commands

- To return to root repository: `workstack switch root`
- To view worktree status: `workstack ls`
```

## Error Handling Summary

All errors should follow this format:

```
❌ Error: [Brief description]

Details: [Specific error message or context]

Suggested action: [What the user should do to resolve]
```

Common error scenarios to handle:

- No plan in context
- Plan file save failures
- Worktree creation failures
- Duplicate worktree names

## Important Notes

- This command does NOT switch directories or execute the plan
- User must manually run `workstack switch` and `/workstack:implement_plan`
- The worktree name is automatically derived from the plan
- Always provide clear feedback at each step
