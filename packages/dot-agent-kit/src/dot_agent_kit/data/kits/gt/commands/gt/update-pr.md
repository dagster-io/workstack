---
description: Update PR by staging changes, committing, restacking, and submitting
---

# Update PR

Streamlines updating an existing PR in a Graphite stack by auto-staging and committing changes, restacking the stack, and submitting updates.

## What This Command Does

1. **Check PR exists**: Verifies current branch has an associated PR
2. **Auto-stage and commit**: Commits any uncommitted changes with default message
3. **Restack**: Restacks the branch with conflict detection
4. **Submit**: Updates the existing PR

## Usage

```bash
/gt:update-pr
```

## Implementation

**IMPORTANT**: All git commands must be run from the repository root, not from subdirectories. Use absolute paths or ensure working directory is set to repo root before executing git operations.

When this command is invoked:

### 1. Check PR Exists

```bash
gh pr view --json number,url
```

Parse the JSON output to verify the current branch has an associated PR.

**Error handling**: If command fails (no PR exists), show error:

```
❌ No PR associated with current branch

Create one with:
  /gt:submit-branch
```

### 2. Check for Uncommitted Changes

```bash
git status --porcelain
```

**If output is empty** (no uncommitted changes):

- Skip to Step 4 (no changes to commit)

**If output is non-empty** (uncommitted changes exist):

- Proceed to Step 3

### 3. Auto-stage and Commit

Stage all changes:

```bash
git add .
```

Commit with simple default message:

```bash
git commit -m "Update changes"
```

**Error handling**: If commit fails, show error message and exit.

### 4. Restack

Run restack with no-interactive mode:

```bash
gt restack --no-interactive
```

**Error handling**: If command fails (exit code ≠ 0), abort with error:

```
❌ Conflicts occurred during restack

Resolve conflicts manually, then run this command again:
  /gt:update-pr
```

**Important**: Do NOT attempt to auto-resolve conflicts. User must resolve manually.

### 5. Submit

Submit to update the existing PR:

```bash
gt submit
```

**Error handling**: If command fails, show error message and exit.

### 6. Confirm Success

After successful submission:

```
✅ PR updated successfully
```

## Example Output

### Success with Uncommitted Changes

```
Checking for PR association...
✓ PR #235 found

Checking for uncommitted changes...
✓ Uncommitted changes detected

Staging and committing changes...
✓ Changes committed with message "Update changes"

Restacking branch...
✓ Restack complete

Submitting updates...
✓ Submitted successfully

✅ PR updated successfully
```

### Success with No Uncommitted Changes

```
Checking for PR association...
✓ PR #235 found

Checking for uncommitted changes...
✓ No uncommitted changes

Restacking branch...
✓ Restack complete

Submitting updates...
✓ Submitted successfully

✅ PR updated successfully
```

### No PR Error

```
❌ No PR associated with current branch

Create one with:
  /gt:submit-branch
```

### Restack Conflict Error

```
Checking for PR association...
✓ PR #235 found

Checking for uncommitted changes...
✓ Uncommitted changes detected

Staging and committing changes...
✓ Changes committed with message "Update changes"

Restacking branch...
❌ Conflicts occurred during restack

Resolve conflicts manually, then run this command again:
  /gt:update-pr
```

## Notes

- Uses simple default commit message: "Update changes"
- Does NOT use git-diff-summarizer for commit message generation (optimized for speed)
- Aborts immediately on restack conflicts - requires manual resolution
- Uses `gh` CLI to check PR existence (requires GitHub CLI authentication)
- Uses `gt` CLI for restack and submit operations
