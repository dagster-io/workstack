"""Tests for workstack rename command.

This file tests the rename command which renames a worktree workspace.
"""

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import pure_workstack_env
from workstack.cli.cli import cli
from workstack.core.gitops import DryRunGitOps
from workstack.core.repo_discovery import RepoContext


def test_rename_successful() -> None:
    """Test successful rename of a worktree."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Construct worktree paths
        work_dir = env.workstacks_root / env.cwd.name
        old_wt = work_dir / "old-name"
        work_dir / "new-name"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )
        test_ctx = env.build_context(
            git_ops=git_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            repo=repo,
            dry_run=False,
            existing_paths={old_wt},
        )
        result = runner.invoke(cli, ["rename", "old-name", "new-name"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "new-name" in result.output


def test_rename_old_worktree_not_found() -> None:
    """Test rename fails when old worktree doesn't exist."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = env.build_context(
            git_ops=git_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )
        result = runner.invoke(cli, ["rename", "nonexistent", "new-name"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Worktree not found" in result.output


def test_rename_new_name_already_exists() -> None:
    """Test rename fails when new name already exists."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Construct worktree paths
        work_dir = env.workstacks_root / env.cwd.name
        old_wt = work_dir / "old-name"
        existing_wt = work_dir / "existing"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )
        test_ctx = env.build_context(
            git_ops=git_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            repo=repo,
            dry_run=False,
            existing_paths={old_wt, existing_wt},
        )
        result = runner.invoke(cli, ["rename", "old-name", "existing"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists" in result.output


def test_rename_with_graphite_enabled() -> None:
    """Test rename with Graphite integration enabled."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Construct worktree paths
        work_dir = env.workstacks_root / env.cwd.name
        old_wt = work_dir / "old-branch"

        # Enable Graphite
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )
        test_ctx = env.build_context(
            use_graphite=True,
            git_ops=git_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            repo=repo,
            dry_run=False,
            existing_paths={old_wt},
        )

        result = runner.invoke(cli, ["rename", "old-branch", "new-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "new-branch" in result.output


def test_rename_dry_run() -> None:
    """Test rename in dry-run mode doesn't actually rename."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Construct worktree paths
        work_dir = env.workstacks_root / env.cwd.name
        old_wt = work_dir / "old-name"

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        git_ops = DryRunGitOps(git_ops)
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )
        test_ctx = env.build_context(
            git_ops=git_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            repo=repo,
            dry_run=True,
            existing_paths={old_wt},
        )
        result = runner.invoke(cli, ["rename", "old-name", "new-name"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Would rename" in result.output or "DRY RUN" in result.output
