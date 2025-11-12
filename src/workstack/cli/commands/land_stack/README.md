# Land Stack Command

Workstack land-stack command: Land stacked PRs sequentially from bottom to top.

## Module Overview

**Purpose:** Merges a stack of Graphite pull requests sequentially from bottom (closest to trunk) to top (current branch), with restacking between each merge.

**Stack direction:** main (bottom) → feat-1 → feat-2 → feat-3 (top)

**Landing order:** feat-1, then feat-2, then feat-3 (bottom to top)

**Integration:** Works with Graphite (gt CLI), GitHub CLI (gh), and worktrees.

## Complete 5-Phase Workflow

### Phase 1: Discovery & Validation

- Build list of branches from bottom of stack to current branch
- Check Graphite enabled, clean working directory, not on trunk, no worktree conflicts
- Verify all branches have open PRs
- Check GitHub for merge conflicts (prevents landing failures)

### Phase 2: User Confirmation

- Display PRs to land and get user confirmation (or --force to skip)

### Phase 3: Landing Sequence

For each branch from bottom to top:

1. Checkout branch (or verify already on branch)
2. Verify stack integrity (parent is trunk after previous restacks)
3. Update PR base branch on GitHub if stale
4. Merge PR via `gh pr merge --squash --auto`
5. Sync trunk with remote (fetch + checkout + pull --ff-only + checkout back)
6. Restack remaining branches via `gt sync -f`
7. Submit updated PRs to GitHub

### Phase 4: Cleanup

- Remove merged branch worktrees
- Navigate to safe branch (trunk or next unmerged branch)
- Regenerate context after directory changes

### Phase 5: Final State

- Display what was accomplished
- Show current branch and merged branches

## Key Concepts

**Stack Direction:**

- Bottom (downstack) = trunk (main/master)
- Top (upstack) = leaves (feature branches furthest from trunk)
- Commands like `gt up` / `gt down` navigate this direction

**Restacking:**
After each PR merge, `gt sync -f` rebases all remaining branches onto the new trunk state. This maintains stack integrity as PRs are landed.

After each PR merge on GitHub, we explicitly sync the local trunk branch with remote (git fetch + pull --ff-only) before running `gt sync -f`. This ensures the local trunk contains the just-merged PR commits, preventing race conditions where Graphite sees merged PRs but stale trunk state.

**Worktree Conflicts:**
Git prevents checking out a branch in multiple worktrees. Phase 1 validation detects this and suggests `workstack consolidate` to fix.

**Context Regeneration:**
After `os.chdir()` calls, must regenerate WorkstackContext to update `ctx.cwd`. This happens in Phase 4 after navigation operations.

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
