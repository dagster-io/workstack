# Plan: Add [erk-plan] Suffix to Plan Issue Titles

## Goal
Replace the "Plan: " prefix approach with an "[erk-plan]" suffix for plan issue titles. When creating PRs via `erk submit`, strip this suffix. Also strip suffix when deriving branch/worktree names.

## Changes Required

### 1. Update submit.py to strip suffix instead of prefix
**File:** `src/erk/cli/commands/submit.py`

Change `_strip_plan_prefix()` to `_strip_erk_plan_suffix()`:
```python
def _strip_erk_plan_suffix(title: str) -> str:
    """Strip '[erk-plan]' suffix from issue title for use as PR title."""
    if title.endswith(" [erk-plan]"):
        return title[:-11]
    return title
```

Update the call site at line 212 to use the new function.

### 2. Add suffix in plan creation pathways

**Key Pattern:** Extract base title first, derive worktree name from base title, then add suffix for issue title only.

#### 2a. plan_save_to_issue.py
**File:** `packages/dot-agent-kit/.../kit_cli_commands/erk/plan_save_to_issue.py`
```python
# Line 79: Extract base title
base_title = extract_title_from_plan(plan)
# Line 92: Derive worktree name from BASE title (no suffix)
worktree_name = sanitize_worktree_name(base_title)
# Line 118: Create issue with SUFFIXED title
issue_title = f"{base_title} [erk-plan]"
result = github.create_issue(repo_root, issue_title, formatted_body, labels=["erk-plan"])
```

#### 2b. create_plan_from_context.py
**File:** `packages/dot-agent-kit/.../kit_cli_commands/erk/create_plan_from_context.py`
- Line 59: Keep base title for worktree name
- Line 79: Add suffix when creating issue

#### 2c. create_issue_from_session.py
**File:** `packages/dot-agent-kit/.../kit_cli_commands/erk/create_issue_from_session.py`
- Line 143: Keep base title for worktree name
- Add suffix when creating issue (gh issue create --title)

#### 2d. plan/create_cmd.py
**File:** `src/erk/cli/commands/plan/create_cmd.py`
- Line 78: Keep base title for worktree name derivation
- Add suffix before issue creation at line 120

### 3. Update tests

#### 3a. test_submit.py
- Rename `test_strip_plan_prefix` to `test_strip_erk_plan_suffix`
- Update test cases to use suffix instead of prefix
- Update `test_submit_strips_plan_prefix_from_pr_title` to use suffix

#### 3b. Add tests for plan creation commands
- Verify "[erk-plan]" suffix is added to created issue titles

## Files to Modify
1. `src/erk/cli/commands/submit.py`
2. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/plan_save_to_issue.py`
3. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_plan_from_context.py`
4. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_issue_from_session.py`
5. `src/erk/cli/commands/plan/create_cmd.py`
6. `tests/commands/test_submit.py`