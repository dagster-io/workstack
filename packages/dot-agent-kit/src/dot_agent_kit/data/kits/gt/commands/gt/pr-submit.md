---
description: Create git commit and submit current branch with Graphite (squashes commits and rebases stack)
argument-hint: <description>
---

# Submit PR

Automatically create a git commit with a helpful summary message and submit the current branch as a pull request.

**Note:** This command squashes commits and rebases the stack. If you prefer a simpler workflow that preserves your commit history, use `/git:pr-push` instead.

## Usage

```bash
# Invoke the command (description argument is optional but recommended)
/gt:pr-submit "Add user authentication feature"

# Without argument (will analyze changes automatically)
/gt:pr-submit
```

## What This Command Does

Executes the complete submit-branch workflow in 3 phases:

1. **Preflight** (Python CLI): Auth checks, squash commits, submit to Graphite, get PR diff
2. **AI Summarization** (Task tool): Generate PR title and body using commit-message-generator subagent
3. **Finalize** (Python CLI): Update PR metadata with AI-generated content

## Implementation

### Step 1: Run Preflight Phase

Execute the preflight command to do all deterministic work:

```bash
dot-agent run gt pr-submit preflight
```

This returns JSON with:

- `success`: boolean
- `pr_number`: int
- `pr_url`: string
- `graphite_url`: string
- `branch_name`: string
- `diff_file`: path to temp diff file
- `repo_root`: repository root path
- `current_branch`: current branch name
- `parent_branch`: parent branch name
- `issue_number`: int or null
- `message`: status message

If `success` is `false`, display the error and stop.

### Step 2: Generate PR Description via AI

Use the Task tool to delegate to the commit-message-generator agent:

```
Task(
    subagent_type="commit-message-generator",
    description="Generate commit message from diff",
    prompt="Analyze the git diff and generate a commit message.

Diff file: {diff_file}
Repository root: {repo_root}
Current branch: {current_branch}
Parent branch: {parent_branch}

Use the Read tool to load the diff file."
)
```

Parse the agent output:

- First line = PR title
- Remaining lines = PR body
- Look for marker: `<!-- erk-generated commit message -->`
- Strip the marker before using the content

### Step 3: Run Finalize Phase

Execute the finalize command to update PR metadata:

```bash
dot-agent run gt pr-submit finalize \
    --pr-number {pr_number} \
    --pr-title "{pr_title}" \
    --pr-body "{pr_body}" \
    --diff-file "{diff_file}"
```

### Step 4: Report Results

Display:

- PR URL: `{pr_url}`
- Graphite URL: `{graphite_url}`
- Success message

## Error Handling

### Preflight Errors

- `gt_not_authenticated` / `gh_not_authenticated`: Auth issues
- `no_branch` / `no_parent` / `no_commits`: Branch state issues
- `squash_conflict` / `pr_has_conflicts`: Merge conflicts
- `submit_failed` / `submit_timeout`: Submission issues

### AI Errors (handled in this command)

- Invalid output (missing marker): Fall back to branch name as title
- Task tool failure: Report error and stop

### Finalize Errors

- `pr_update_failed`: Non-fatal, PR already submitted

## Backwards Compatibility

The existing `orchestrate` command is preserved for backwards compatibility:

```bash
dot-agent run gt pr-submit orchestrate
```

This still works but has a 30+ second startup delay due to subprocess-based AI invocation.
