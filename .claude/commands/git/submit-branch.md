---
description: Create git commit and submit branch as PR using git + GitHub CLI
argument-hint: <description>
---

# Submit Branch (Git Only)

Automatically create a git commit with a helpful summary message and submit the current branch as a pull request using standard git + GitHub CLI (no Graphite required).

## Usage

```bash
# Invoke the command (description argument is optional but recommended)
/git:submit-branch "Add user authentication feature"

# Without argument (will analyze changes automatically)
/git:submit-branch
```

## What This Command Does

Delegates the complete git-only submit-branch workflow to the `git-branch-submitter` agent, which handles:

1. Check for uncommitted changes and stage/commit them if needed
2. Analyze git diff to generate meaningful commit message
3. Create commit with AI-generated message
4. Push to origin with upstream tracking
5. Create GitHub PR
6. Report results with PR URL

## Key Differences from /gt:submit-branch

- ✅ Uses standard `git push` instead of `gt submit`
- ✅ Uses `gh pr create` instead of Graphite's PR submission
- ✅ No stack operations (no restack, no stack metadata updates)
- ✅ Simpler workflow: git → push → PR (no Graphite layer)
- ✅ Works in any git repository (not just Graphite-enabled repos)

## Prerequisites

- Git repository with remote configured
- GitHub CLI (`gh`) installed and authenticated
- Run `gh auth status` to verify authentication
- Run `gh auth login` if not authenticated

## Implementation

Execute the git-only submit-branch workflow with the following steps:

### Step 1: Verify Prerequisites

Check GitHub CLI authentication and get current git state:

```bash
# Check GitHub CLI authentication (show status for verification)
gh auth status

# Get current branch name
current_branch=$(git branch --show-current)

# Check for uncommitted changes
has_changes=$(git status --porcelain)
```

If `gh auth status` fails, report error and tell user to run `gh auth login`.

### Step 2: Stage Changes (if needed)

If `has_changes` is non-empty, stage all changes:

```bash
git add .
```

### Step 3: Analyze Staged Diff

Get the staged diff and analyze it to generate a commit message:

```bash
# Get repository root for relative paths
repo_root=$(git rev-parse --show-toplevel)

# Get staged diff for analysis
git diff --staged
```

**Analyze the diff** following these principles:

- **Be concise and strategic** - focus on significant changes
- **Use component-level descriptions** - reference modules/components, not individual functions
- **Highlight breaking changes prominently**
- **Note test coverage patterns**
- **Use relative paths from repository root**
- **Keep "Key Changes" to 3-5 major items**
- **Group related changes together**

**Structure your commit message:**

```
[Brief 2-4 sentence summary of what the branch does]

## Summary
[2-3 sentence high-level overview]

## Files Changed

### Added (X files)
- `path/to/file` - Brief purpose

### Modified (Y files)
- `path/to/file` - What area changed

### Deleted (Z files)
- `path/to/file` - Why removed

## Key Changes
- [3-5 high-level component/architectural changes]

## Critical Notes
[Only if there are breaking changes or important warnings - 1-2 bullets max]
```

**Important:**
- NO Claude footer or attribution
- Use relative paths from repository root
- Avoid function-level details unless critical
- Maximum 5 key changes

### Step 4: Create Commit

Create the commit with your AI-generated message using heredoc:

```bash
git commit -m "$(cat <<'COMMIT_MSG'
[Your generated commit message here]
COMMIT_MSG
)"
```

### Step 5: Push to Remote

Push the branch to origin with upstream tracking:

```bash
git push -u origin "$(git branch --show-current)"
```

### Step 6: Create GitHub PR

Extract PR title (first line) and body (remaining lines) from commit message, then create PR:

```bash
# Get the commit message
commit_msg=$(git log -1 --pretty=%B)

# Extract first line as title
pr_title=$(echo "$commit_msg" | head -n 1)

# Extract remaining lines as body (skip empty first line after title)
pr_body=$(echo "$commit_msg" | tail -n +2)

# Create PR using GitHub CLI
gh pr create --title "$pr_title" --body "$pr_body"
```

### Step 7: Report Results

Display a clear summary:

```
## Branch Submission Complete

### What Was Done

✓ Staged all uncommitted changes
✓ Created commit with AI-generated message
✓ Pushed branch to origin with upstream tracking
✓ Created GitHub PR

### View PR

[PR URL from gh pr create output]
```

**CRITICAL**: The PR URL MUST be the absolute last line of your output. Do not add any text after it.

## Error Handling

When errors occur, provide clear guidance:

**GitHub CLI not authenticated:**
```
❌ GitHub CLI is not authenticated

To use this command, authenticate with GitHub:
    gh auth login
```

**Nothing to commit:**
```
❌ No changes to commit

Your working directory is clean. Make some changes first.
```

**Push failed (diverged branches):**
```
❌ Push failed: branch has diverged

Option 1: Pull and merge
    git pull origin [branch]

Option 2: Force push (⚠️ overwrites remote)
    git push -f origin [branch]
```

**PR already exists:**
```
❌ PR already exists for this branch

To update the existing PR:
    gh pr edit [pr-number] --title "..." --body "..."

Or view it:
    gh pr view
```
