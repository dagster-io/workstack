---
description: Create GitHub issue from persisted plan with auto-implementation queue label
---

# /erk:queue-plan

⚠️ **DEPRECATED**: This command is deprecated. The workflow has been simplified to create GitHub issues directly from conversation without requiring disk files.

**For automatic implementation via GitHub Actions**, consider updating your automation to:

1. Use `/erk:enhance-and-save-plan` or `/erk:save-plan` to create the issue
2. Add the `erk-queue` label to the created issue using `gh issue edit <number> --add-label erk-queue`

This command remains functional for backward compatibility with existing plan files on disk and automation workflows.

## Goal

**Create a GitHub issue from an existing plan file on disk with the `erk-queue` label for automatic implementation.**

This command detects plan files at the repository root, selects the most recent one, creates a GitHub issue with the plan content, adds the `erk-queue` label (which triggers automatic implementation), and optionally links it to an existing worktree's `.impl/` folder.

**What this command does:**

- ✅ Auto-detect most recent `*-plan.md` file at repo root
- ✅ Extract title from plan front matter or first H1 heading
- ✅ Ensure `erk-queue` label exists (create if needed)
- ✅ Create GitHub issue with plan body as content
- ✅ Add label: `erk-queue` (triggers automatic implementation workflow)
- ✅ Save issue reference to `.impl/issue.json` (if worktree exists)
- ✅ Display issue URL

## What Happens

When you run this command, these steps occur:

1. **Verify Scope** - Confirm we're in a git repository with gh CLI available
2. **Detect Plan File** - Find and select most recent `*-plan.md` at repo root
3. **Parse Plan** - Extract title and body from markdown
4. **Ensure Label Exists** - Check for `erk-queue` label, create if missing
5. **Create Issue** - Use gh CLI to create issue with `erk-queue` label
6. **Automatic Implementation** - GitHub Actions workflow automatically starts implementation
7. **Link to Worktree** - If `.impl/` folder exists in current worktree, save issue reference
8. **Display Result** - Show issue number and URL

## Usage

```bash
/erk:queue-plan
```

**No arguments accepted** - This command automatically detects and uses the most recent plan file.

## Optional: Link Existing Issue

If you want to link an existing issue instead of creating a new one:

```bash
/erk:queue-plan --link 123
```

This will save the issue reference without creating a new issue. Use this when:

- Issue was created manually on GitHub
- Want to associate an existing issue with a worktree

## Key Difference from `/erk:create-plan-from-file`

**`/erk:create-plan-from-file`**: Creates issue with `erk-plan` label (manual implementation)
**`/erk:queue-plan`**: Creates issue with `erk-queue` label (automatic implementation via GitHub Actions)

Use `/erk:queue-plan` when you want the implementation to happen automatically via CI. Use `/erk:create-plan-from-file` when you want to manually implement the plan.

## Prerequisites

- At least one `*-plan.md` file must exist at repository root
- Current working directory must be in a git repository
- `gh` CLI must be installed and authenticated
- Typically run after `/erk:save-context-enriched-plan`
- Can run before or after `/erk:create-planned-wt`

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Detection:**
✅ Plan file detected at repository root
✅ Most recent plan file selected (if multiple exist)
✅ Title extracted from front matter or H1 heading

**Label Pre-flight:**
✅ `erk-queue` label exists (created if missing)

**Issue Creation:**
✅ GitHub issue created with plan content
✅ Label added: `erk-queue`
✅ Issue URL displayed
✅ GitHub Actions workflow triggered automatically

**Worktree Linking (if applicable):**
✅ If `.impl/` folder exists: issue reference saved to `.impl/issue.json`
✅ If no `.impl/` folder: issue created but not linked (can link later)

## Troubleshooting

### "No plan files found"

**Cause:** No `*-plan.md` files exist at repository root
**Solution:**

- Run `/erk:save-context-enriched-plan` to create a plan first
- Ensure plan file ends with `-plan.md`
- Verify you're in the correct repository

### "gh CLI not available"

**Cause:** gh CLI not installed or not in PATH
**Solution:**

- Install: `brew install gh` (macOS) or see https://cli.github.com
- Authenticate: `gh auth login`

### "gh not authenticated"

**Cause:** gh CLI installed but not authenticated with GitHub
**Solution:**

- Run: `gh auth login`
- Follow prompts to authenticate

### "Failed to create issue"

**Cause:** GitHub API error or network issue
**Solution:**

- Check network connectivity
- Verify repository access: `gh repo view`
- Check API rate limits: `gh api rate_limit`

### "Issue created but not linked"

**Cause:** No `.impl/` folder in current worktree
**Solution:**

- This is expected if you haven't created a worktree yet
- Create worktree: `/erk:create-planned-wt`
- Navigate to worktree: `erk checkout <branch>`
- Re-run: `/erk:queue-plan --link <issue-number>`

### "Workflow not triggered"

**Cause:** GitHub Actions workflow may not be enabled or `erk-queue` label not recognized
**Solution:**

- Verify workflow exists: `.github/workflows/dispatch-erk-queue.yml`
- Check workflow runs: `gh run list`
- Manually trigger if needed: Add `erk-queue` label to issue

### "PR creation failed: not permitted to create pull requests"

**Cause:** GitHub Actions token lacks permission to create PRs
**Solution:**

1. Navigate to **Settings > Actions > General**
2. Enable "Allow GitHub Actions to create and approve pull requests"
3. If in organization: Also check **Organization Settings > Actions**
4. Re-run the workflow

## Integration with Workflow

**Typical workflow (automatic implementation):**

1. Create plan: `/erk:save-context-enriched-plan`
2. Create queued issue: `/erk:queue-plan` ← **YOU ARE HERE**
3. GitHub Actions automatically:
   - Creates branch from issue title
   - Creates `.impl/` folder structure
   - Runs `/erk:implement-plan`
   - Creates pull request

**Alternative workflow (manual implementation):**

1. Create plan: `/erk:save-context-enriched-plan`
2. Create issue: `/erk:create-plan-from-file` (uses `erk-plan` label, no auto-implementation)
3. Create worktree: `/erk:create-wt-from-plan-file`
4. Navigate and implement: `erk checkout <branch> && claude --permission-mode acceptEdits "/erk:implement-plan"`

---

## Agent Instructions

You are executing the `/erk:queue-plan` command. Follow these steps carefully:

### Step 1: Check for --link Flag

Parse user input to check if `--link <issue-number>` was provided:

- If `--link 123` provided: Skip to Step 7 (link existing issue)
- If no flag: Continue to Step 2 (create new issue)

### Step 2: Verify Prerequisites

Check that required tools are available:

1. Verify we're in a git repository:

   ```bash
   git rev-parse --git-dir
   ```

   If fails: Error and exit

2. Check if gh CLI is available:

   ```bash
   gh --version
   ```

   If fails: Show installation instructions and exit

3. Check gh authentication:
   ```bash
   gh auth status
   ```
   If fails: Show `gh auth login` instructions and exit

### Step 3: Detect Plan File

Find the most recent `*-plan.md` file at repository root using the kit CLI command:

1. Use the find-most-recent-plan-file command:

   ```bash
   result=$(dot-agent kit-command erk find-most-recent-plan-file)
   ```

2. Parse the JSON result:

   ```bash
   if ! echo "$result" | jq -e '.success' > /dev/null; then
       error=$(echo "$result" | jq -r '.message')
       echo "❌ Error: $error"
       exit 1
   fi

   plan_file=$(echo "$result" | jq -r '.plan_file')
   ```

3. If no files found (success=false with error="no_plan_files_found"):

   ```
   ❌ Error: No plan files found at repository root

   Run /erk:save-context-enriched-plan to create a plan first.
   ```

   Exit with error.

### Step 4: Create GitHub Issue (Single Command)

Use the composite kit CLI command that handles the complete workflow for queued plans:

- Reads plan file from disk
- Extracts title from plan
- Ensures erk-queue label exists
- Creates GitHub issue with plan body and erk-queue label
- Returns structured JSON result

**Algorithm:**

1. Call the composite kit command with the plan file path:

   ```bash
   result=$(dot-agent kit-command erk create-queued-plan "<path-to-plan-file>")

   # Parse JSON output
   if ! echo "$result" | jq -e '.success' > /dev/null; then
       echo "❌ Error: Failed to create GitHub issue" >&2
       exit 1
   fi

   issue_number=$(echo "$result" | jq -r '.issue_number')
   issue_url=$(echo "$result" | jq -r '.issue_url')
   ```

2. If command fails:

   ```
   ❌ Error: Failed to create GitHub issue

   Troubleshooting:
   - Check file exists and is readable
   - Check authentication: gh auth status
   - Verify repository access: gh repo view
   - Check network connectivity
   ```

   Exit with error.

**What this command does internally:**

- Reads plan file using Python (not shell cat)
- Extracts title (H1 → H2 → first line fallback)
- Ensures erk-queue label exists (creates if needed with orange color)
- Creates issue with full plan as body and erk-queue label
- Returns JSON: `{"success": true, "issue_number": 123, "issue_url": "..."}`

**Note:** The erk-queue label indicates this issue is queued for automatic implementation by the erk system, as opposed to erk-plan which is for manual execution.

### Step 5: Display Issue URL

Show success message with issue information:

```
✅ GitHub issue created successfully!

Issue #<number>: <title>
URL: <issue-url>
Label: erk-queue (automatic implementation will begin)

GitHub Actions will automatically:
- Create branch from issue title
- Set up .impl/ folder structure
- Run implementation via Claude Code
- Create pull request with results

You can monitor progress:
- View issue: gh issue view <number>
- Watch workflow: gh run list
- Check Actions tab: <repo-url>/actions
```

### Step 6: Link Issue to Worktree (if .impl/ exists)

Check if current directory has a `.impl/` folder:

1. Check for `.impl/` directory:

   ```bash
   test -d .impl && echo "exists" || echo "not found"
   ```

2. If `.impl/` exists:
   - Use `ctx.issues.get_issue(repo_root, issue_number)` to fetch issue details
   - Import: `from erk.core.impl_folder import save_issue_reference`
   - Call: `save_issue_reference(Path.cwd() / ".impl", issue_number, issue_url)`
   - Display:

     ```
     📋 Issue linked to worktree

     Issue reference saved to .impl/issue.json

     The issue will be updated with progress during automatic implementation.
     ```

3. If `.impl/` doesn't exist:
   - Display informational message:

     ```
     ℹ️  Issue created but not linked to a worktree

     The GitHub Actions workflow will create a new branch and implement automatically.
     ```

### Step 7: Handle --link Flag

If user provided `--link <issue-number>`:

1. Fetch issue using gh CLI:

   ```bash
   gh issue view <issue-number> --json number,title,url
   ```

2. If issue not found:

   ```
   ❌ Error: Issue #<number> not found

   Verify issue exists: gh issue view <number>
   ```

   Exit with error.

3. Check for `.impl/` directory (same as Step 8)

4. If `.impl/` exists:
   - Save issue reference using `save_issue_reference()`
   - Display:

     **IMPORTANT:** Output each field on its own line. Preserve newlines between fields - do not concatenate into a single line.

     ```
     ✅ Issue #<number> linked to worktree

     Issue: <title>
     URL: <url>

     Issue reference saved to .impl/issue.json
     ```

5. If `.impl/` doesn't exist:

   ```
   ❌ Error: No .impl/ folder found in current directory

   The --link flag requires a .impl/ folder in the current worktree.
   ```

   Exit with error.

### Important Notes

- **Automatic implementation**: This command triggers automatic implementation via GitHub Actions
- **Label difference**: Uses `erk-queue` (auto) vs `erk-plan` (manual)
- **Workflow monitoring**: User should monitor GitHub Actions for implementation progress
- **Graceful degradation**: Creating issue without linking is valid (can link later)
- **Idempotent linking**: Can run `--link` multiple times safely (overwrites `.impl/issue.json`)
- **Context usage**: Use `ctx.issues.create_issue()` for issue creation (injected via ErkContext)

### Error Handling

If any critical step fails:

1. Explain what went wrong
2. Show relevant command output
3. Suggest troubleshooting steps
4. Exit cleanly with error message
