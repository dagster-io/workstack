---
description: Create git commit and submit current branch with Graphite
argument-hint: <description>
---

# Submit Branch

Automatically create a git commit with a helpful summary message and submit the current branch as a pull request.

This command uses an optimized Python script that consolidates git operations to minimize agent invocations and improve performance by 60-70%.

## What This Command Does

1. **Prepare branch**: Stage and commit any uncommitted changes, then squash all commits (via Python script)
2. **Analyze changes**: Use git-diff-summarizer agent to analyze all changes and create a comprehensive commit message
3. **Amend commit**: Update the squashed commit with the generated message (via Python script)
4. **Submit branch**: Run `gt submit --publish` to create/update PR (via Python script)
5. **Update PR metadata**: If PR already exists, sync PR title and body with the commit message (via Python script)
6. **Report results**: Show the submitted PRs and their URLs

## Usage

```bash
# With description argument
/submit-branch "Add user authentication feature"

# Without argument (will analyze changes automatically)
/submit-branch
```

## Performance

This optimized implementation reduces agent invocations from 3 to 1:

- **Before**: gt-runner (squash) + gt-runner (submit) + git-diff-summarizer = ~15-20 seconds
- **After**: Python script + git-diff-summarizer = ~5-7 seconds
- **Improvement**: 60-70% faster execution

## Implementation Steps

When this command is invoked:

### 1. Prepare Branch (Python Script)

Run the Python script to prepare the branch for submission:

```bash
uv run packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/skills/gt-graphite/scripts/submit_branch.py prepare
```

This script:

- Checks for uncommitted changes and commits them with "WIP: Prepare for submission"
- Squashes all commits in the current branch into a single commit
- Returns branch name and parent branch info

The script returns JSON with the result:

```json
{
  "success": true,
  "status": "prepared",
  "branch": "feature-branch",
  "parent": "main",
  "message": "Prepared branch feature-branch for submission (parent: main)"
}
```

If this step fails, report the error and exit.

### 2. Analyze Changes (git-diff-summarizer Agent)

Use the git-diff-summarizer agent to analyze all changes and create a comprehensive commit message:

```
Task(
    subagent_type="git-diff-summarizer",
    description="Analyze branch changes",
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

The agent returns a compressed analysis with these sections:

- Summary (2-3 sentence overview)
- Files Changed (grouped concisely)
- Key Changes (max 5 bullets, focusing on what and why)
- Critical Notes (only if necessary - breaking changes, security issues)

### 3. Craft Commit Message

Create a comprehensive commit message by:

**3a. Craft Brief Top Summary**

Create a concise 2-4 sentence summary paragraph that:

- States what the branch does (feature/fix/refactor)
- Highlights the key changes briefly
- Uses clear, professional language

**3b. Construct Full Commit Message**

Use the compressed output directly from the git-diff-summarizer agent:

```
[Brief summary paragraph crafted from agent's summary]

[Compressed analysis from git-diff-summarizer]
```

The message should be concise (typically 15-30 lines total) with the essential information preserved.

**Important:**

- **DO NOT include any Claude Code footer or co-authorship attribution**
- Preserve all markdown formatting from the agent output
- Ensure proper line breaks between sections
- The brief summary at top should be manually crafted, not copied from agent

### 4. Amend Commit (Python Script)

Update the squashed commit with the generated message:

```bash
uv run packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/skills/gt-graphite/scripts/submit_branch.py amend "<full commit message>"
```

The script uses `git commit --amend` to update the commit message.

If this step fails, report the error and exit.

### 5. Submit Branch (Python Script)

Submit the current branch as a PR:

```bash
uv run packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/skills/gt-graphite/scripts/submit_branch.py submit
```

This script runs `gt submit --publish --no-interactive --restack` with flags:

- `--publish`: Publish any draft PRs
- `--no-interactive`: Skip interactive prompts and automatically sync commit message to PR description
- `--restack`: Restack branches before submitting

**If `gt submit` fails with "updated remotely" or "Must sync" error:**

The script returns an error with type "branch_diverged". Report to the user:

1. **STOP immediately** - do not retry or attempt to resolve automatically
2. Report that the branch has diverged from remote
3. Show the error message
4. Exit and let the user manually resolve with `gt sync` or force push

**Rationale**: Branch divergence requires user decision about resolution strategy.

If this step fails, report the error and exit.

### 6. Update PR Metadata (Python Script)

Update the PR title and body to match the commit message:

```bash
uv run packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/skills/gt-graphite/scripts/submit_branch.py update-pr "<full commit message>"
```

This script:

- Checks if a PR exists for the current branch using `gh pr view`
- If a PR exists, extracts title (first line) and body (rest) from commit message
- Updates PR with `gh pr edit --title "<title>" --body "<body>"`
- If no PR exists, skips the update (PR will be created by gt submit)
- If update fails, reports error but doesn't fail the command

If this step fails, report the error but continue (this is not a critical failure).

### 7. Show Results

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

- **Performance optimized**: This command uses a Python script to consolidate git operations, reducing execution time by 60-70%
- **Single agent invocation**: Only git-diff-summarizer agent is invoked; all other operations run via Python script
- **ALWAYS use git-diff-summarizer agent** for analyzing changes and creating commit messages
- **NO Claude footer**: Do not add any attribution or generated-by footer to the final commit message
- **Script location**: The Python script is at `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/skills/gt-graphite/scripts/submit_branch.py`
- If there are no changes to commit at the start, the prepare step will handle it gracefully

## Error Handling

All errors are handled by the Python script with structured JSON responses. Parse the JSON and report errors clearly.

### Branch Divergence

The script detects branch divergence and returns:

```json
{
  "success": false,
  "error_type": "branch_diverged",
  "message": "Branch has been updated remotely and diverged from local.\n\nPlease resolve with: gt sync\nThen try again.",
  "details": { "current_branch": "feature-branch" }
}
```

When this occurs:

1. **STOP immediately** - do not retry or attempt automatic resolution
2. Report to the user that the branch has diverged from remote
3. Show the error message
4. Explain that the user needs to manually resolve with `gt sync`
5. Exit the command

**Rationale**: Branch divergence requires user decision about resolution strategy.

### Other Errors

The script returns structured error JSON for all failure cases:

- `no_changes`: No uncommitted changes to commit
- `squash_failed`: Failed to squash commits
- `amend_failed`: Failed to amend commit message
- `submit_failed`: Failed to submit branch
- `pr_update_failed`: Failed to update PR metadata

Parse the JSON, report the error message and details, and exit (except pr_update_failed which is non-critical).

## Example Output

```
Preparing branch...
✓ Committed uncommitted changes
✓ Squashed 3 commits into 1
✓ Branch prepared: feature-branch (parent: main)

Analyzing changes with git-diff-summarizer...
✓ Analysis complete with detailed breakdown

Crafting commit message...
✓ Created comprehensive commit message with analysis

Amending commit...
✓ Updated commit message

Submitting branch...
✓ Branch submitted

Updating PR metadata...
✓ PR #123 title and body updated to match commit message

## ✅ Branch Submitted Successfully

- **PR Updated**: #123
- **URL**: https://github.com/owner/repo/pull/123
- **Branch**: feature-branch
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
