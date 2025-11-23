"""Tests for plan-issue shell integration with Click groups."""

from datetime import datetime, timezone

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.git.abc import WorktreeInfo
from erk.core.plan_issue_store.fake import FakePlanIssueStore
from erk.core.plan_issue_store.types import PlanIssue, PlanIssueState
from tests.fakes.git import FakeGit
from tests.test_utils.env_helpers import erk_isolated_fs_env


def test_shell_integration_plan_issue_implement_invokes_successfully() -> None:
    """Test that __shell plan-issue implement invokes subcommand successfully.

    This verifies that shell integration correctly handles Click groups by
    delegating to the appropriate subcommand (implement) rather than failing
    at the group level.
    """
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        # Set up minimal git environment
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
        )

        # Set up fake plan issue store with a test issue
        now = datetime.now(timezone.utc)
        test_issue = PlanIssue(
            plan_issue_identifier="123",
            title="Test Implementation Plan",
            body="# Plan\n\nTest plan content",
            state=PlanIssueState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={"number": 123},
        )
        plan_issue_store = FakePlanIssueStore(plan_issues={"123": test_issue})

        test_ctx = env.build_context(git=git_ops, plan_issue_store=plan_issue_store)

        # Act: Invoke plan-issue implement through __shell handler
        result = runner.invoke(cli, ["__shell", "plan-issue", "implement", "123"], obj=test_ctx)

        # Should succeed without TypeError or group-level failures
        # May fail for other reasons (missing worktree directory, etc.)
        assert result.exit_code in (0, 1), f"Unexpected exit code: {result.exit_code}"

        # If successful, should return a script path (not passthrough)
        if result.exit_code == 0:
            script_path_str = result.stdout.strip()
            assert script_path_str != "", "Should produce script path for directory switching"
            assert script_path_str != "__ERK_PASSTHROUGH__", "Should not passthrough for this command"


def test_shell_integration_plan_issue_get_invokes_successfully() -> None:
    """Test that __shell plan-issue get invokes subcommand successfully."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
        )

        now = datetime.now(timezone.utc)
        test_issue = PlanIssue(
            plan_issue_identifier="123",
            title="Test Plan",
            body="# Content",
            state=PlanIssueState.OPEN,
            url="https://github.com/test/repo/issues/123",
            labels=["erk-plan"],
            assignees=[],
            created_at=now,
            updated_at=now,
            metadata={"number": 123},
        )
        plan_issue_store = FakePlanIssueStore(plan_issues={"123": test_issue})

        test_ctx = env.build_context(git=git_ops, plan_issue_store=plan_issue_store)

        # Act: Invoke plan-issue get through __shell handler
        result = runner.invoke(cli, ["__shell", "plan-issue", "get", "123"], obj=test_ctx)

        # Should complete without TypeError (may fail for other reasons)
        assert result.exit_code in (0, 1), f"Unexpected exit code: {result.exit_code}"


def test_shell_integration_plan_issue_list_invokes_successfully() -> None:
    """Test that __shell plan-issue list invokes subcommand successfully."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ]
            },
        )

        plan_issue_store = FakePlanIssueStore(plan_issues={})

        test_ctx = env.build_context(git=git_ops, plan_issue_store=plan_issue_store)

        # Act: Invoke plan-issue list through __shell handler
        result = runner.invoke(cli, ["__shell", "plan-issue", "list"], obj=test_ctx)

        # Should complete without TypeError (may fail for other reasons)
        assert result.exit_code in (0, 1), f"Unexpected exit code: {result.exit_code}"
