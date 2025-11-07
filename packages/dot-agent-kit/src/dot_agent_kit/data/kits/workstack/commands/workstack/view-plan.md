---
description: View and display the implementation plan from .PLAN.md in current directory
---

# /view-plan

This command views and displays the `.PLAN.md` file from the current directory, providing quick access to your implementation plan.

## What This Command Does

When you run this command, it will:

1. Check if `.PLAN.md` exists in the current directory
2. Read and display the entire plan file
3. Provide helpful error messages if the file is not found

## Usage

```bash
/view-plan
```

## Prerequisites

- Must be in a worktree directory that contains `.PLAN.md`
- Typically used after running `workstack switch <worktree-name>`

## Use Cases

- Quickly reference your implementation plan while working
- Review plan details before starting implementation
- Check success criteria for current phase
- Understand context after switching worktrees

---

## Agent Instructions

You are executing the `/view-plan` command. Follow these steps:

### Step 1: Check if .PLAN.md Exists

Check if `.PLAN.md` exists in the current working directory.

**Get current directory:**

Use Bash to determine the current directory: `pwd`

**Check for file:**

Check if `.PLAN.md` exists at `<current-dir>/.PLAN.md`

### Step 2: Handle File Not Found

If `.PLAN.md` does NOT exist, display this error message:

```
❌ Error: No .PLAN.md file found in current directory

Details: .PLAN.md files are created by workstack when you create a worktree with a plan

Suggested action:
  1. Check if you're in the correct worktree: workstack list
  2. Switch to a worktree with a plan: workstack switch <worktree-name>
  3. Create a new worktree with a plan: /workstack:create-from-plan
```

Then STOP - do not proceed to Step 3.

### Step 3: Display the Plan

If `.PLAN.md` EXISTS, read and display its contents:

1. Read the file using the Read tool
2. Display the contents to the user with a brief header

**Output format:**

```
📋 Implementation Plan (.PLAN.md)

[full file contents here]
```

That's it - simple and straightforward!

## Important Notes

- This is a read-only command - it never modifies files
- Works in any directory, but designed for workstack worktrees
- Provides helpful guidance when file is missing
- No interaction required - just displays the plan
