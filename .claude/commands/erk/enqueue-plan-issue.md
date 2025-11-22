---
description: Enqueue existing plan issue for automatic implementation
---

# /erk:enqueue-plan-issue

## Goal

**Add the `erk-queue` label to an existing plan issue to trigger automatic implementation.**

This command takes an existing GitHub issue (created with `erk-plan` label) and adds the `erk-queue` label, which triggers the GitHub Actions workflow for automatic implementation.

**What this command does:**

- ✅ Fetch existing plan issue by identifier
- ✅ Verify issue exists
- ✅ Ensure `erk-queue` label exists (create if needed)
- ✅ Add `erk-queue` label to issue (keeps existing labels)
- ✅ Display confirmation
- ✅ Show workflow monitoring instructions

## What Happens

When you run this command, these steps occur:

1. **Parse Identifier** - Extract issue number or identifier from user input
2. **Verify Issue** - Confirm the plan issue exists
3. **Ensure Label Exists** - Check for `erk-queue` label, create if missing
4. **Add Label** - Add `erk-queue` to the issue (keeps all existing labels including `erk-plan`)
5. **Automatic Implementation** - GitHub Actions workflow automatically starts implementation
6. **Display Result** - Show success confirmation and monitoring instructions

## Usage

### By Issue Number

```bash
/erk:enqueue-plan-issue 42
```

### By GitHub URL

```bash
/erk:enqueue-plan-issue https://github.com/owner/repo/issues/42
```

### By Plan Issue Identifier

```bash
/erk:enqueue-plan-issue github-123
```

## Key Difference from `/erk:create-queued-plan`

**`/erk:create-queued-plan`**: Creates a NEW issue with `erk-queue` label from a plan file
**`/erk:enqueue-plan-issue`**: Adds `erk-queue` label to an EXISTING issue

Use `/erk:enqueue-plan-issue` when:

- Issue already exists with `erk-plan` label
- You want to convert manual workflow to automatic
- You've reviewed the issue and are ready for auto-implementation

## Label Behavior

**Important:** This command is **additive** - it adds the `erk-queue` label without removing any existing labels like `erk-plan`. After enqueuing, the issue will have both labels.

## Prerequisites

- Issue must exist (typically created with `/erk:create-planned-issue`)
- Current working directory must be in a git repository
- `gh` CLI must be installed and authenticated

## Success Criteria

This command succeeds when ALL of the following are true:

**Issue Validation:**
✅ Issue exists and is accessible
✅ Issue identifier correctly parsed

**Label Pre-flight:**
✅ `erk-queue` label exists (created if missing)

**Label Addition:**
✅ `erk-queue` label added to issue
✅ Existing labels preserved (not removed)
✅ GitHub Actions workflow triggered automatically
✅ Success confirmation displayed

## Troubleshooting

### "Issue not found"

**Cause:** Issue number doesn't exist or you don't have access
**Solution:**

- Verify issue exists: `gh issue view <number>`
- Check you're in the correct repository
- Ensure you have access to the repository

### "gh CLI not available"

**Cause:** gh CLI not installed or not in PATH
**Solution:**

- Install: `brew install gh` (macOS) or see https://cli.github.com
- Authenticate: `gh auth login`

### "Failed to add label"

**Cause:** GitHub API error or permissions issue
**Solution:**

- Check network connectivity
- Verify you have write access to the repository
- Check API rate limits: `gh api rate_limit`

### "Workflow not triggered"

**Cause:** GitHub Actions workflow may not be enabled or `erk-queue` label not recognized
**Solution:**

- Verify workflow exists: `.github/workflows/dispatch-erk-queue.yml`
- Check workflow runs: `gh run list`
- Manually check issue labels: `gh issue view <number>`

### "PR creation failed: not permitted to create pull requests"

**Cause:** GitHub Actions token lacks permission to create PRs
**Solution:**

1. Navigate to **Settings > Actions > General**
2. Enable "Allow GitHub Actions to create and approve pull requests"
3. If in organization: Also check **Organization Settings > Actions**
4. Re-run the workflow by adding/removing the label

## Integration with Workflow

**Typical workflow (converting manual to automatic):**

1. Create plan: `/erk:save-context-enriched-plan`
2. Create issue: `/erk:create-planned-issue` (manual workflow)
3. Review issue on GitHub
4. **Enqueue for auto-implementation:** `/erk:enqueue-plan-issue <issue-number>` ← **YOU ARE HERE**
5. GitHub Actions automatically:
   - Creates branch from issue title
   - Creates `.plan/` folder structure
   - Runs `/erk:implement-plan`
   - Creates pull request

**Alternative workflow (automatic from start):**

1. Create plan: `/erk:save-context-enriched-plan`
2. Create queued issue: `/erk:create-queued-plan` (automatic from start)

---

## Agent Instructions

You are executing the `/erk:enqueue-plan-issue` command. Follow these steps carefully:

### Step 1: Parse Issue Identifier

Extract the issue identifier from user input. Accept these formats:

- **Issue number**: `42`, `123`
- **GitHub URL**: `https://github.com/owner/repo/issues/42`
- **Plan issue identifier**: `github-123`, `PROJ-456`

Parse logic:

1. If input contains `github.com/`, extract issue number from URL path
2. If input is numeric only, use as-is
3. Otherwise, use as plan issue identifier

Store the parsed value as `identifier` (string).

### Step 2: Execute CLI Command

Use the Bash tool to run the `erk plan-issue enqueue` command:

```bash
erk plan-issue enqueue <identifier>
```

### Step 3: Check Command Result

1. If exit code is 0:
   - Parse output for success message
   - Extract issue number from output (format: `#<number>`)
   - Continue to Step 4

2. If exit code is non-zero:
   - Display error message from command output
   - Provide troubleshooting suggestions based on error
   - Exit cleanly

### Step 4: Display Success and Monitoring Instructions

Show success confirmation and guide user on monitoring:

```
✅ Issue enqueued for automatic implementation!

The issue now has the erk-queue label, which triggers GitHub Actions to:
- Create a branch from the issue
- Set up .plan/ folder structure
- Run implementation via Claude Code
- Create pull request with results

Monitor progress:
- View issue: gh issue view <number>
- Watch workflow: gh run list
- Check Actions tab: <repo-url>/actions

The workflow typically completes in 5-15 minutes depending on plan complexity.
```

### Important Notes

- **Uses CLI command**: This slash command delegates to `erk plan-issue enqueue`
- **Error handling**: CLI command handles all validation and API calls
- **Additive operation**: Does not remove existing labels
- **Automatic trigger**: Adding label immediately starts GitHub Actions workflow
- **No worktree linking**: This command only adds labels, doesn't interact with `.plan/` folders

### Error Handling

If the CLI command fails:

1. Show the error message from the command
2. Suggest relevant troubleshooting based on error type:
   - "not found" → Check issue number and repository
   - "not authenticated" → Run `gh auth login`
   - "permission denied" → Verify repository access
   - "API rate limit" → Wait or check `gh api rate_limit`
3. Exit cleanly with clear guidance

### Example Execution

**User input:** `/erk:enqueue-plan-issue 42`

**Agent actions:**

1. Parse identifier: `"42"`
2. Execute: `erk plan-issue enqueue 42`
3. Command succeeds with exit code 0
4. Display success message with monitoring instructions
5. Done

**User input:** `/erk:enqueue-plan-issue https://github.com/owner/repo/issues/123`

**Agent actions:**

1. Parse URL, extract: `"123"`
2. Execute: `erk plan-issue enqueue 123`
3. Command succeeds with exit code 0
4. Display success message
5. Done
