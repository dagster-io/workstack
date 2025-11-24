## Summary

Modify `erk down --delete-current` and `erk up --delete-current` to warn (not error) when no pull request exists for a branch, while still blocking deletion if a PR exists but is not merged. This provides balance between safety and flexibility for experimental branches.

## Context & Understanding

### Current Behavior
The `--delete-current` flag requires a pull request to exist and be merged before allowing branch deletion. This is enforced in `verify_pr_merged()` at `/Users/schrockn/code/erk/src/erk/cli/commands/navigation_helpers.py:118-138`.

### Design Intent Discovery
- The PR requirement appears to be a safety mechanism to prevent accidental deletion of unmerged work
- Both `erk down` and `erk up` commands share this same safety check
- Test cases explicitly verify this behavior, indicating it was an intentional design decision
- The pattern frames `--delete-current` as a "merge cleanup" feature, not general deletion

### Key Insight
Many legitimate use cases don't require PRs:
- Local experimental branches
- Temporary work branches  
- Feature exploration that doesn't need review
- Quick fixes or prototypes

The current behavior forces users to create unnecessary PRs or use multiple commands (`erk down`, then `erk delete`), reducing efficiency.

### Architecture Notes
- `/Users/schrockn/code/erk/src/erk/cli/commands/navigation_helpers.py` contains shared navigation utilities
- Both `/Users/schrockn/code/erk/src/erk/cli/commands/down.py` and `/Users/schrockn/code/erk/src/erk/cli/commands/up.py` call `verify_pr_merged()`
- Tests are in `/Users/schrockn/code/erk/tests/commands/navigation/test_down.py` and `test_up.py`

## Implementation Steps

### Step 1: Modify verify_pr_merged() function

**File:** `/Users/schrockn/code/erk/src/erk/cli/commands/navigation_helpers.py`

Current implementation (lines 118-138):
```python
def verify_pr_merged(ctx: ErkContext, repo_root: Path, branch: str) -> None:
    """Verify that the branch's PR is merged on GitHub.
    
    Raises SystemExit if PR not found or not merged.
    """
    pr_info = ctx.github.get_pr_status(repo_root, branch, debug=False)
    
    if pr_info.state == "NONE" or pr_info.pr_number is None:
        user_output(
            click.style("Error: ", fg="red") + f"No pull request found for branch '{branch}'.\n"
            "Cannot verify merge status."
        )
        raise SystemExit(1)
    
    if pr_info.state != "MERGED":
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request for branch '{branch}' is not merged.\n"
            "Only merged branches can be deleted with --delete-current."
        )
        raise SystemExit(1)
```

Change to:
```python
def verify_pr_merged(ctx: ErkContext, repo_root: Path, branch: str) -> None:
    """Verify that the branch's PR is merged on GitHub.
    
    Warns if no PR exists, raises SystemExit if PR exists but not merged.
    """
    pr_info = ctx.github.get_pr_status(repo_root, branch, debug=False)
    
    if pr_info.state == "NONE" or pr_info.pr_number is None:
        # Warn but continue when no PR exists
        user_output(
            click.style("Warning: ", fg="yellow") + f"No pull request found for branch '{branch}'.\n"
            "Proceeding with deletion without PR verification."
        )
        return  # Allow deletion to proceed
    
    if pr_info.state != "MERGED":
        # Keep error for unmerged PRs (safety mechanism remains)
        user_output(
            click.style("Error: ", fg="red")
            + f"Pull request for branch '{branch}' is not merged.\n"
            "Only merged branches can be deleted with --delete-current."
        )
        raise SystemExit(1)
```

**Key changes:**
- Change "Error: " to "Warning: " with yellow color when no PR exists
- Return normally instead of `raise SystemExit(1)` for missing PRs
- Keep the error for PRs that exist but aren't merged (preserves safety)

### Step 2: Update test for erk down --delete-current with no PR

**File:** `/Users/schrockn/code/erk/tests/commands/navigation/test_down.py`

Find test around line 552: `test_down_delete_current_no_pr`

Current behavior: Expects command to fail with exit code 1
New behavior: Should succeed with warning message displayed

Changes needed:
- Mock should still return `PRStatus(state="NONE", pr_number=None)`
- Expect exit code 0 (success) instead of 1
- Verify warning message is displayed in output
- Verify branch deletion proceeds successfully

### Step 3: Update test for erk up --delete-current with no PR

**File:** `/Users/schrockn/code/erk/tests/commands/navigation/test_up.py`

Similar changes as Step 2, for the corresponding test in the up command test file.

### Step 4: Add new test cases for warning behavior

Add tests to verify:
1. Warning message appears when no PR exists
2. Branch deletion proceeds after warning
3. Unmerged PRs still block deletion (safety preserved)
4. Merged PRs work as before (no regression)

**Test coverage matrix:**
| Scenario | Expected Result |
|----------|----------------|
| No PR exists | Warning displayed, deletion proceeds |
| PR exists but open | Error displayed, deletion blocked |
| PR exists and merged | No warning, deletion proceeds |
| PR exists but closed (not merged) | Error displayed, deletion blocked |

### Step 5: Verify both commands work consistently

Since both `erk down` and `erk up` use the same `verify_pr_merged()` function:
- No changes needed in `/Users/schrockn/code/erk/src/erk/cli/commands/down.py`
- No changes needed in `/Users/schrockn/code/erk/src/erk/cli/commands/up.py`
- Both commands automatically inherit the new behavior

### Step 6: Run test suite

Execute tests to ensure no regressions:
```bash
uv run pytest tests/commands/navigation/test_down.py -xvs
uv run pytest tests/commands/navigation/test_up.py -xvs
uv run pytest tests/commands/navigation/ -xvs  # All navigation tests
```

## Testing Strategy

Based on fake-driven testing architecture:

### Layer 4: Business Logic Tests (Primary)
- Mock `ctx.github.get_pr_status()` to return different PR states
- Use `FakeGitHub` if available, or mock the method
- Test through CliRunner, not subprocess
- Verify output messages and exit codes

### Layer 5: Integration Tests (Optional)
- Could add one smoke test with actual GitHub API
- Only if critical for production confidence

## Success Criteria

✅ `erk down --delete-current` succeeds with warning when no PR exists
✅ `erk up --delete-current` succeeds with warning when no PR exists  
✅ Warning message is yellow and informative
✅ Unmerged PRs still block deletion (safety preserved)
✅ All existing tests pass
✅ New tests verify warning behavior

## Risks & Mitigations

**Risk:** Users might accidentally delete branches they meant to keep
**Mitigation:** Clear yellow warning message makes risk visible

**Risk:** Confusion about when deletion is allowed
**Mitigation:** Consistent behavior - warn for no PR, error for unmerged PR

## Alternative Considered

We considered adding a `--force` flag but rejected it because:
- Adds complexity with minimal benefit  
- Warning provides sufficient safety
- Simpler UX with one less flag to remember

🤖 Generated with [Claude Code](https://claude.com/claude-code)
