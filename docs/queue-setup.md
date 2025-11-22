# Setting Up Erk Queue

This guide covers enabling GitHub Actions workflows to create pull requests for the erk implementation queue.

## Overview

The erk queue system allows GitHub Actions workflows to automatically create and manage pull requests. This requires enabling specific permissions in your GitHub repository.

## Prerequisites

- Repository admin access
- `gh` CLI installed and authenticated

## Quick Setup

### 1. Check Current Permissions

```bash
erk admin github-pr-setting
```

This displays the current state of the GitHub Actions PR creation permission.

### 2. Enable PR Creation

```bash
erk admin github-pr-setting --enable
```

This enables GitHub Actions workflows in your repository to create and update pull requests.

### 3. Verify Setup

Run the check command again to verify:

```bash
erk admin github-pr-setting
```

You should see "Current status: Enabled"

## What This Does

When you enable queue permissions, your repository's GitHub Actions workflows gain the ability to:

- Create pull requests
- Update existing pull requests
- Approve pull requests (if configured)

This is required for automated implementation workflows that create PRs from queued issues.

## Security Note

This permission applies to **all** GitHub Actions workflows in your repository. Review your workflows before enabling.

## Using the Queue System

Once queue permissions are enabled, you can queue issues for automatic implementation using labels.

### Enqueuing Existing Issues

If you have an existing GitHub issue with a plan, you can enqueue it for automatic implementation:

**CLI command:**

```bash
erk plan-issue enqueue <issue-number>
```

**Slash command (in Claude Code):**

```
/erk:enqueue-plan-issue <issue-number>
```

**What happens:**

1. The `erk-queue` label is added to the issue
2. GitHub Actions workflow is triggered automatically
3. Workflow creates a branch, implements the plan, and opens a PR

**Examples:**

```bash
# Enqueue by issue number
erk plan-issue enqueue 42

# Or using slash command
/erk:enqueue-plan-issue 42

# Also accepts GitHub URLs
/erk:enqueue-plan-issue https://github.com/owner/repo/issues/42
```

### Creating Queued Issues

You can also create a new issue with the `erk-queue` label directly:

**Slash command (in Claude Code):**

```
/erk:create-queued-plan
```

This creates a GitHub issue from an existing plan file at the repository root and immediately queues it for implementation.

### Manual vs Automatic Workflow

**Manual workflow (erk-plan label):**

1. Create issue: `/erk:create-planned-issue`
2. Review and edit issue on GitHub
3. Implement manually: Create worktree, checkout, implement

**Automatic workflow (erk-queue label):**

1. Create queued issue: `/erk:create-queued-plan`
2. OR enqueue existing: `/erk:enqueue-plan-issue <number>`
3. Wait for GitHub Actions to automatically implement and create PR

**Converting manual to automatic:**

If you started with a manual workflow but want automatic implementation:

```bash
erk plan-issue enqueue <issue-number>
```

This adds the `erk-queue` label while preserving the existing `erk-plan` label.

### Monitoring Queue Progress

After enqueuing an issue, monitor progress:

```bash
# View issue status
gh issue view <number>

# Watch workflow runs
gh run list

# Check Actions tab
gh run list --workflow=dispatch-erk-queue.yml
```

## Disabling Queue Permissions

If you need to disable PR creation for workflows:

```bash
erk admin github-pr-setting --disable
```

## Troubleshooting

**"Resource not accessible by integration"**

- Ensure you have admin access to the repository
- Re-authenticate gh CLI: `gh auth refresh -s admin:repo_hook`

**Permissions not updating**

- Wait a few seconds and try again (GitHub API may have delay)
- Verify you're authenticated: `gh auth status`

## TODO

- [ ] Add workflow configuration guide
- [ ] Document label-based queue triggering
- [ ] Add security best practices
- [ ] Document integration with existing workflows

## See Also

- [GitHub Actions Permissions](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#permissions-for-the-github_token)
- TODO: Link to erk queue architecture docs
