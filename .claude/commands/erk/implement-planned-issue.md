---
description: Execute implementation plan from linked GitHub issue
---

# /erk:implement-planned-issue

This command reads the GitHub issue linked in `.plan/issue.json`, fetches its body, saves it as `.plan/plan.md`, and then executes the plan. It combines issue fetching with plan execution in a single workflow.

## Usage

```bash
/erk:implement-planned-issue
```

## Prerequisites

- Must be in a worktree directory that contains `.plan/` folder
- `.plan/issue.json` must exist with valid issue reference
- Typically run after `/erk:create-planned-wt` and `erk checkout <branch>`

## What Happens

When you run this command:

1. Reads `.plan/issue.json` to get issue number
2. Fetches issue body from GitHub using gh CLI
3. Saves issue body to `.plan/plan.md` (overwrites if exists)
4. Delegates to `/erk:implement-plan` for execution

## Expected Outcome

- Issue body becomes the executable plan
- Plan is executed with progress tracking
- Progress comments posted back to the issue
- Clear completion summary

## Typical Workflow

1. Create plan: `/erk:save-context-enriched-plan`
2. Create issue: `/erk:create-planned-issue`
3. Create worktree: `/erk:create-planned-wt`
4. Navigate: `erk checkout <branch>`
5. Execute: `/erk:implement-planned-issue` ← **YOU ARE HERE**

---

## Agent Instructions

You are executing the `/erk:implement-planned-issue` command. Follow these steps carefully:

### Step 1: Verify .plan/ Folder Exists

Check that `.plan/` folder exists in the current directory.

If not found:

```
❌ Error: No .plan/ folder found in current directory

This command must be run from a worktree with a plan folder.

To create a worktree:
1. Run /erk:create-planned-wt to create worktree from plan
2. Run: erk checkout <branch>
3. Then run: /erk:implement-planned-issue
```

Exit with error.

### Step 2: Read Issue Reference

Check that `.plan/issue.json` exists and read the issue number.

1. Check for file:

   ```bash
   test -f .plan/issue.json && echo "exists" || echo "not found"
   ```

2. If not found:

   ```
   ❌ Error: No GitHub issue linked to this plan

   .plan/issue.json not found in current directory.

   To link an issue:
   1. Create issue from plan: /erk:create-planned-issue
   2. Or link existing issue: /erk:create-planned-issue --link <issue-number>
   ```

   Exit with error.

3. Read issue reference using Read tool:

   ```bash
   Read .plan/issue.json
   ```

4. Parse JSON to extract `number` field

### Step 3: Fetch Issue Body

Use gh CLI to fetch the issue body from GitHub.

1. Fetch issue:

   ```bash
   gh issue view <issue-number> --json body --jq '.body'
   ```

2. If command fails:

   ```
   ❌ Error: Failed to fetch GitHub issue #<number>

   Command output: <stderr>

   Troubleshooting:
   - Check network connectivity
   - Verify issue exists: gh issue view <number>
   - Check authentication: gh auth status
   ```

   Exit with error.

3. Store the issue body content

### Step 4: Save Issue Body as Plan

Write the issue body to `.plan/plan.md`, overwriting if it exists.

Use the Write tool to save the content:

```python
Write(
    file_path=".plan/plan.md",
    content=issue_body
)
```

Display confirmation:

```
📋 Plan synchronized from GitHub issue #<number>

Saved to: .plan/plan.md

Now executing the plan...
```

### Step 5: Delegate to /erk:implement-plan

Execute the plan using the existing implement-plan command.

Use SlashCommand tool:

```python
SlashCommand(command="/erk:implement-plan")
```

This will:

- Read `.plan/plan.md` (the issue body you just saved)
- Execute the implementation steps
- Update `.plan/progress.md` with checkboxes
- Post progress comments back to the GitHub issue
- Provide completion summary

### Important Notes

- **Overwrites plan.md**: This command replaces `.plan/plan.md` with issue body
- **Use with caution**: If you've made local edits to plan.md, they will be lost
- **Idempotent**: Safe to run multiple times (re-syncs from issue)
- **Delegates execution**: All actual implementation happens in /erk:implement-plan

### Error Handling

If any critical step fails:

1. Explain what went wrong
2. Show relevant command output
3. Suggest troubleshooting steps
4. Exit cleanly with error message
