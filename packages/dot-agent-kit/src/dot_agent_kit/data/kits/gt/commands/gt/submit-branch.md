---
description: Create git commit and submit current branch with Graphite
argument-hint: <description>
---

# Submit Branch

Automatically create a git commit with a helpful summary message and submit the current branch as a pull request.

## What This Command Does

1. **Commit outstanding changes**: Stage and commit any uncommitted changes with a temporary message
2. **Squash commits**: Run `gt squash` to combine all commits in the current branch
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

- Check uncommitted changes
- Commit if needed
- Run gt squash
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

### 1. Execute Pre-Analysis Phase

Run the kit CLI command to handle mechanical git operations:

```bash
dot-agent run gt submit-branch pre-analysis
```

**What this does:**

- Gets current branch and parent branch
- Checks for uncommitted changes
- If uncommitted: commits with "WIP: Prepare for submission"
- Runs `gt squash` to consolidate commits
- Returns JSON with branch info and status

**Parse the JSON output** to get:

- `branch_name`: Current branch name
- `parent_branch`: Parent branch name
- `had_uncommitted_changes`: Whether changes were committed
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
If the command fails (exit code 1), parse the error JSON:

- If error_type is "submit_failed" and message contains "updated remotely" or "Must sync":
  - Report that the branch has diverged from remote
  - Explain that user needs to manually resolve with `gt sync`
  - Exit the command
- For other errors, report the error message and exit

**Important notes:**

- The PR body should contain the full commit message (all sections: Summary, Files Changed, Key Changes, Critical Notes)
- Use proper escaping for the commit message when passing as command argument
- Branch divergence requires user decision - do not attempt automatic resolution

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
- **Error handling**: Parse JSON errors from kit commands and report appropriately
- **Branch divergence**: Let user manually resolve with `gt sync` - do not attempt automatic resolution

## Error Handling

### Branch Divergence

If `gt submit` fails with "Branch has been updated remotely" or "Must sync with remote":

1. **STOP immediately** - do not retry or attempt automatic resolution
2. Report to the user that the branch has diverged from remote
3. Show the error message from `gt submit`
4. Explain that the user needs to manually resolve with `gt sync` or other approach
5. Exit the command

**Rationale**: Branch divergence requires user decision about resolution strategy. The command should not make this decision automatically.

### Other Errors

If any other step fails:

- Report the specific command that failed
- Show the error message
- Ask the user how to proceed (don't retry automatically)

## Example Output

```
Running pre-analysis phase...
✓ Pre-analysis complete for branch: optimize-submit-branch
✓ Committed uncommitted changes and squashed commits

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
