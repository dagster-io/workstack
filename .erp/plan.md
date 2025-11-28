# Fix plan-clone Command to Handle Associated PRs

## Problem

When `/erk:plan-clone` clones an issue, it:
- Creates a new issue with the **same title**
- Closes the original issue
- **Does NOT close the associated PR**

This leaves an orphaned PR that causes branch collision detection to fail when trying to submit the cloned issue.

**Example:**
- Issue #1350 → PR #1363 (branch: `refactor-manual-error-checking`)
- Clone creates #1413 with same title → would derive same branch name
- #1350 closed, but PR #1363 still open and linked to #1350
- `erk submit 1413` fails with collision detection error

## Root Cause

The branch name is derived from **issue title** (truncated to 30 chars), not from `worktree_name` in plan-header. When titles are similar, they derive to the same branch name.

## Solution

Update `/erk:plan-clone` to close any associated PR before closing the original issue.

### Changes to `.claude/commands/erk/plan-clone.md`

Add new step between "Close Original Issue" and current step 9:

**Step 8.5: Close Associated PR (if exists)**

1. Derive branch name from original issue title (same logic as workflow)
2. Check if PR exists for that branch: `gh pr view <branch> --json state,number`
3. If PR exists and is OPEN:
   - Close PR with comment: "Closing PR - issue cloned to #<new_issue_number>"
   - `gh pr close <branch> --comment "..."`
4. If PR doesn't exist or already closed, continue silently

**Pseudocode:**
```bash
# Derive branch name from title
branch_name=$(echo "$title" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')
branch_name="${branch_name:0:30}"
branch_name=$(echo "$branch_name" | sed 's/-$//')

# Check if PR exists
if gh pr view "$branch_name" --json state,number &>/dev/null; then
    pr_state=$(gh pr view "$branch_name" --json state -q '.state')
    if [ "$pr_state" = "OPEN" ]; then
        gh pr close "$branch_name" --comment "Closing PR - issue cloned to #$new_issue_number with new worktree name"
        echo "Closed associated PR for branch: $branch_name"
    fi
fi
```

## Files to Modify

1. **`.claude/commands/erk/plan-clone.md`** - Add PR cleanup step

## Testing

1. Create test issue with erk-plan label and plan content
2. Submit it to create a PR
3. Clone the issue with `/erk:plan-clone`
4. Verify:
   - Original issue is closed
   - Associated PR is closed with explanatory comment
   - New issue can be submitted without collision error

## Alternative Considered

**Change title to derive different branch**: Rejected because it changes the semantic meaning of the issue and requires user to understand naming conventions.