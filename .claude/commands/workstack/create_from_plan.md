---
description: Create a workstack worktree from an implementation plan in context (with optional guidance)
---

# /workstack:create_from_plan

This command finds an implementation plan in the conversation context, saves it to disk, and creates a workstack worktree with that plan.

## Usage

```bash
/workstack:create_from_plan [guidance]
```

**Examples:**

- `/workstack:create_from_plan` - Create worktree from plan as-is
- `/workstack:create_from_plan "Make error handling more robust and add retry logic"` - Apply guidance before creating worktree
- `/workstack:create_from_plan "Fix: Use LBYL instead of try/except throughout"` - Apply corrections to plan

## Prerequisites

- An implementation plan must exist in recent conversation context
- Current working directory must be in the workstack repository
- The plan should not already be saved to disk
- (Optional) Guidance text for final corrections/additions to the plan

## What Happens

When you run this command:

1. The assistant searches recent conversation for an implementation plan
2. If guidance provided, AI intelligently merges it into the plan (corrections, additions, clarifications)
3. Extracts and saves the (possibly modified) plan as `<feature-name>-plan.md` at current worktree root
4. Creates a new workstack worktree with: `workstack create --plan <filename>-plan.md`
5. Displays instructions for switching to the worktree and implementing the plan

**Note:** This command does NOT implement code - it only creates the workspace with the plan.

## Expected Outcome

- A new worktree created with your implementation plan
- Clear instructions for next steps
- No automatic execution (requires manual switch and implement command)

---

## 🔴 CRITICAL: This Command Does NOT Implement Code

**This command's ONLY job:**

1. Find the plan in context
2. (Optional) Apply guidance to modify the plan
3. Save plan to disk
4. Create worktree with `workstack create --plan`

**DO NOT:**

- ❌ Write ANY code files (.py, .ts, .js, etc.)
- ❌ Make ANY edits to existing code
- ❌ Run tests, linters, or formatters
- ❌ Execute any part of the implementation
- ❌ Create anything except the plan file

**The implementation happens later** when the user runs `/workstack:implement_plan` after switching to the worktree.

---

## Agent Instructions

You are executing the `/workstack:create_from_plan` command. Follow these steps carefully:

### Step 0: READ THIS FIRST - Scope Limitation 🔴

**YOUR ONLY TASKS:**

1. Extract implementation plan from conversation
2. Apply guidance modifications if provided
3. Save plan to disk as markdown file
4. Run `workstack create --plan <file>`
5. Display next steps to user

**FORBIDDEN ACTIONS:**

- Writing ANY code files (.py, .ts, .js, etc.)
- Making ANY edits to existing codebase
- Running ANY commands except `git rev-parse` and `workstack create`
- Implementing ANY part of the plan

This command sets up the workspace. Implementation happens in the worktree via `/workstack:implement_plan`.

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

### Step 1.5: Apply Guidance to Plan (if provided)

**Check for guidance argument:**

If guidance text is provided as an argument to this command:

1. Read the extracted plan from Step 1
2. Read the guidance text (corrections, additions, clarifications, priority changes, etc.)
3. Use AI reasoning to intelligently merge the guidance into the plan:
   - Update relevant sections based on guidance
   - Add new sections if guidance introduces new requirements
   - Correct errors or approaches if guidance identifies issues
   - Adjust priorities or ordering if guidance suggests changes
   - Integrate guidance naturally into the plan structure (not just appended)
4. Produce the modified plan content

If no guidance provided: use the original plan as-is from Step 1

**Output:** Final plan content (original or modified) ready for Step 2 processing

### Step 2: Extract and Process Plan Content (with Guidance Applied)

At this point, you have the final plan content (original or modified by guidance from Step 1.5):

1. The plan content is ready (already includes any guidance modifications)
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

After successful worktree creation, provide clear instructions.

**IMPORTANT:** You have NOT implemented any code. Implementation happens after the user switches to the worktree.

Use the following output format:

```markdown
✅ Worktree created: **<worktree-name>**

Plan: `<filename>`
Branch: `<branch-name>`
Location: `<worktree-path>`

**Next step:**

`workstack switch <worktree-name> && claude "/workstack:implement_plan"`
```

**Note:** The final output the user sees should be the single copy-pasteable command above. No additional text after that command.

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

- 🔴 **This command does NOT write code** - only creates workspace with plan
- This command does NOT switch directories or execute the plan
- This command does NOT run tests, linters, formatters, or any implementation tasks
- User must manually run `workstack switch` and `/workstack:implement_plan` to begin implementation
- The worktree name is automatically derived from the plan
- Optional guidance parameter allows final corrections/additions before persisting plan
- Always provide clear feedback at each step
