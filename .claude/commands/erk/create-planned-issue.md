---
description: Create GitHub issue from persisted plan
---

# /erk:create-planned-issue

## Goal

**Create a GitHub issue from an existing plan file on disk.**

This command detects plan files at the repository root, selects the most recent one, creates a GitHub issue with the plan content, and optionally links it to an existing worktree's `.plan/` folder.

**What this command does:**

- ✅ Auto-detect most recent `*-plan.md` file at repo root
- ✅ Extract title from plan front matter or first H1 heading
- ✅ Ensure `erk-plan` label exists (create if needed)
- ✅ Create GitHub issue with plan body as content
- ✅ Add label: `erk-plan`
- ✅ Save issue reference to `.plan/issue.json` (if worktree exists)
- ✅ Display issue URL

## What Happens

When you run this command, these steps occur:

1. **Verify Scope** - Confirm we're in a git repository with gh CLI available
2. **Detect Plan File** - Find and select most recent `*-plan.md` at repo root
3. **Parse Plan** - Extract title and body from markdown
4. **Ensure Label Exists** - Check for `erk-plan` label, create if missing
5. **Create Issue** - Use gh CLI to create issue with `erk-plan` label
6. **Link to Worktree** - If `.plan/` folder exists in current worktree, save issue reference
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
- Typically run after `/erk:persist-plan`
- Can run before or after `/erk:create-planned-wt`

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
✅ If `.plan/` folder exists: issue reference saved to `.plan/issue.json`
✅ If no `.plan/` folder: issue created but not linked (can link later)

## Troubleshooting

### "No plan files found"

**Cause:** No `*-plan.md` files exist at repository root
**Solution:**

- Run `/erk:persist-plan` to create a plan first
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

**Cause:** No `.plan/` folder in current worktree
**Solution:**

- This is expected if you haven't created a worktree yet
- Create worktree: `/erk:create-planned-wt`
- Navigate to worktree: `erk checkout <branch>`
- Re-run: `/erk:create-planned-issue --link <issue-number>`

## Integration with Workflow

**Typical workflow:**

1. Create plan: `/erk:persist-plan`
2. Create issue: `/erk:create-planned-issue` ← **YOU ARE HERE**
3. Create worktree: `/erk:create-planned-wt`
4. Navigate and implement: `erk checkout <branch> && claude --permission-mode acceptEdits "/erk:implement-plan"`

**Alternative workflow (create issue from within worktree):**

1. Create plan: `/erk:persist-plan`
2. Create worktree: `/erk:create-planned-wt`
3. Navigate: `erk checkout <branch>`
4. Create issue: `/erk:create-planned-issue` ← Issue automatically linked to `.plan/` folder

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

Find the most recent `*-plan.md` file at repository root:

1. Get repository root:

   ```bash
   git rev-parse --show-toplevel
   ```

2. List plan files:

   ```bash
   find <repo-root> -maxdepth 1 -name "*-plan.md" -type f
   ```

3. If no files found:

   ```
   ❌ Error: No plan files found at repository root

   Run /erk:persist-plan to create a plan first.
   ```

   Exit with error.

4. If multiple files found: Select most recent by modification time
   ```bash
   ls -t <repo-root>/*-plan.md | head -1
   ```

### Step 4: Parse Plan File

Extract title and body from the selected plan file:

1. Read file contents using Read tool

2. Extract title (try in order):
   a. First, check for YAML front matter with `title:` field
   b. If no front matter, extract first H1 heading (line starting with `# `)
   c. If no H1, use filename without `-plan.md` suffix as title

3. Body is the full plan markdown content

### Step 5: Ensure Label Exists

Check if the `erk-plan` label exists, and create it if needed:

1. Check for label using gh CLI:

   ```bash
   gh label list --json name --jq '.[] | select(.name == "erk-plan") | .name'
   ```

2. If label doesn't exist (empty output), create it:

   ```bash
   gh label create "erk-plan" \
     --description "Implementation plan created by erk" \
     --color "0E8A16"
   ```

   Note: Color 0E8A16 is GitHub's default green color for planning/enhancement labels.

3. If label already exists: Continue silently (no output needed)

4. If label creation fails:

   ```
   ⚠️  Warning: Could not create erk-plan label

   Command output: <stderr>

   Continuing with issue creation...
   ```

   Continue to Step 6 (non-blocking warning - gh will still accept the label even if not in repo's label list)

### Step 6: Create GitHub Issue

Use gh CLI to create the issue:

1. Create issue with gh CLI:

   ```bash
   gh issue create \
     --title "<extracted-title>" \
     --body-file <path-to-plan-file> \
     --label "erk-plan" \
     --repo <owner>/<repo>
   ```

2. Parse issue number from output (gh returns URL like `https://github.com/owner/repo/issues/123`)

3. If gh command fails:

   ```
   ❌ Error: Failed to create GitHub issue

   Command output: <stderr>

   Troubleshooting:
   - Check network connectivity
   - Verify repository access: gh repo view
   - Check API rate limits: gh api rate_limit
   ```

   Exit with error.

### Step 7: Display Issue URL

Show success message with issue information:

```
✅ GitHub issue created successfully!

Issue #<number>: <title>
URL: <issue-url>

You can now:
- View issue: gh issue view <number>
- Create worktree: /erk:create-planned-wt
- Or if worktree exists: erk checkout <branch> && /erk:create-planned-issue --link <number>
```

### Step 8: Link Issue to Worktree (if .plan/ exists)

Check if current directory has a `.plan/` folder:

1. Check for `.plan/` directory:

   ```bash
   test -d .plan && echo "exists" || echo "not found"
   ```

2. If `.plan/` exists:
   - Use `ctx.issues.get_issue(repo_root, issue_number)` to fetch issue details
   - Import: `from erk.core.plan_folder import save_issue_reference`
   - Call: `save_issue_reference(Path.cwd() / ".plan", issue_number, issue_url)`
   - Display:

     ```
     📋 Issue linked to worktree

     Issue reference saved to .plan/issue.json

     The issue will be updated with progress during implementation.
     ```

3. If `.plan/` doesn't exist:
   - Display informational message:

     ```
     ℹ️  Issue created but not linked to a worktree

     To link this issue to a worktree:
     1. Create worktree: /erk:create-planned-wt
     2. Navigate: erk checkout <branch>
     3. Link issue: /erk:create-planned-issue --link <issue-number>
     ```

### Step 9: Handle --link Flag

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

3. Check for `.plan/` directory (same as Step 8)

4. If `.plan/` exists:
   - Save issue reference using `save_issue_reference()`
   - Display:

     ```
     ✅ Issue #<number> linked to worktree

     Issue: <title>
     URL: <url>

     Issue reference saved to .plan/issue.json
     ```

5. If `.plan/` doesn't exist:

   ```
   ❌ Error: No .plan/ folder found in current directory

   Navigate to a worktree with a plan:
   1. List worktrees: erk list
   2. Navigate: erk checkout <branch>
   3. Try again: /erk:create-planned-issue --link <issue-number>
   ```

   Exit with error.

### Important Notes

- **NO auto-implementation**: This command ONLY creates the GitHub issue
- **Graceful degradation**: Creating issue without linking is valid (can link later)
- **Idempotent linking**: Can run `--link` multiple times safely (overwrites `.plan/issue.json`)
- **Context usage**: Use `ctx.issues.create_issue()` for issue creation (injected via ErkContext)

### Error Handling

If any critical step fails:

1. Explain what went wrong
2. Show relevant command output
3. Suggest troubleshooting steps
4. Exit cleanly with error message
