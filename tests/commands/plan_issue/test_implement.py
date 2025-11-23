"""Tests for plan-issue implement command."""

from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.plan_issue import plan_issue_group
from erk.core.plan_issue_store import FakePlanIssueStore, PlanIssue, PlanIssueState
from tests.fakes.git import FakeGit
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def _create_sample_plan_issue(issue_number: str = "42") -> PlanIssue:
    """Create a sample plan issue for testing."""
    return PlanIssue(
        plan_issue_identifier=issue_number,
        title="Add Authentication Feature",
        body="# Implementation Plan\n\nAdd user authentication to the application.",
        state=PlanIssueState.OPEN,
        url=f"https://github.com/owner/repo/issues/{issue_number}",
        labels=["erk-plan", "enhancement"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )


def test_implement_creates_worktree_with_auto_generated_name() -> None:
    """Test successful worktree creation with auto-generated name from issue title."""
    # Arrange
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        # Act
        result = runner.invoke(plan_issue_group, ["implement", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Created worktree" in result.output
        assert "add-authentication-feature" in result.output

        # Verify worktree was created via git
        assert len(git.added_worktrees) == 1

        # Verify .impl/ folder exists with plan content
        worktree_paths = [wt[0] for wt in git.added_worktrees]
        assert len(worktree_paths) == 1
        impl_path = worktree_paths[0] / ".impl"
        assert impl_path.exists()
        assert (impl_path / "plan.md").exists()
        assert (impl_path / "progress.md").exists()
        assert (impl_path / "issue.json").exists()

        # Verify issue.json content
        issue_json_path = impl_path / "issue.json"
        issue_json_content = issue_json_path.read_text(encoding="utf-8")
        assert '"issue_number": 42' in issue_json_content
        assert "github.com/owner/repo/issues/42" in issue_json_content


def test_implement_with_custom_worktree_name() -> None:
    """Test worktree creation with custom name override."""
    # Arrange
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        # Act
        result = runner.invoke(
            plan_issue_group, ["implement", "42", "--worktree-name", "my-custom-feature"], obj=ctx
        )

        # Assert
        assert result.exit_code == 0
        assert "Created worktree" in result.output
        assert "my-custom-feature" in result.output

        # Verify worktree uses custom name
        assert len(git.added_worktrees) == 1
        worktree_path, branch_name = git.added_worktrees[0]
        assert "my-custom-feature" in str(worktree_path)


def test_implement_fails_without_erk_plan_label() -> None:
    """Test that command fails when issue doesn't have erk-plan label."""
    # Arrange
    plan_issue = PlanIssue(
        plan_issue_identifier="42",
        title="Regular Issue",
        body="Not a plan issue",
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["bug"],  # Missing "erk-plan" label
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        # Act
        result = runner.invoke(plan_issue_group, ["implement", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "erk-plan" in result.output
        assert len(git.added_worktrees) == 0  # No worktree created


def test_implement_fails_when_issue_not_found() -> None:
    """Test that command fails when issue doesn't exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={})  # Empty store
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        # Act
        result = runner.invoke(plan_issue_group, ["implement", "999"], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert len(git.added_worktrees) == 0


def test_implement_dry_run_mode_no_side_effects() -> None:
    """Test dry-run mode prints actions without creating worktree."""
    # Arrange
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        # Act
        result = runner.invoke(plan_issue_group, ["implement", "42", "--dry-run"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Would create worktree" in result.output
        assert "Add Authentication Feature" in result.output
        assert 'claude --permission-mode acceptEdits "/erk:implement-plan"' in result.output

        # Verify NO worktree created
        assert len(git.added_worktrees) == 0


def test_implement_with_closed_issue_shows_warning() -> None:
    """Test that closed issue shows warning but proceeds."""
    # Arrange
    plan_issue = PlanIssue(
        plan_issue_identifier="42",
        title="Closed Plan Issue",
        body="# Plan\n\nImplement feature",
        state=PlanIssueState.CLOSED,  # Issue is closed
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        # Act
        result = runner.invoke(plan_issue_group, ["implement", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0  # Still succeeds
        assert "Warning" in result.output
        assert "CLOSED" in result.output
        assert "Proceeding anyway" in result.output
        assert len(git.added_worktrees) == 1  # Worktree still created


def test_implement_fails_when_custom_branch_already_exists() -> None:
    """Test that command fails when custom worktree name conflicts with existing branch."""
    # Arrange
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Pre-create branch that would conflict with custom name
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={
                env.cwd: ["main", "my-custom-feature"]  # Existing branch
            },
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        # Act - try to use custom name that already exists as a branch
        result = runner.invoke(
            plan_issue_group, ["implement", "42", "--worktree-name", "my-custom-feature"], obj=ctx
        )

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "already exists" in result.output
        assert len(git.added_worktrees) == 0


def test_implement_script_mode_generates_activation_script() -> None:
    """Test that --script flag generates activation script with Claude command."""
    # Arrange
    plan_issue = _create_sample_plan_issue()

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        # Act
        result = runner.invoke(plan_issue_group, ["implement", "42", "--script"], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify script path output (shell integration expects path on stdout)
        assert result.output.startswith("/")
        assert ".sh" in result.output

        # Verify worktree was still created
        assert len(git.added_worktrees) == 1


def test_implement_with_minimal_issue_fields() -> None:
    """Test with minimal issue (no assignees, no body)."""
    # Arrange
    plan_issue = PlanIssue(
        plan_issue_identifier="1",
        title="Minimal Plan",
        body="",  # Empty body
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/1",
        labels=["erk-plan"],
        assignees=[],  # No assignees
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"1": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        # Act
        result = runner.invoke(plan_issue_group, ["implement", "1"], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Created worktree" in result.output
        assert len(git.added_worktrees) == 1


def test_implement_saves_plan_content_to_impl_folder() -> None:
    """Test that issue body is saved as plan.md in .impl/ folder."""
    # Arrange
    plan_body = "# Implementation Plan\n\nStep 1: Do this\nStep 2: Do that"
    plan_issue = PlanIssue(
        plan_issue_identifier="42",
        title="Test Plan",
        body=plan_body,
        state=PlanIssueState.OPEN,
        url="https://github.com/owner/repo/issues/42",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            default_branches={env.cwd: "main"},
        )
        store = FakePlanIssueStore(plan_issues={"42": plan_issue})
        ctx = build_workspace_test_context(env, git=git, plan_issue_store=store)

        # Act
        result = runner.invoke(plan_issue_group, ["implement", "42"], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify plan.md contains issue body
        worktree_path = git.added_worktrees[0][0]
        plan_md_path = worktree_path / ".impl" / "plan.md"
        assert plan_md_path.exists()
        plan_content = plan_md_path.read_text(encoding="utf-8")
        assert "Step 1: Do this" in plan_content
        assert "Step 2: Do that" in plan_content
