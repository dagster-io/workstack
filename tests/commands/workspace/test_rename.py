"""Tests for workstack rename command.

This file tests the rename command which renames a worktree workspace.
"""

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.gitops import DryRunGitOps
from workstack.core.global_config import GlobalConfig


def test_rename_successful() -> None:
    """Test successful rename of a worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create old worktree
        old_wt = env.workstacks_root / "old-name"
        old_wt.mkdir(parents=True)
        (old_wt / ".env").write_text(
            'WORKTREE_PATH="/old/path"\nWORKTREE_NAME="old-name"\n', encoding="utf-8"
        )

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=GlobalConfig(
                workstacks_root=env.workstacks_root,
                use_graphite=False,
                shell_setup_complete=False,
                show_pr_info=True,
                show_pr_checks=False,
            ),
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=env.cwd,
            dry_run=False,
        )
        result = runner.invoke(cli, ["rename", "old-name", "new-name"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "new-name" in result.output


def test_rename_old_worktree_not_found() -> None:
    """Test rename fails when old worktree doesn't exist."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=GlobalConfig(
                workstacks_root=env.workstacks_root,
                use_graphite=False,
                shell_setup_complete=False,
                show_pr_info=True,
                show_pr_checks=False,
            ),
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=env.cwd,
            dry_run=False,
        )
        result = runner.invoke(cli, ["rename", "nonexistent", "new-name"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Worktree not found" in result.output


def test_rename_new_name_already_exists() -> None:
    """Test rename fails when new name already exists."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create two worktrees
        old_wt = env.workstacks_root / "old-name"
        old_wt.mkdir(parents=True)
        existing_wt = env.workstacks_root / "existing"
        existing_wt.mkdir(parents=True)

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=GlobalConfig(
                workstacks_root=env.workstacks_root,
                use_graphite=False,
                shell_setup_complete=False,
                show_pr_info=True,
                show_pr_checks=False,
            ),
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=env.cwd,
            dry_run=False,
        )
        result = runner.invoke(cli, ["rename", "old-name", "existing"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists" in result.output


def test_rename_with_graphite_enabled() -> None:
    """Test rename with Graphite integration enabled."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktree
        old_wt = env.workstacks_root / "old-branch"
        old_wt.mkdir(parents=True)

        # Enable Graphite
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=GlobalConfig(
                workstacks_root=env.workstacks_root,
                use_graphite=True,
                shell_setup_complete=False,
                show_pr_info=True,
                show_pr_checks=False,
            ),
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["rename", "old-branch", "new-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "new-branch" in result.output


def test_rename_dry_run() -> None:
    """Test rename in dry-run mode doesn't actually rename."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktree
        old_wt = env.workstacks_root / "old-name"
        old_wt.mkdir(parents=True)

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        git_ops = DryRunGitOps(git_ops)
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=GlobalConfig(
                workstacks_root=env.workstacks_root,
                use_graphite=False,
                shell_setup_complete=False,
                show_pr_info=True,
                show_pr_checks=False,
            ),
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=env.cwd,
            dry_run=True,
        )
        result = runner.invoke(cli, ["rename", "old-name", "new-name"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Would rename" in result.output or "DRY RUN" in result.output
