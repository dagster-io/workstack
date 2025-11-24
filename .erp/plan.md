# Fix /gt:update-pr Command to Handle PR Creation

## Overview

The `/gt:update-pr` command currently rejects branches without existing PRs, causing it to fail with a "No PR associated with current branch" error. However, the intent is to update an existing PR OR create a new one if none exists. The root causes are:

1. **Early exit check (lines 34-36)**: Rejects immediately if no PR exists
2. **publish=False flag (line 52)**: Prevents Graphite from creating new PRs
3. **Incorrect semantics**: Uses `publish=False` which tells gt submit not to create/publish the PR

## Problem Analysis

### Current Behavior

```python
# Line 34-36: Early exit
pr_info = kit.github().get_pr_info()
if not pr_info:
    return {"success": False, "error": "No PR associated with current branch"}

# Line 52: Prevents PR creation
result = kit.graphite().submit(publish=False, restack=False)
```

The `submit(publish=False)` call tells Graphite to NOT create or publish a new PR, only update an existing one.

### Expected Behavior

Compare with `submit_branch.py` (line 401):

```python
result = ops.graphite().submit(publish=True, restack=True)
```

The `submit_branch.py` command uses `publish=True`, which allows Graphite to:
- Create a new PR if one doesn't exist
- Handle the complete submission flow
- Properly integrate with Graphite's PR tracking

## Solution

### Step 1: Remove Early Exit Check

Delete lines 34-36 that reject branches without existing PRs. Let Graphite handle both creation and update scenarios.

**Why**: Graphite's `submit` command is designed to handle both creating new PRs and updating existing ones. The early exit artificially restricts this functionality.

### Step 2: Use publish=True Flag

Change line 52 from:
```python
result = kit.graphite().submit(publish=False, restack=False)
```

To:
```python
result = kit.graphite().submit(publish=True, restack=False)
```

**Why**: The `publish=True` flag tells Graphite to create a new PR if one doesn't exist, aligning with the actual intent of the update-pr command.

### Step 3: Simplify Response Handling

Since we're now letting Graphite handle both creation and updates, the response logic becomes:

1. Let `submit` complete (with create or update)
2. Attempt to fetch PR info (as in `submit_branch.py`)
3. Return success with PR details

This mirrors the successful pattern in `submit_branch.py` (lines 474-530).

### Step 4: Optional - Add PR Creation Messaging

Consider adding a check after successful submit to distinguish between:
- Created new PR (PR didn't exist before)
- Updated existing PR (PR already existed)

This can be done by checking if `pr_info` was initially None, then comparing with final state.

## Command Semantics

### Current Intent vs Implementation Mismatch

From the command documentation (update-pr.md line 36-39):
```
## When to Use

- Update an existing PR with new changes
- Quick iteration on PR feedback
```

The documentation says "update an existing PR", but the real use case (from Graphite workflows) is:
- Submit changes (create PR if needed, OR update if exists)
- Quick branch updates in Graphite stacks

The command should support both paths transparently.

## Testing Considerations

After implementation, verify:

1. **Branch without PR**: Create new branch, run update-pr → should create new PR
2. **Branch with PR**: Create changes on existing PR branch, run update-pr → should update PR
3. **With uncommitted changes**: Ensure changes are committed before submit
4. **Restack behavior**: With `restack=False`, only the current branch is affected

## Graphite Integration

### How publish Flag Works

- `publish=True`: Tells `gt submit` to create new PRs (use for initial submission)
- `publish=False`: Tells `gt submit` to update existing PRs only (restrictive)
- `restack=True`: Updates all child branches after submission
- `restack=False`: Updates only the current branch

For update-pr (focused on single branch updates), `restack=False` is appropriate to avoid affecting child branches.

## Context & Understanding

### Architectural Insights

- **Graphite Design Pattern**: The `publish` flag in `gt submit` determines whether new PRs are created, not whether they're posted to GitHub. This is a Graphite-specific concept.
- **Two-tier Commands**: `submit_branch` (complete workflow) vs `update_pr` (quick update). Both should create PRs if needed, but `update_pr` is simpler (no squashing, no AI analysis).
- **RealGtKit Abstraction**: Both commands use RealGtKit to delegate operations, but differ in workflow complexity and user interaction.

### Known Pitfalls

- **publish=False Misconception**: Many developers think this means "don't publish to GitHub". Actually it means "don't create new PRs". This caused the bug.
- **Early Exit Anti-Pattern**: Checking PR existence upfront prevents Graphite from handling both scenarios. Let the command layer handle all valid states.
- **Naming Ambiguity**: The command is called "update-pr" but should handle creation too. Consider if documentation needs clarification or if the name is accurate enough.

### API/Tool Quirks

- **gh pr info behavior**: Returns PR details for current branch or None if no PR. The wrapper in RealGtKit retries with exponential backoff (as seen in submit_branch.py lines 474-489) due to GitHub API latency.
- **gt submit flags**: The `--publish` flag doesn't appear to have a `--no-publish` counterpart in Graphite. When `publish=False` is used, it means the API call uses `gt submit` without the `--publish` flag.

### Complex Reasoning

1. **Why not just use submit_branch.py code?** 
   - `submit_branch` is more complex: it does pre-analysis (commit/squash), AI analysis (diff review), and post-analysis (metadata updates)
   - `update_pr` should be simpler and faster: just stage, commit, restack, submit
   - Different workflows for different scenarios

2. **Why remove early exit instead of adding another code path?**
   - Graphite's `submit` command is designed to handle both cases
   - Adding logic to distinguish them adds complexity without benefit
   - Let the tool do what it's designed for

3. **restack=False reasoning**:
   - `update_pr` is a single-branch operation (quick update)
   - Using `restack=True` would update all child branches, which may not be desired
   - User can run `gt restack` separately if they need full restack

### Raw Discoveries Log

- `submit_branch.py` successfully creates PRs using `publish=True` (line 401)
- `update_pr.py` unnecessarily prevents this with `publish=False` (line 52)
- Early PR existence check (lines 34-36) is a blocker that Graphite doesn't need
- `submit_branch.py` includes retry logic for PR info retrieval (lines 474-489) due to GitHub API eventual consistency
- Both commands commit changes, but `submit_branch` also squashes if there are 2+ commits
- RealGtKit provides git, graphite, and github sub-operations via composition
- The `restack` parameter controls whether child branches are updated

### Planning Artifacts

- Examined `update_pr.py` (lines 1-72) to understand current implementation
- Reviewed `submit_branch.py` (lines 1-615) to compare working pattern
- Checked `ops.py` (lines 143-180) to understand GraphiteGtKit.submit signature
- Reviewed `update-pr.md` command documentation
- Reviewed `gt-update-pr-submitter.md` agent documentation

### Implementation Risks

- **Behavioral Change**: Removing the PR existence check changes command semantics. However, this aligns with Graphite's actual capabilities.
- **No Backward Compatibility Issue**: The command is relatively new, and the current behavior (rejection) is arguably a bug.
- **Testing Coverage**: Need to verify both creation and update scenarios work correctly.
- **GitHub API Latency**: After `gt submit --publish`, the PR may not immediately appear in `gh pr info`. The retry logic in `submit_branch.py` handles this, but `update_pr.py` doesn't currently attempt retry (could be added if needed).

## Summary of Changes

1. Remove lines 34-36 (early PR existence check)
2. Change line 52: `publish=False` → `publish=True`
3. Optionally add PR info retrieval with retry (following submit_branch.py pattern)
4. Update documentation if needed to clarify that command creates PRs if needed

## File Location

`packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/update_pr.py`
