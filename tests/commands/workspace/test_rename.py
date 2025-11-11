"""Tests for workstack rename command.

This file tests the rename command which renames a worktree workspace.
"""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.gitops import DryRunGitOps
from workstack.core.global_config import GlobalConfig


def _create_test_context(cwd: Path, workstacks_root: Path, dry_run: bool = False):
    """Helper to create a standard test context for workspace commands.

    Args:
        cwd: Current working directory (repo root)
        workstacks_root: Root directory for workstacks
        dry_run: Whether to use dry-run mode

    Returns:
        WorkstackContext configured for testing
    """
    git_dir = cwd / ".git"
    git_ops = FakeGitOps(git_common_dirs={cwd: git_dir})

    if dry_run:
        git_ops = DryRunGitOps(git_ops)

    return WorkstackContext(
        git_ops=git_ops,
        global_config_ops=GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        ),
        github_ops=FakeGitHubOps(),
        graphite_ops=FakeGraphiteOps(),
        shell_ops=FakeShellOps(),
        cwd=Path("/test/default/cwd"),
        dry_run=dry_run,
    )


def test_rename_successful() -> None:
    """Test successful rename of a worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Create git repo and old worktree
        (cwd / ".git").mkdir()
        repo_name = cwd.name
        old_wt = workstacks_root / repo_name / "old-name"
        old_wt.mkdir(parents=True)
        (old_wt / ".env").write_text(
            'WORKTREE_PATH="/old/path"\nWORKTREE_NAME="old-name"\n', encoding="utf-8"
        )

        test_ctx = _create_test_context(cwd, workstacks_root)
        result = runner.invoke(cli, ["rename", "old-name", "new-name"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "new-name" in result.output


def test_rename_old_worktree_not_found() -> None:
    """Test rename fails when old worktree doesn't exist."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Create git repo but not the worktree
        (cwd / ".git").mkdir()
        (workstacks_root / cwd.name).mkdir(parents=True)

        test_ctx = _create_test_context(cwd, workstacks_root)
        result = runner.invoke(cli, ["rename", "nonexistent", "new-name"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Worktree not found" in result.output


def test_rename_new_name_already_exists() -> None:
    """Test rename fails when new name already exists."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Create git repo and two worktrees
        (cwd / ".git").mkdir()
        repo_name = cwd.name
        old_wt = workstacks_root / repo_name / "old-name"
        old_wt.mkdir(parents=True)
        existing_wt = workstacks_root / repo_name / "existing"
        existing_wt.mkdir(parents=True)

        test_ctx = _create_test_context(cwd, workstacks_root)
        result = runner.invoke(cli, ["rename", "old-name", "existing"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists" in result.output


def test_rename_with_graphite_enabled() -> None:
    """Test rename with Graphite integration enabled."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Create git repo and worktree
        (cwd / ".git").mkdir()
        repo_name = cwd.name
        old_wt = workstacks_root / repo_name / "old-branch"
        old_wt.mkdir(parents=True)

        # Enable Graphite
        git_ops = FakeGitOps(git_common_dirs={cwd: cwd / ".git"})
        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=GlobalConfig(
                workstacks_root=workstacks_root,
                use_graphite=True,
                shell_setup_complete=False,
                show_pr_info=True,
                show_pr_checks=False,
            ),
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        result = runner.invoke(cli, ["rename", "old-branch", "new-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "new-branch" in result.output


def test_rename_dry_run() -> None:
    """Test rename in dry-run mode doesn't actually rename."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Create git repo and worktree
        (cwd / ".git").mkdir()
        repo_name = cwd.name
        old_wt = workstacks_root / repo_name / "old-name"
        old_wt.mkdir(parents=True)

        test_ctx = _create_test_context(cwd, workstacks_root, dry_run=True)
        result = runner.invoke(cli, ["rename", "old-name", "new-name"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Would rename" in result.output or "DRY RUN" in result.output
