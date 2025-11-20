# Implementation Plan: `.submission/` Protocol for Remote AI Implementation

**Date:** 2025-11-20
**Status:** Planning

---

## Overview

Simplify the submission workflow: `erk submit` copies `.plan/` to `.submission/`, commits it, pushes, and triggers GitHub Actions. The `/erk:implement-plan` command handles iterative CI fixing internally.

## Key Design Decisions

- ✅ No new slash commands - use existing `/erk:create-planned-wt`
- ✅ Only new component: `erk submit` CLI command
- ✅ GitHub Actions runs with `--dangerously-skip-permissions`
- ✅ `/erk:implement-plan` iteratively fixes CI issues internally
- ✅ .submission/ deleted after successful implementation
- ✅ .plan/ remains untouched as source of truth
- ✅ Extend existing `implement-plan.yml` workflow

---

## Implementation Phases

### Phase 1: Add `.submission/` Folder Utilities

**Goal:** Add minimal utilities for copying .plan/ to .submission/

**Add to `src/erk/core/plan_folder.py`:**

```python
def copy_plan_to_submission(worktree_path: Path) -> Path:
    """Copy .plan/ folder to .submission/ folder.

    Args:
        worktree_path: Path to worktree directory

    Returns:
        Path to created .submission/ directory

    Raises:
        FileNotFoundError: If .plan/ folder doesn't exist
        FileExistsError: If .submission/ folder already exists
    """
    plan_folder = worktree_path / ".plan"
    submission_folder = worktree_path / ".submission"

    if not plan_folder.exists():
        raise FileNotFoundError(f"No .plan/ folder found at {worktree_path}")

    if submission_folder.exists():
        raise FileExistsError(f".submission/ folder already exists at {worktree_path}")

    shutil.copytree(plan_folder, submission_folder)
    return submission_folder


def get_submission_path(worktree_path: Path) -> Path | None:
    """Get path to .submission/ folder if it exists."""
    submission_folder = worktree_path / ".submission"
    if submission_folder.exists() and submission_folder.is_dir():
        return submission_folder
    return None


def remove_submission_folder(worktree_path: Path) -> None:
    """Remove .submission/ folder if it exists."""
    submission_folder = worktree_path / ".submission"
    if submission_folder.exists():
        shutil.rmtree(submission_folder)
```

**Files affected:**
- `src/erk/core/plan_folder.py` (+40 lines)

**Tests needed:**
- `test_copy_plan_to_submission()` - Copies correctly
- `test_copy_plan_to_submission_no_plan()` - Error when no .plan/
- `test_copy_plan_to_submission_already_exists()` - Error when .submission/ exists
- `test_get_submission_path()` - Detects .submission/
- `test_remove_submission_folder()` - Removes folder

---

### Phase 2: Implement `erk submit` Command

**Goal:** Create command that copies .plan/ to .submission/, commits, pushes, triggers workflow

**Rewrite `src/erk/cli/commands/submit.py`:**

```python
"""Submit plan for remote AI implementation via GitHub Actions."""

import subprocess
from pathlib import Path

import click

from erk.cli.core import discover_repo_context
from erk.cli.output import user_output
from erk.core.context import ErkContext
from erk.core.plan_folder import copy_plan_to_submission, get_submission_path
from erk.core.repo_discovery import RepoContext


@click.command("submit")
@click.option("--dry-run", is_flag=True, help="Show what would be done without executing")
@click.pass_obj
def submit_cmd(ctx: ErkContext, dry_run: bool) -> None:
    """Submit plan for remote AI implementation via GitHub Actions.

    Copies .plan/ folder to .submission/, commits it, pushes to remote,
    and triggers the GitHub Actions workflow for implementation.

    Requires:
    - Current directory must have a .plan/ folder
    - Must be on a branch (not detached HEAD)
    """
    # Get repository context
    if isinstance(ctx.repo, RepoContext):
        repo = ctx.repo
    else:
        repo = discover_repo_context(ctx, ctx.cwd)

    # Check for .plan/ folder
    plan_folder = ctx.cwd / ".plan"
    if not plan_folder.exists():
        user_output(
            click.style("Error: ", fg="red") + "No .plan/ folder found.\n\n"
            "The current directory must contain a .plan/ folder.\n"
            "To create one, use: /erk:create-planned-wt"
        )
        raise SystemExit(1)

    # Check if .submission/ already exists
    if get_submission_path(ctx.cwd):
        user_output(
            click.style("Error: ", fg="red") + ".submission/ folder already exists.\n\n"
            "This usually means a submission is in progress.\n"
            "To clean up, delete the folder manually: rm -rf .submission/"
        )
        raise SystemExit(1)

    # Get current branch
    current_branch = ctx.git.get_current_branch(repo.root)
    if current_branch is None:
        user_output(click.style("Error: ", fg="red") + "Not on a branch (detached HEAD)")
        raise SystemExit(1)

    user_output(f"Submitting plan from: {click.style(str(ctx.cwd), fg='yellow')}")
    user_output(f"Current branch: {click.style(current_branch, fg='cyan')}")
    user_output("")

    if dry_run:
        dry_run_msg = click.style("(dry run)", fg="bright_black")
        user_output(f"{dry_run_msg} Would copy .plan/ to .submission/")
        user_output(f"{dry_run_msg} Would commit and push .submission/")
        user_output(f"{dry_run_msg} Would trigger GitHub Actions workflow")
        return

    # Copy .plan/ to .submission/
    user_output("Copying .plan/ to .submission/...")
    copy_plan_to_submission(ctx.cwd)

    # Stage and commit .submission/ folder
    user_output("Committing .submission/ folder...")
    subprocess.run(
        ["git", "add", ".submission/"],
        cwd=ctx.cwd,
        check=True,
        capture_output=True,
    )

    subprocess.run(
        ["git", "commit", "-m", "Submit plan for AI implementation\n\n"
         "This commit signals GitHub Actions to begin implementation."],
        cwd=ctx.cwd,
        check=True,
        capture_output=True,
    )

    # Push branch
    user_output("Pushing branch...")
    subprocess.run(
        ["git", "push", "-u", "origin", current_branch],
        cwd=ctx.cwd,
        check=True,
        capture_output=True,
    )

    # Trigger workflow
    workflow = "implement-plan.yml"
    user_output(f"Triggering workflow: {click.style(workflow, fg='cyan')}")
    ctx.github.trigger_workflow(
        repo.root,
        workflow,
        {"branch-name": current_branch},
    )

    user_output("")
    user_output(click.style("✓", fg="green") + " Submission complete!")
    user_output("")
    user_output("Monitor progress:")
    user_output("  gh run list --workflow=implement-plan.yml")
    user_output("  gh run watch")
```

**Key features:**
- Checks for .plan/ folder existence
- Checks for existing .submission/ (error if present)
- Copies .plan/ to .submission/
- Commits with clear message
- Pushes to origin
- Triggers workflow with branch name
- Clear user feedback

**Files affected:**
- `src/erk/cli/commands/submit.py` (complete rewrite, ~110 lines)

---

### Phase 3: Update `/erk:implement-plan` to Handle CI Iteratively

**Goal:** Modify the slash command to detect .submission/ and run CI fixes in a loop

**Modify `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/implement-plan.md`:**

Add new section after implementation completes:

```markdown
## Step 6: Run CI and Fix Issues Iteratively (if .submission/ present)

**CRITICAL: Only run this step if working in a .submission/ folder (not .plan/)**

Check if current directory contains `.submission/` folder:
- If yes: This is a remote submission, run iterative CI
- If no: This is local implementation, skip CI loop

**Iterative CI Process (max 5 attempts):**

For each attempt:
1. Run the fast CI checks: `/fast-ci` (unit tests + pyright)
2. If all checks pass: Break out of loop, proceed to cleanup
3. If checks fail: Read the error output carefully
4. Analyze the failures and fix them
5. Increment attempt counter
6. If max attempts reached: Exit with error, DO NOT proceed

**After CI passes (or if .plan/ folder):**

If in .submission/ folder:
1. Delete .submission/ folder: `rm -rf .submission/`
2. Stage deletion: `git add .submission/`
3. Commit: `git commit -m "Clean up submission artifacts after implementation"`
4. Push: `git push`

If in .plan/ folder:
1. DO NOT delete .plan/
2. DO NOT auto-commit
3. Leave changes for user review

## Step 7: Create/Update PR (if .submission/ present)

**Only if .submission/ was present:**

Use gh CLI to create or update PR:
```bash
gh pr create --fill --label "ai-generated" || gh pr edit --add-label "ai-generated"
```
```

**Key additions:**
- Detect .submission/ vs .plan/ folder
- Run /fast-ci in loop (up to 5 attempts)
- Fix issues between attempts
- Only auto-cleanup and create PR for .submission/
- Leave .plan/ untouched for local work

**Files affected:**
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/implement-plan.md` (+60 lines)

---

### Phase 4: Update Tests for `erk submit`

**Goal:** Comprehensive test coverage for new submit behavior

**Rewrite `tests/commands/test_submit.py`:**

```python
"""Tests for erk submit command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import submit_cmd
from erk.core.repo_discovery import RepoContext
from tests.fakes.context import create_test_context
from tests.fakes.git import FakeGit
from tests.fakes.github import FakeGitHub


def test_submit_errors_without_plan_folder(tmp_path: Path) -> None:
    """Test submit shows error when no .plan/ folder exists."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    fake_git = FakeGit(current_branches={repo_root: "feature-branch"})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, [], obj=ctx)

    assert result.exit_code == 1
    assert "No .plan/ folder found" in result.output


def test_submit_dry_run_shows_operations(tmp_path: Path) -> None:
    """Test dry-run shows what would happen."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create .plan/ folder
    plan_dir = repo_root / ".plan"
    plan_dir.mkdir()
    (plan_dir / "plan.md").write_text("# Plan", encoding="utf-8")

    fake_git = FakeGit(current_branches={repo_root: "feature-branch"})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["--dry-run"], obj=ctx)

    assert result.exit_code == 0
    assert "Would copy .plan/ to .submission/" in result.output
    assert "Would commit and push .submission/" in result.output
    assert "Would trigger GitHub Actions workflow" in result.output
    assert len(fake_github.triggered_workflows) == 0


def test_submit_errors_with_existing_submission(tmp_path: Path) -> None:
    """Test submit errors when .submission/ already exists."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create both .plan/ and .submission/
    (repo_root / ".plan").mkdir()
    (repo_root / ".submission").mkdir()

    fake_git = FakeGit(current_branches={repo_root: "feature-branch"})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, [], obj=ctx)

    assert result.exit_code == 1
    assert ".submission/ folder already exists" in result.output


def test_submit_errors_on_detached_head(tmp_path: Path) -> None:
    """Test submit errors when in detached HEAD state."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create .plan/ folder
    (repo_root / ".plan").mkdir()

    # No current branch (detached HEAD)
    fake_git = FakeGit(current_branches={repo_root: None})
    fake_github = FakeGitHub()
    repo_dir = tmp_path / ".erk" / "repos" / "test-repo"
    repo = RepoContext(
        root=repo_root,
        repo_name="test-repo",
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
    )
    ctx = create_test_context(cwd=repo_root, git=fake_git, github=fake_github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(submit_cmd, [], obj=ctx)

    assert result.exit_code == 1
    assert "Not on a branch" in result.output
```

**Files affected:**
- `tests/commands/test_submit.py` (rewrite, ~140 lines)
- `tests/core/test_plan_folder.py` (add submission tests, +50 lines)

---

### Phase 5: Update GitHub Actions Workflow

**Goal:** Simplify workflow - just run /erk:implement-plan with skip permissions

**Modify `.github/workflows/implement-plan.yml`:**

```yaml
name: Implement Plan

on:
  workflow_dispatch:
    inputs:
      branch-name:
        description: 'Branch name to implement'
        required: true
  push:
    branches:
      - '**'
    paths:
      - '.submission/**'

jobs:
  implement:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.branch-name || github.ref }}
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Check for submission
        id: check_submission
        run: |
          if [ -d ".submission" ]; then
            echo "has_submission=true" >> $GITHUB_OUTPUT
          else
            echo "has_submission=false" >> $GITHUB_OUTPUT
          fi

      - name: Setup environment
        if: steps.check_submission.outputs.has_submission == 'true'
        run: |
          # Install uv
          curl -LsSf https://astral.sh/uv/install.sh | sh
          source $HOME/.cargo/env

          # Install erk
          cd $GITHUB_WORKSPACE
          uv tool install --from . erk

          # Install Claude Code
          npm install -g @anthropic-ai/claude-code

          # Install erk kit for Claude Code
          dot-agent kit install erk

      - name: Configure git
        if: steps.check_submission.outputs.has_submission == 'true'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Run implementation with CI loop
        if: steps.check_submission.outputs.has_submission == 'true'
        run: |
          dot-agent command "/erk:implement-plan" \
            --permission-mode dangerouslySkipPermissions
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Key simplifications:**
- No manual CI loop in workflow
- Just run `/erk:implement-plan` with skip permissions
- The command handles everything:
  - Implementation
  - Iterative CI fixing
  - Cleanup of .submission/
  - PR creation
- Git is pre-configured for the bot to commit

**Files affected:**
- `.github/workflows/implement-plan.yml` (simplify, ~80 lines total)

---

### Phase 6: Update Documentation

**Goal:** Document the new submission workflow

**Update `AGENTS.md`:**

Add section explaining the .submission/ protocol:

```markdown
## .submission/ Folder Protocol

**Purpose:** Signal for remote AI implementation via GitHub Actions

**Workflow:**
1. Create worktree with `/erk:create-planned-wt` (creates .plan/)
2. Run `erk submit` to copy .plan/ to .submission/
3. GitHub Actions detects .submission/ and runs implementation
4. .submission/ is auto-deleted after completion

**Key differences from .plan/:**
- `.plan/` = Local implementation tracking (NOT git-tracked)
- `.submission/` = Remote submission signal (git-tracked, ephemeral)

**Important:** `.submission/` folders should NOT be added to .gitignore. They are meant to be committed as a signal to GitHub Actions.
```

**Files affected:**
- `AGENTS.md` (add ~30 lines)
- `.agent/kits/erk/registry-entry.md` (update command list)

---

## Complete User Workflow

**After implementation, the full workflow is:**

### 1. Create Plan
```bash
/erk:persist-plan  # Save plan to repo root as <name>-plan.md
```

### 2. Create Worktree
```bash
/erk:create-planned-wt  # Creates worktree with .plan/ folder
```

### 3. Submit for Remote Implementation
```bash
erk checkout <branch-name>
erk submit  # Copies .plan/ to .submission/, commits, pushes, triggers
```

### 4. GitHub Actions Automatically
- Detects .submission/ folder in push
- Runs `/erk:implement-plan` with `--dangerously-skip-permissions`
- Command detects .submission/ and runs CI loop internally:
  - Implement code according to plan
  - Run `/fast-ci` (unit tests + pyright)
  - Fix issues if CI fails
  - Repeat up to 5 times
  - Delete .submission/ folder
  - Commit and push
  - Create/update PR with `ai-generated` label

### 5. Result
- ✅ Clean PR with implemented code
- ✅ No .submission/ artifacts
- ✅ Original .plan/ unchanged in worktree
- ✅ CI passing
- ✅ PR ready for human review

---

## Success Criteria

✅ `erk submit` only requires .plan/ folder to exist
✅ .submission/ automatically created and committed
✅ GitHub Actions triggered automatically on push
✅ Implementation runs without permission prompts
✅ `/erk:implement-plan` handles CI fixes internally
✅ .submission/ cleaned up after completion
✅ .plan/ remains for reference/resubmission

---

## Scope Summary

### Modified Files

| File | Change Type | Lines |
|------|-------------|-------|
| `src/erk/core/plan_folder.py` | Add functions | +40 |
| `src/erk/cli/commands/submit.py` | Complete rewrite | ~110 |
| `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/implement-plan.md` | Add CI loop section | +60 |
| `tests/commands/test_submit.py` | Complete rewrite | ~140 |
| `tests/core/test_plan_folder.py` | Add submission tests | +50 |
| `.github/workflows/implement-plan.yml` | Simplify | ~80 total |
| `AGENTS.md` | Add documentation | +30 |

**Total:** ~510 lines of code
**Tests:** 9 new test cases

---

## Implementation Order

### Recommended Sequence

1. **Phase 1** - Add utilities (safe, isolated)
   - No dependencies on other changes
   - Can be tested in isolation

2. **Phase 4** - Write tests (TDD approach)
   - Define expected behavior before implementation
   - Tests guide the implementation

3. **Phase 2** - Implement submit command (tests guide)
   - Tests already define expected behavior
   - Can verify correctness immediately

4. **Phase 3** - Update /erk:implement-plan command (add CI loop)
   - Slash command modification
   - Can be tested manually before CI

5. **Phase 5** - Update GitHub Actions (after local testing)
   - Only deploy after everything works locally
   - Test with workflow_dispatch first

6. **Phase 6** - Update docs (after everything works)
   - Document the working system
   - Include examples from testing

---

## Risk Mitigation

### Risk 1: .submission/ conflicts with existing work
- **Impact:** User unable to submit
- **Mitigation:** Error if .submission/ already exists
- **Recovery:** Manual cleanup with `rm -rf .submission/`

### Risk 2: CI loop never terminates
- **Impact:** Wastes API calls, delays PR creation
- **Mitigation:** Max 5 attempts, then fail
- **Recovery:** Manual fixes, then re-submit

### Risk 3: Incomplete cleanup after failure
- **Impact:** .submission/ folder left in repository
- **Mitigation:** Make deletion step idempotent
- **Recovery:** User can manually delete or re-run

### Risk 4: GitHub Actions not triggering on push
- **Impact:** No automatic implementation
- **Mitigation:** Test with real push before rollout
- **Recovery:** Manual workflow_dispatch trigger

### Risk 5: Breaking existing .plan/ workflow
- **Impact:** Users unable to do local implementation
- **Mitigation:** Touch nothing in existing commands
- **Recovery:** Parallel workflows, no breaking changes

---

## Testing Strategy

### Unit Tests (tests/core/test_plan_folder.py)
- `test_copy_plan_to_submission()` - Happy path
- `test_copy_plan_to_submission_no_plan()` - Missing .plan/ error
- `test_copy_plan_to_submission_already_exists()` - Existing .submission/ error
- `test_get_submission_path()` - Detection works
- `test_remove_submission_folder()` - Cleanup works

### Command Tests (tests/commands/test_submit.py)
- `test_submit_errors_without_plan_folder()` - Error when no .plan/
- `test_submit_dry_run_shows_operations()` - Dry run output
- `test_submit_errors_with_existing_submission()` - Error on conflict
- `test_submit_errors_on_detached_head()` - Error on detached HEAD

### Integration Tests (Manual)
1. Create worktree with `/erk:create-planned-wt`
2. Run `erk submit --dry-run` (verify output)
3. Run `erk submit` (verify .submission/ created)
4. Verify commit message
5. Verify push succeeded
6. Trigger workflow manually with `gh workflow run`
7. Verify .submission/ deleted after completion

---

## Open Questions

### Question 1: Should .submission/ be tracked in git?
**Decision:** Yes, required for GitHub Actions to detect it
**Rationale:** Push trigger requires file to be in commit

### Question 2: Should we support manual cleanup command?
**Suggestion:** Add `erk clean-submission` command for manual cleanup
**Rationale:** Useful when GitHub Actions fails

### Question 3: Should submission worktrees have special naming?
**Suggestion:** Add `-submission` suffix to worktree names
**Rationale:** Makes it clear this is for remote work

### Question 4: What if /fast-ci doesn't exist?
**Decision:** Document that /fast-ci must be available
**Rationale:** Required for CI loop to work

### Question 5: Should we log CI attempts?
**Suggestion:** Log each CI attempt to a file in .submission/
**Rationale:** Helps debug if max attempts reached

---

## Future Enhancements

### Enhancement 1: Submission Status Command
```bash
erk submission status  # Show current submission state
```
- Check if .submission/ exists
- Show GitHub Actions run status
- Show PR status if created

### Enhancement 2: Submission History
Track all submissions in `.erk/submissions.json`:
- Timestamp
- Branch name
- Plan file used
- Success/failure status
- PR URL

### Enhancement 3: Multi-Plan Support
Allow submitting specific plans:
```bash
erk submit --plan other-feature-plan.md
```

### Enhancement 4: Submission Rollback
```bash
erk submission rollback  # Delete .submission/, reset branch
```

---

## Notes

- This implementation keeps the existing `.plan/` workflow completely unchanged
- `.plan/` and `.submission/` can coexist - they serve different purposes
- The protocol is explicit: presence of `.submission/` = "please implement this"
- No magic detection or implicit behavior - everything is opt-in
- CI loop is self-contained within `/erk:implement-plan` command
- GitHub Actions workflow is simple - just run one command
