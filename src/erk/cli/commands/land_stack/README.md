# Land Stack Command

Erk land-stack command: Land stacked PRs sequentially from bottom to top.

## Module Overview

**Purpose:** Merges a stack of Graphite pull requests sequentially from bottom (closest to trunk) to top (current branch), with restacking between each merge.

**Stack direction:** main (bottom) → feat-1 → feat-2 → feat-3 (top)

**Landing order:** feat-1, then feat-2, then feat-3 (bottom to top)

**Integration:** Works with Graphite (gt CLI), GitHub CLI (gh), and worktrees.

## Complete 5-Phase Workflow

### Phase 1: Discovery & Validation

- Build list of branches from bottom of stack to current branch
- Check Graphite enabled, clean working directory, not on trunk, no worktree conflicts
  - **Note:** Worktree conflict validation checks ALL worktrees, including the current worktree. You must run `erk consolidate` if any branches in the stack are checked out in worktrees, or run land-stack from the root worktree.
- Verify all branches have open PRs
- Check GitHub for merge conflicts (prevents landing failures)

### Phase 2: User Confirmation

- Display PRs to land and get user confirmation (or --force to skip)

### Phase 3: Landing Sequence

For each branch from bottom to top:

1. **Checkout** branch (or verify already on branch)
2. **Verify stack integrity** - parent is trunk after previous restacks
3. **Verify and update PR base** [Phase 2.5] - Check PR base on GitHub matches expected parent (trunk), update if stale
4. **Merge PR** via `gh pr merge --squash --auto`
5. **Sync trunk** with remote (fetch + checkout + pull --ff-only + checkout back)

**Note:** Restacking (`gt sync -f`) and force-pushing remaining branches (`gt submit`) are NOT run automatically to give users full control. After landing completes, you can manually run these commands if needed.

### Phase 4: Cleanup

- Navigate to safe branch (trunk or next unmerged branch)
- Regenerate context after directory changes

**Note:** Worktree cleanup (`erk sync -f`) is NOT run automatically. After landing, you can manually run `erk sync -f` to remove worktrees for merged branches.

### Phase 5: Final State

- Display what was accomplished
- Show current branch and merged branches
- Display next steps for manual operations:
  - Run `erk sync -f` to remove worktrees for merged branches
  - Run `gt sync -f` to rebase remaining stack branches (if needed)

## Phase 2.5: PR Base Verification (Race Condition Prevention)

**Problem:** When landing stacked PRs, a race condition can occur where:

1. Parent PR (feat-1) merges and deletes its branch
2. Child PR (feat-2) base on GitHub still points to deleted feat-1
3. Child PR merges into deleted branch, creating orphaned commit that never reaches main

**Solution:** Phase 2.5 runs BEFORE merge to verify and update PR bases:

- **Check PR base** on GitHub via `gh pr view --json baseRefName`
- **Compare** to expected parent (trunk after previous restack)
- **Update if stale** via GitHub API
- **Include retry logic** with exponential backoff for transient API failures

**Timing:** Phase 2.5 must run BEFORE Phase 4 (merge) to eliminate the race condition window. Previous implementations updated bases AFTER merge, which left a timing window where the base could be stale.

**Retry Logic:** GitHub API calls include exponential backoff retry (max 3 attempts, 1s base delay) to handle:

- Network timeouts
- Rate limiting
- Temporary API unavailability
- Connection issues

## Key Concepts

**Stack Direction:**

- Bottom (downstack) = trunk (main/master)
- Top (upstack) = leaves (feature branches furthest from trunk)
- Commands like `gt up` / `gt down` navigate this direction

**Restacking:**
After PRs are merged, remaining upstack branches need to be rebased onto the new trunk state to maintain stack integrity. This is done manually by running `gt sync -f` after landing completes.

**Manual Control:** The land-stack command does NOT automatically run `gt sync -f` or `erk sync -f`. This gives you full control over when restacking and cleanup happen, allowing you to inspect the state between operations.

**Worktree Conflicts:**
Git prevents checking out a branch in multiple worktrees. Phase 1 validation detects ANY branch in the stack that is checked out in ANY worktree (including the current worktree) and requires `erk consolidate` to fix. This ensures all landing operations happen from a consistent location (the root worktree).

**Context Regeneration:**
After `os.chdir()` calls, must regenerate ErkContext to update `ctx.cwd`. This happens in Phase 4 after navigation operations.

## Error Handling Strategy

**Fail Fast:**
All validation happens in Phase 1, before user confirmation. If any precondition fails, command exits immediately with helpful error message.

**Error Types:**

- `SystemExit(1)` - All validation failures and expected errors
- `subprocess.CalledProcessError` - git/gh/gt command failures (caught and converted to SystemExit)
- `FileNotFoundError` - Missing CLI tools (caught and converted to SystemExit)

**Error Messages:**
All errors include:

- Clear description of what failed
- Context (branch names, paths, PR numbers)
- Concrete fix steps ("To fix: ...")

## Troubleshooting

### Stale PR Base Scenarios

**Symptom:** PR merges but commit doesn't appear in trunk branch history

**Cause:** PR was merged into a deleted parent branch instead of trunk

**Prevention:** Phase 2.5 automatically detects and fixes stale bases before merge

**Manual Fix (if it happens):**

```bash
# 1. Find the orphaned merge commit
gh pr view <pr-number> --json mergeCommit

# 2. Cherry-pick to trunk
git checkout main
git cherry-pick <merge-commit-sha>
git push origin main

# 3. Close and reopen PR (or create new PR)
```

### GitHub API Failures

**Symptom:** "Failed to get PR base from GitHub" or "Failed to update PR base"

**Cause:** Transient network issues, rate limiting, or API unavailability

**Automatic Retry:** Phase 2.5 includes exponential backoff retry (3 attempts, 1s → 2s → 4s delays)

**Manual Retry:**

```bash
# Wait a few seconds and retry the land-stack command
erk land-stack
```

**Check Rate Limits:**

```bash
gh api rate_limit
```
