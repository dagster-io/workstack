---
description: Create GitHub issue from persisted plan
---

# /erk:create-plan-issue-from-plan-file

⚠️ **DEPRECATED**: This command is deprecated. Use `/erk:save-context-enriched-plan` or `/erk:save-plan` instead, which create GitHub issues directly without requiring disk files.

This command remains functional for backward compatibility with existing plan files on disk.

## Goal

**Create a GitHub issue from an existing plan file on disk.**

This command detects plan files at the repository root, selects the most recent one, creates a GitHub issue with the plan content, and optionally links it to an existing worktree's `.impl/` folder.

**What this command does:**

- ✅ Auto-detect most recent `*-plan.md` file at repo root
- ✅ Extract title from plan front matter or first H1 heading
- ✅ Ensure `erk-plan` label exists (create if needed)
- ✅ Create GitHub issue with plan body as content
- ✅ Add label: `erk-plan`
- ✅ Save issue reference to `.impl/issue.json` (if worktree exists)
- ✅ Display issue URL

## What Happens

When you run this command, these steps occur:

1. **Verify Scope** - Confirm we're in a git repository with gh CLI available
2. **Detect Plan File** - Find and select most recent `*-plan.md` at repo root
3. **Parse Plan** - Extract title and body from markdown
4. **Ensure Label Exists** - Check for `erk-plan` label, create if missing
5. **Create Issue** - Use gh CLI to create issue with `erk-plan` label
6. **Link to Worktree** - If `.impl/` folder exists in current worktree, save issue reference
7. **Display Result** - Show issue number and URL

## Usage

```bash
/erk:create-planned-issue
```

**No arguments accepted** - This command automatically detects and uses the most recent plan file.

## Optional: Link Existing Issue

If you want to link an existing issue instead of creating a new one:

```bash
/erk:create-planned-issue --link 123
```

This will save the issue reference without creating a new issue. Use this when:

- Issue was created manually on GitHub
- Want to associate an existing issue with a worktree

## Prerequisites

- At least one `*-plan.md` file must exist at repository root
- Current working directory must be in a git repository
- `gh` CLI must be installed and authenticated
- Typically run after `/erk:save-context-enriched-plan`
- Can run before or after `/erk:create-wt-from-plan-file`

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Detection:**
✅ Plan file detected at repository root
✅ Most recent plan file selected (if multiple exist)
✅ Title extracted from front matter or H1 heading

**Label Pre-flight:**
✅ `erk-plan` label exists (created if missing)

**Issue Creation:**
✅ GitHub issue created with plan content
✅ Label added: `erk-plan`
✅ Issue URL displayed

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
- Create worktree: `/erk:create-wt-from-plan-file`
- Navigate to worktree: `erk checkout <branch>`
- Re-run: `/erk:create-planned-issue --link <issue-number>`

## Integration with Workflow

**Typical workflow:**

1. Create plan: `/erk:save-context-enriched-plan`
2. Create issue: `/erk:create-planned-issue` ← **YOU ARE HERE**
3. Create worktree: `/erk:create-wt-from-plan-file`
4. Navigate and implement: `erk checkout <branch> && claude --permission-mode acceptEdits "/erk:implement-plan"`

**Alternative workflow (create issue from within worktree):**

1. Create plan: `/erk:save-context-enriched-plan`
2. Create worktree: `/erk:create-wt-from-plan-file`
3. Navigate: `erk checkout <branch>`
4. Create issue: `/erk:create-planned-issue` ← Issue automatically linked to `.impl/` folder

---

## Agent Instructions

You are executing the `/erk:create-planned-issue` command. Follow these steps carefully:

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

Use the composite kit CLI command that handles the complete workflow from plan file:

- Reads plan file from disk
- Extracts title from plan
- Ensures erk-plan label exists
- Creates GitHub issue with plan body
- Returns structured JSON result

**Algorithm:**

1. Call the composite kit command with the plan file path:

   ```bash
   result=$(dot-agent kit-command erk create-plan-issue-from-plan-file "<path-to-plan-file>")

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
- Ensures erk-plan label exists (creates if needed)
- Creates issue with full plan as body
- Returns JSON: `{"success": true, "issue_number": 123, "issue_url": "..."}`

### Step 5: Display Issue URL

Show success message with issue information:

```
✅ GitHub issue created successfully!

Issue #<number>: <title>
URL: <issue-url>

You can now:
- View issue: gh issue view <number>
- Create worktree: /erk:create-wt-from-plan-file
```

### Step 6: Link Issue to Worktree (if .impl/ exists)

Check if current directory has a `.impl/` folder:

1. Check for `.impl/` directory:

   ```bash
   test -d .plan && echo "exists" || echo "not found"
   ```

2. If `.impl/` exists:
   - Use `ctx.issues.get_issue(repo_root, issue_number)` to fetch issue details
   - Import: `from erk.core.impl_folder import save_issue_reference`
   - Call: `save_issue_reference(Path.cwd() / ".impl", issue_number, issue_url)`
   - Display:

     ```
     📋 Issue linked to worktree

     Issue reference saved to .impl/issue.json

     The issue will be updated with progress during implementation.
     ```

3. If `.impl/` doesn't exist:
   - Continue silently (no action needed)

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

- **NO auto-implementation**: This command ONLY creates the GitHub issue
- **Graceful degradation**: Creating issue without linking is valid (can link later)
- **Idempotent linking**: Can run `--link` multiple times safely (overwrites `.impl/issue.json`)
- **Context usage**: Use `ctx.issues.create_issue()` for issue creation (injected via ErkContext)

### Error Handling

If any critical step fails:

1. Explain what went wrong
2. Show relevant command output
3. Suggest troubleshooting steps
4. Exit cleanly with error message
