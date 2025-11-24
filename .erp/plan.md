<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>📋 Implementation Plan</strong></summary>

## Implementation Plan: Display GitHub Action Runs in Plan List

### Changes Overview

1. **Enhance data model** to include branch names in PR info
2. **Add Issue→PR→Run traversal** logic to fetch workflow runs
3. **Reorganize columns** to move State next to Plan, replace Action with GitHub run data
4. **Display format**: Compact icon + linkified run ID (e.g., `⏳ #12345`)

### Detailed Steps

#### 1. Update `PullRequestInfo` dataclass

**File**: `packages/erk-shared/src/erk_shared/github/types.py`

- Add `head_ref_name: str` field to store branch name
- Update all construction sites to include this field

#### 2. Update GitHub integration to fetch branch names

**File**: `src/erk/core/github/real.py`

- Modify `get_prs_linked_to_issues()` to include `headRefName` in GraphQL query
- Update `parse_github_pr_list()` to extract `headRefName` from JSON
- Ensure all PR list commands include `headRefName` in `--json` fields

#### 3. Add PR→Run matching logic

**File**: `src/erk/cli/commands/plan/list_cmd.py`

- Create helper function `get_run_for_pr(pr: PullRequestInfo, all_runs: list[WorkflowRun]) -> WorkflowRun | None`
- Match `pr.head_ref_name` to `run.branch`
- Return most recent run (highest run_id or latest by position in list)

#### 4. Add Issue→PR→Run traversal

**File**: `src/erk/cli/commands/plan/list_cmd.py`

- Fetch workflow runs once: `ctx.github.list_workflow_runs(repo.root, "implement-plan.yml")`
- For each plan, get linked PRs, select latest PR, find its most recent run
- Build mapping: `plan_number -> WorkflowRun | None`

#### 5. Reorganize table columns

**File**: `src/erk/cli/commands/plan/list_cmd.py`

- **Before**: Plan | PR | Checks | State | Action | Title | Local Worktree
- **After**: Plan | State | PR | Checks | Action | Title | Local Worktree
- Move State column immediately after Plan column

#### 6. Replace Action column display logic

**File**: `src/erk/cli/commands/plan/list_cmd.py`

- Remove `determine_action_state()` function (comment-based state)
- Create `format_workflow_run(run: WorkflowRun | None, repo_owner: str, repo_name: str) -> str`
- Format:
  - No run: `-` (dim)
  - With run: `{icon} #{run_id}` as terminal hyperlink
  - Icons: `⏳` (queued), `⏳` (in_progress), `✓` (success), `✗` (failure), `⏸` (cancelled)
- Terminal link: `https://github.com/{owner}/{repo}/actions/runs/{run_id}`

#### 7. Handle edge cases

- Issue with no PRs → show `-`
- Issue with multiple PRs → pick latest by PR number
- PR with no runs → show `-`
- PR with multiple runs → pick most recent by run_id

### Files Modified

1. `packages/erk-shared/src/erk_shared/github/types.py` - Add `head_ref_name` field
2. `src/erk/core/github/real.py` - Fetch branch names in PR queries
3. `src/erk/cli/commands/plan/list_cmd.py` - Main display logic changes

### Testing Approach

- Test with plans that have: no PRs, single PR, multiple PRs
- Test with PRs that have: no runs, single run, multiple runs
- Verify terminal links work (manually click in terminal)
- Check column alignment with various run states

</details>
<!-- /erk:metadata-block:plan-body -->

---

## Execution Commands

**Submit to Erk Queue:**

```bash
erk submit 1102
```

---

### Local Execution

**Standard mode (interactive):**

```bash
erk implement 1102
```

**Yolo mode (fully automated, skips confirmation):**

```bash
erk implement 1102 --yolo
```

**Dangerous mode (auto-submit PR after implementation):**

```bash
erk implement 1102 --dangerous
```
