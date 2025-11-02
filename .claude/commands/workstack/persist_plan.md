---
description: Save implementation plan from context and create worktree
---

# /workstack:persist_plan

This command finds an implementation plan in the conversation context, saves it to disk, and creates a workstack worktree with that plan.

## Usage

```bash
/workstack:persist_plan
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

You are executing the `/workstack:persist_plan` command. Follow these steps carefully:

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

Execute: `workstack create --plan <worktree-root>/<filename>`

Use the absolute path from Step 3 to ensure workstack can find the plan file regardless of current working directory.

Parse the output to extract:

- Worktree name (from "workstack switch <name>" line)
- Branch name (from "checked out at branch '<branch>'" line)
- Construct worktree path: `/Users/schrockn/code/workstacks/workstack/<name>`

Handle specific errors:

- **Worktree exists**:

  ```
  ❌ Error: Worktree with this name already exists

  Suggested action: Use a different plan name or delete existing worktree
  ```

- **Invalid plan**:

  ```
  ❌ Error: Plan file format is invalid

  Details: [workstack error message]
  ```

### Step 6: Display Next Steps

After successful worktree creation, provide clear instructions:

```markdown
✅ Worktree created successfully!

**Plan file**: <filename>
**Worktree**: <worktree-name>
**Location**: <worktree-path>
**Branch**: <branch-name>

To switch to the worktree and begin implementation, run:

    workstack switch <worktree-name>

Then execute:

    /workstack:implement_plan

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
