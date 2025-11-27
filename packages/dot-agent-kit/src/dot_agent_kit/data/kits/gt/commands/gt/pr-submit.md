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

Orchestrates the complete submit-branch workflow:

1. **Pre-analysis** - Check for uncommitted changes, squash commits, get branch info
2. **Diff analysis** - Get diff context for commit message generation
3. **Generate commit message** - Use AI to analyze diff and generate structured commit message
4. **Post-analysis** - Amend commit, submit branch, update PR metadata
5. **Report results** - Display summary and PR URL

## Implementation

Execute these steps in order:

### Step 1: Run Pre-Analysis

```bash
dot-agent run gt submit-pr pre-analysis
```

Parse the JSON output. If `success` is `false`, display the error and stop.

### Step 2: Get Diff Context

```bash
dot-agent run gt submit-pr get-diff-context
```

Parse the JSON output to get:
- `current_branch`: Current branch name
- `parent_branch`: Parent branch name
- `diff`: Full diff output

### Step 3: Generate Commit Message

Analyze the diff and generate a commit message following this format:

```
[First line: PR title - imperative mood, max 72 chars]

## Summary
[2-3 sentence high-level overview]

## Files Changed
### Added (X files)
- `path/file.py` - Brief purpose

### Modified (Y files)
- `path/file.py` - What changed

### Deleted (Z files)
- `path/file.py` - Why removed

## Key Changes
[3-5 bullet points at component level]

## Critical Notes
[Only if breaking changes or security concerns - otherwise omit]
```

### Step 4: Run Post-Analysis

Pass the commit message to post-analysis:

```bash
dot-agent run gt submit-pr post-analysis --commit-message "$(cat <<'EOF'
<commit message here>
EOF
)"
```

Parse the JSON output for PR info.

### Step 5: Display Results

Show a summary:

```
## Branch Submission Complete

### What Was Done

✓ Created commit with AI-generated message
✓ Submitted branch to Graphite
✓ Updated PR #<number>: <title>

### View PR

<graphite_url>
```

## Error Handling

If any step fails, parse the error JSON and provide clear guidance. Common errors:

- `pr_has_conflicts` - Branch has merge conflicts
- `submit_merged_parent` - Parent branch was merged, need to sync
- `squash_conflict` - Conflicts during squash

**NEVER** attempt to resolve conflicts automatically - display the error and stop.
