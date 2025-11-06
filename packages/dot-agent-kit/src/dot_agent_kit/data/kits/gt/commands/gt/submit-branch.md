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

## Graphite Command Execution

**ALWAYS use the `gt-runner` agent for ALL gt commands in this workflow:**

```
Task(
    subagent_type="gt-runner",
    description="[Short description]",
    prompt="Execute: gt [command]"
)
```

This ensures:

- Consistent execution and error handling
- Proper output parsing without polluting context
- Cost-optimized execution with Haiku model

## Implementation Steps

When this command is invoked:

### 1. Commit Outstanding Changes

Check for uncommitted changes and commit them:

```bash
git status
```

If there are uncommitted changes:

```bash
git add .
git commit -m "WIP: Prepare for submission"
```

### 2. Squash All Commits

Combine all commits in the current branch into a single commit using gt-runner:

```
Task(subagent_type="gt-runner", description="Squash commits", prompt="Execute: gt squash")
```

This creates a single commit containing all changes from the branch.

### 3. Analyze Changes and Update Commit Message

Use the git-diff-summarizer agent to analyze all changes and create a comprehensive commit message:

**Step 3a: Invoke git-diff-summarizer**

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

**Step 3b: Extract Analysis from Agent Output**

The agent returns a compressed analysis with these sections:

- Summary (2-3 sentence overview)
- Files Changed (grouped concisely)
- Key Changes (max 5 bullets, focusing on what and why)
- Critical Notes (only if necessary - breaking changes, security issues)

**Step 3c: Craft Brief Top Summary**

Create a concise 2-4 sentence summary paragraph that:

- States what the branch does (feature/fix/refactor)
- Highlights the key changes briefly
- Uses clear, professional language

**Step 3d: Construct Commit Message**

Use the compressed output directly from the git-diff-summarizer agent:

```
[Brief summary paragraph crafted from agent's summary]

[Compressed analysis from git-diff-summarizer]
```

The message should be concise (typically 15-30 lines total) with the essential information preserved.

**Step 3e: Amend Commit**

Update the squashed commit using a HEREDOC to preserve formatting:

```bash
git commit --amend -m "$(cat <<'EOF'
[Brief summary paragraph]

## Summary
[Agent's compressed summary]

## Files Changed
[Agent's grouped file changes]

## Key Changes
[Agent's 3-5 key bullet points]

## Critical Notes
[Only if provided by agent - breaking changes or warnings]
EOF
)"
```

**Important:**

- **DO NOT include any Claude Code footer or co-authorship attribution**
- Preserve all markdown formatting from the agent output
- Ensure proper line breaks between sections
- The brief summary at top should be manually crafted, not copied from agent

### 4. Submit Branch

Submit the current branch as a PR using gt-runner:

```
Task(subagent_type="gt-runner", description="Submit branch", prompt="Execute: gt submit --publish --no-interactive --restack")
```

Flags explained:

- `--publish`: Publish any draft PRs
- `--no-interactive`: Skip interactive prompts and automatically sync commit message to PR description
- `--restack`: Restack branches before submitting. If there are conflicts, output the branch names that could not be restacked

**If `gt submit` fails with "updated remotely" or "Must sync" error:**

1. **STOP immediately** - do not retry or attempt to resolve automatically
2. Report to the user that the branch has diverged from remote
3. Show the error message from `gt submit`
4. Exit the command and let the user manually resolve the divergence with `gt sync` or force push

**Rationale**: Branch divergence requires user decision about how to resolve (sync, force push, or manual merge). The command should not make this decision automatically

### 5. Update PR Body and Title (If PR Already Exists)

After `gt submit` completes, check if a PR already exists and update its body and title to match the new commit message:

**Step 5a: Check if PR exists for current branch**

```bash
gh pr view --json number,title,url
```

If the command succeeds (exit code 0), a PR exists for this branch.

**Step 5b: Extract title and body from commit message**

Parse the commit message created in Step 3:

- **Title**: First line of the commit message (the brief summary)
- **Body**: Everything after the first line (the compressed analysis - same content as commit message)

**Step 5c: Update PR title and body**

Use the `gh` CLI to update the PR:

```bash
gh pr edit --title "$(cat <<'EOF'
[First line of commit message]
EOF
)" --body "$(cat <<'EOF'
[Everything after first line of commit message]
EOF
)"
```

**Important:**

- Use HEREDOC to preserve formatting in both title and body
- The PR body should include the compressed analysis (same as commit message body)
- If `gh pr view` fails (no PR exists), skip this step - the PR will be created by `gt submit`
- If `gh pr edit` fails, report the error but don't fail the entire command

### 6. Show Results

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

- **ALWAYS use git-diff-summarizer agent** for analyzing changes and creating commit messages
- **Commit early**: Stage and commit all changes before squashing
- **Squash before analyzing**: Run `gt squash` before using git-diff-summarizer so it analyzes the complete branch changes
- **NO Claude footer**: Do not add any attribution or generated-by footer to the final commit message
- If there are no changes to commit at the start, report to the user and exit

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
Checking for uncommitted changes...
✓ Found changes in 3 files
✓ Committed as "WIP: Prepare for submission"

Squashing commits...
✓ 3 commits squashed into 1

Analyzing changes with git-diff-summarizer...
✓ Analysis complete with detailed breakdown
✓ Crafting brief summary
✓ Updating commit message with full analysis

Submitting branch...
✓ Branch submitted

Updating PR metadata...
✓ PR #123 title and body updated to match commit message

## ✅ Branch Submitted Successfully

- **PR Updated**: #123
- **URL**: https://github.com/owner/repo/pull/123
- **Branch**: gt-tree-format
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
