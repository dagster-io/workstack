---
description: Create git commit and submit current branch with Graphite
argument-hint: <description>
---

# Submit Branch

Automatically create a git commit with a helpful summary message and submit the current branch as a pull request.

## What This Command Does

1. **Check for uncommitted changes**: Check working tree and commit any uncommitted changes (via Claude permissions system)
2. **Squash commits**: Run `gt squash` to combine all commits in the current branch (only if 2+ commits)
3. **Analyze and update message**: Use git-diff-summarizer agent to analyze all changes and create a comprehensive commit message
4. **Submit branch**: Run `gt submit --publish` to create/update PR for the current branch
5. **Update PR metadata**: If PR already exists, sync PR title and body with the new commit message
6. **Report results**: Show the submitted PRs and their URLs

## Usage

```bash
# With description argument
/submit-branch "Add user authentication feature"

# Without argument (will analyze changes automatically)
/submit-branch
```

## Two-Phase Workflow

This command uses a two-phase kit CLI command to optimize execution:

**Phase 1 (pre-analysis)**: Python kit command handles mechanical git/gt operations

- Get current branch and parent branch
- Count commits in branch
- Run gt squash (only if 2+ commits)
- Return branch info as JSON

**Phase 2 (post-analysis)**: Python kit command handles submission and PR metadata

- Amend commit with AI-generated message
- Submit branch with gt
- Update PR metadata if exists
- Return PR info as JSON

**Between phases**: Claude performs AI-driven analysis with git-diff-summarizer agent

This separation ensures:

- Speed: Python handles ~8 git/gh/gt operations faster than Claude
- Token efficiency: Mechanical operations don't pollute context
- Testability: Python logic can be unit tested
- Reusability: Helper functions available for other commands

## Implementation Steps

When this command is invoked:

### 0. Check for Uncommitted Changes and Commit

**Before running pre-analysis**, check if there are uncommitted changes and commit them:

```bash
git status --porcelain
```

**If output is non-empty** (uncommitted changes exist):

```bash
git add . && git commit -m "WIP: Prepare for submission"
```

**Important**: This step runs through Claude's Bash tool so it goes through the permissions system. The user will see what files are being committed.

**If no uncommitted changes**, proceed directly to Step 1.

### 1. Execute Pre-Analysis Phase

Run the kit CLI command to handle mechanical git operations:

```bash
dot-agent run gt submit-branch pre-analysis
```

**What this does:**

- Gets current branch and parent branch
- Counts commits in the branch (compared to parent)
- Runs `gt squash` to consolidate commits (only if 2+ commits exist)
- Returns JSON with branch info and status

**Parse the JSON output** to get:

- `branch_name`: Current branch name
- `parent_branch`: Parent branch name
- `commit_count`: Number of commits in branch
- `squashed`: Whether squashing occurred (true if 2+ commits, false if 1 commit)
- `message`: Human-readable status message

**Error handling:**
If the command fails (exit code 1), parse the error JSON and report to user. Do not continue.

### 2. Analyze Changes and Craft Commit Message

Use the git-diff-summarizer agent to analyze all changes and create a comprehensive commit message:

**Step 2a: Invoke git-diff-summarizer**

```
Task(
    subagent_type="git-diff-summarizer",
    prompt="""Analyze all changes in this branch (compared to parent branch) and provide a COMPRESSED summary. Be concise but informative:

FORMAT REQUIREMENTS:
- Summary: ONE paragraph (2-3 sentences max)
- Files Changed: Group similar files (e.g., "Modified 5 test files" not listing each)
- Key Changes: Maximum 5 bullet points, focus on WHAT changed and WHY it matters
- Critical Notes: Only if there are breaking changes, security concerns, or important warnings (1-2 bullets max)

COMPRESSION RULES:
- No redundant information (don't repeat file names in multiple sections)
- Combine related changes into single points
- Omit obvious details (e.g., "Updated tests" is enough, not "Added test cases for new functionality")
- Use active voice and direct language
- Skip the Observations section unless there's something critical"""
)
```

**Step 2b: Extract Analysis from Agent Output**

The agent returns a compressed analysis with these sections:

- Summary (2-3 sentence overview)
- Files Changed (grouped concisely)
- Key Changes (max 5 bullets, focusing on what and why)
- Critical Notes (only if necessary - breaking changes, security issues)

**Step 2c: Craft Brief Top Summary**

Create a concise 2-4 sentence summary paragraph that:

- States what the branch does (feature/fix/refactor)
- Highlights the key changes briefly
- Uses clear, professional language

**Step 2d: Construct Commit Message**

Use the compressed output directly from the git-diff-summarizer agent:

```
[Brief summary paragraph crafted from agent's summary]

[Compressed analysis from git-diff-summarizer]
```

The message should be concise (typically 15-30 lines total) with the essential information preserved.

### 3. Execute Post-Analysis Phase

Run the kit CLI command to handle submission and PR metadata:

**Step 3a: Extract commit message components**

Parse the commit message created in Step 2:

- **Title**: First line of the commit message (the brief summary)
- **Body**: Everything after the first line (full commit message including all sections)

**Step 3b: Call post-analysis command**

```bash
dot-agent run gt submit-branch post-analysis \
  --commit-message "[Full commit message from Step 2]" \
  --pr-title "[First line of commit message]" \
  --pr-body "[Full commit message body - everything after first line]"
```

**What this does:**

- Amends the commit with the AI-generated commit message
- Runs `gt submit --publish --no-interactive --restack`
- Checks if PR exists
- If PR exists: updates title and body with `gh pr edit`
- Returns JSON with PR number, URL, and status

**Parse the JSON output** to get:

- `pr_number`: PR number (may be null)
- `pr_url`: PR URL
- `branch_name`: Branch name
- `message`: Human-readable status message

**Error handling:**
If the command fails (exit code 1), parse the error JSON. The error will include:
- `error_type`: Category of error (submit_merged_parent, submit_diverged, submit_failed, amend_failed, pr_update_failed)
- `message`: Human-readable description of what failed
- `details`: Additional context including stdout, stderr, branch_name, and other relevant information

Use this information to provide helpful, context-aware guidance to the user about what went wrong and how to resolve it. Consider the error type, the actual command output, and the user's situation to determine the best course of action.

**Important notes:**

- The PR body should contain the full commit message (all sections: Summary, Files Changed, Key Changes, Critical Notes)
- Use proper escaping for the commit message when passing as command argument
- Do not attempt automatic resolution of errors - provide user with information and let them decide

### 4. Show Results

After submission, provide a clear summary using bullet list formatting:

```
## ✅ Branch Submitted Successfully

- **PR Created**: #235
- **URL**: https://app.graphite.dev/github/pr/dagster-io/workstack/235
- **Branch**: merge-artifact-check-commands
```

**Formatting requirements:**

- Use bullet list (`-`) for each item
- Bold the labels (**PR Created**, **URL**, **Branch**)
- Do NOT use two-space line breaks (they are fragile in terminal rendering)

## Important Notes

- **Two-phase workflow**: Pre-analysis (kit CLI) → AI analysis (Claude) → Post-analysis (kit CLI)
- **ALWAYS use git-diff-summarizer agent** for analyzing changes and creating commit messages
- **NO Claude footer**: Do not add any attribution or generated-by footer to the final commit message
- **Error handling**: Parse JSON errors from kit commands and provide context-aware guidance to the user
- **No automatic fixes**: Let user manually resolve errors - provide information and guidance, don't retry automatically

## Error Handling

When any step fails, the kit CLI command will return a JSON error with:
- `error_type`: Categorizes the failure (e.g., submit_merged_parent, submit_diverged, submit_failed)
- `message`: Human-readable description
- `details`: Command output (stdout/stderr) and other context

**Your role:**
1. Parse the error JSON to understand what failed
2. Examine the error type and command output (stdout/stderr in details)
3. Provide clear, helpful guidance based on the specific situation
4. Do not retry automatically - let the user decide how to proceed

**Rationale**: Errors often require user decisions about resolution strategy. Claude should provide intelligent, context-aware guidance rather than following rigid rules for each error type.

### Specific Error Type Guidance

#### `submit_merged_parent` Error

When parent branches have been merged but those commits aren't in the local `main` yet:

```
**Issue:** Your parent branches were merged, but those commits aren't in your local `main` yet. Graphite won't let you submit until the stack is clean.

**Solution:**

```bash
# Sync main and restack everything
gt sync -f

# If you're using workstack
workstack sync -f
```

This will:
1. Pull latest `main` with the merged commits
2. Rebase your entire stack onto the updated `main`
3. Clean up any merged branches

**Alternative** (if you just want to update this worktree):
```bash
# Just update main in this worktree
git checkout main && git pull origin main
gt repo sync
```

The `-f` flag forces the sync even if there are conflicts or merged branches.
```

## Example Output

```
Checking for uncommitted changes...
✓ Committed uncommitted changes

Running pre-analysis phase...
✓ Pre-analysis complete for branch: optimize-submit-branch
✓ Squashed 3 commits into 1

Analyzing changes with git-diff-summarizer...
✓ Analysis complete with detailed breakdown

Crafting commit message...
✓ Commit message crafted

Running post-analysis phase...
✓ Amended commit with AI-generated message
✓ Submitted branch successfully
✓ Updated PR #235 title and body to match commit message

## ✅ Branch Submitted Successfully

- **PR Updated**: #235
- **URL**: https://app.graphite.dev/github/pr/dagster-io/workstack/235
- **Branch**: optimize-submit-branch
```

### Example Commit Message Structure (Compressed Format)

```
Add tree visualization to gt branches command

Introduces hierarchical tree display for Graphite branch stacks, improving visualization of branch relationships and stack navigation.

## Summary

Replaces flat list format with ASCII tree visualization (├──, └──) for gt branches command, making parent-child relationships clear at a glance.

## Files Changed

- Modified: 2 command files, 1 formatting utility, 3 test files

## Key Changes

- Added `--tree` flag for hierarchical stack display
- Created reusable tree formatting module for consistent rendering
- Implemented LBYL pattern for safe branch traversal
- Added comprehensive test coverage including edge cases
- Foundation for unified visualization across other gt commands

## Critical Notes

- Performance untested with 100+ branch stacks - may need optimization for large repositories
```
