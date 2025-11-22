---
description: Execute implementation plan from GitHub issue with erk-plan label
---

# /erk:implement-plan-issue

Take over an existing worktree by fetching a GitHub issue with the `erk-plan` label and executing its implementation plan. This command creates a `.plan/` folder from the issue and delegates to `/erk:implement-plan` for execution.

## Usage

```bash
/erk:implement-plan-issue <issue-number-or-url>
```

**Examples:**

```bash
# Using issue number
/erk:implement-plan-issue 123

# Using GitHub URL
/erk:implement-plan-issue https://github.com/owner/repo/issues/123
```

## Prerequisites

- Must be in a worktree directory that does NOT have a `.plan/` folder
- Issue must have `erk-plan` label on GitHub
- GitHub CLI (`gh`) must be authenticated

## What Happens

When you run this command:

1. Parses input (issue number or GitHub URL)
2. Checks that `.plan/` folder does NOT exist (errors if exists)
3. Fetches issue from GitHub
4. Validates issue has `erk-plan` label (errors if missing)
5. Creates `.plan/` directory
6. Saves issue body to `.plan/plan.md`
7. Saves issue reference to `.plan/issue.json`
8. Delegates to `/erk:implement-plan` for execution

## Expected Outcome

- `.plan/` folder created with issue contents
- Plan execution starts with progress tracking
- Progress comments posted back to the issue
- Clear completion summary

## Typical Workflow

**Scenario:** You have an existing worktree (created manually or via `erk create`) and want to "take it over" with a plan from a GitHub issue.

```bash
# 1. Create worktree (if not already created)
erk create my-feature

# 2. Navigate to worktree
erk checkout my-feature

# 3. Take over with plan issue
/erk:implement-plan-issue 123
```

## Comparison with Other Commands

| Command                        | Use Case                                                      |
| ------------------------------ | ------------------------------------------------------------- |
| `/erk:implement-plan`          | Execute existing `.plan/plan.md` in current directory         |
| `/erk:implement-plan-issue`    | **THIS COMMAND** - Fetch issue, create `.plan/`, then execute |
| `/erk:create-planned-issue-wt` | Create BOTH issue and worktree from plan file                 |

---

## Agent Instructions

You are executing the `/erk:implement-plan-issue` command. Follow these steps carefully:

### Step 1: Parse Input Argument

**Extract issue number from input:**

The command accepts either:

- Issue number: `123`
- GitHub URL: `https://github.com/owner/repo/issues/123`

**Parsing logic:**

1. Check if input contains `github.com/`
2. If yes: Extract issue number using regex `github\.com/[^/]+/[^/]+/issues/(\d+)`
3. If no: Treat input as issue number directly

**If no argument provided:**

```
❌ Error: Missing required argument

Usage: /erk:implement-plan-issue <issue-number-or-url>

Examples:
  /erk:implement-plan-issue 123
  /erk:implement-plan-issue https://github.com/owner/repo/issues/123
```

Exit with error.

**If parsing fails:**

```
❌ Error: Invalid issue reference

Could not parse issue number from: <input>

Expected formats:
  - Issue number: 123
  - GitHub URL: https://github.com/owner/repo/issues/123
```

Exit with error.

**Store the extracted issue number for Step 3.**

### Step 2: Verify .plan/ Folder Does NOT Exist

Check that `.plan/` folder does NOT exist in the current directory.

**Use Bash to check:**

```bash
test -d .plan && echo "exists" || echo "not found"
```

**If .plan/ exists:**

```
❌ Error: Cannot take over worktree that already has .plan/ folder

This command creates a new .plan/ folder from a GitHub issue.
The current directory already has a .plan/ folder with existing content.

To execute the existing plan:
  /erk:implement-plan

To replace the plan manually:
  1. Back up existing plan: mv .plan .plan.backup
  2. Run this command again: /erk:implement-plan-issue <issue>
```

Exit with error.

**If not found:** Continue to Step 3.

### Step 3: Fetch Issue from GitHub

**IMPORTANT:** Use the Python integration layer, NOT direct gh CLI.

Use `ctx.issues.get_issue(repo_root, issue_number)` to fetch the issue.

**Required imports (agent mental model):**

- `ctx` provides `issues` integration (ABC interface)
- `repo_root` is available from `ctx.repo_root` or can be detected via `git rev-parse --show-toplevel`
- `get_issue()` returns `IssueInfo` dataclass with fields: `number`, `title`, `body`, `state`, `url`, `labels`

**Example usage pattern:**

```python
# Fetch issue
try:
    issue = ctx.issues.get_issue(repo_root, issue_number)
except Exception as e:
    # Handle GitHub API errors
    ...
```

**If fetch fails:**

```
❌ Error: Failed to fetch GitHub issue #<number>

Details: <error message>

Troubleshooting:
  1. Check network connectivity
  2. Verify issue exists: gh issue view <number>
  3. Check authentication: gh auth status
  4. Ensure you have read permissions for this repository
```

Exit with error.

**Store the issue info for Step 4.**

### Step 4: Validate erk-plan Label

Check that the issue has the `erk-plan` label.

**Label validation:**

```python
# Case-insensitive label check
labels_lower = [label.lower() for label in issue.labels]
if "erk-plan" not in labels_lower:
    # Error - label missing
    ...
```

**If label missing:**

```
❌ Error: Issue #<number> does not have 'erk-plan' label

This command only executes issues marked with the 'erk-plan' label to prevent
accidentally executing non-plan issues.

Issue labels: <list of labels, or "none">

To add the label:
  gh issue edit <number> --add-label "erk-plan"

Or use a different command for existing plans:
  /erk:implement-plan
```

Exit with error.

**If label found:** Continue to Step 5.

### Step 5: Create .plan/ Directory

Create the `.plan/` folder in the current directory.

**Use Bash:**

```bash
mkdir .plan
```

**If creation fails:**

```
❌ Error: Failed to create .plan/ directory

Details: <error message>

Check:
  - File permissions in current directory
  - Available disk space
```

Exit with error.

### Step 6: Save Issue Body as .plan/plan.md

Write the issue body to `.plan/plan.md`.

**Use Write tool:**

```python
Write(
    file_path=".plan/plan.md",
    content=issue.body
)
```

**If write fails:**

```
❌ Error: Failed to save plan file

Details: <error message>

Check:
  - .plan/ directory was created
  - File permissions
```

Exit with error.

**Display confirmation:**

```
📋 Plan loaded from GitHub issue #<number>

Title: <issue.title>
Saved to: .plan/plan.md

Now executing the plan...
```

### Step 7: Save Issue Reference

Save the issue reference to `.plan/issue.json` for progress tracking.

**Use the plan_folder utilities:**

```python
from erk.core.plan_folder import save_issue_reference

save_issue_reference(
    plan_dir=Path(".plan"),
    issue_number=issue.number,
    issue_url=issue.url
)
```

**This creates `.plan/issue.json` with:**

```json
{
  "number": 123,
  "url": "https://github.com/owner/repo/issues/123"
}
```

**If save fails:**

```
❌ Warning: Failed to save issue reference

The plan file was created but issue tracking may not work properly.
Progress comments will not be posted to the GitHub issue.

Details: <error message>

You can continue with plan execution, but progress tracking may be limited.
```

Show warning but continue (non-critical).

### Step 8: Delegate to /erk:implement-plan

Execute the plan using the existing implement-plan command.

**Use SlashCommand tool:**

```python
SlashCommand(command="/erk:implement-plan")
```

This will:

- Read `.plan/plan.md` (the issue body you just saved)
- Execute the implementation steps
- Update `.plan/progress.md` with checkboxes
- Post progress comments back to the GitHub issue (via `.plan/issue.json`)
- Provide completion summary

**The /erk:implement-plan command handles:**

- Plan parsing and execution
- Progress tracking
- GitHub issue updates
- Error handling

### Important Notes

- **Safety first**: `.plan/` existence check prevents accidental overwrites
- **Label requirement**: Only issues with `erk-plan` label can be executed
- **Integration layer**: Uses `ctx.issues.get_issue()` for testability and consistency
- **Delegation pattern**: All plan execution logic lives in `/erk:implement-plan`
- **Issue reference**: Saved for progress tracking and GitHub integration

### Error Handling

All errors follow the standard format:

```
❌ Error: [Brief description]

[Details and context]

[Troubleshooting steps or suggested actions]
```

**Critical failures (must exit):**

- No argument provided
- Invalid argument format
- .plan/ folder already exists
- Issue fetch fails
- erk-plan label missing
- Directory creation fails
- Plan file write fails

**Non-critical failures (warn and continue):**

- Issue reference save fails (progress tracking limited)

### Testing Checklist

After implementation, verify:

- [ ] Accepts issue numbers (e.g., 123)
- [ ] Accepts GitHub URLs (e.g., https://github.com/owner/repo/issues/123)
- [ ] Errors if no argument provided
- [ ] Errors if .plan/ exists
- [ ] Errors if issue missing erk-plan label
- [ ] Creates .plan/ directory
- [ ] Saves issue body to .plan/plan.md
- [ ] Saves issue reference to .plan/issue.json
- [ ] Delegates to /erk:implement-plan successfully
