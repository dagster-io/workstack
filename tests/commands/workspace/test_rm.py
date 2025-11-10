"""Tests for workstack rm command.

This file tests the rm command which removes a worktree workspace.
"""

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.gitops import DryRunGitOps, WorktreeInfo
from workstack.core.global_config import GlobalConfig
from workstack.core.graphite_ops import BranchMetadata


def _create_test_context(env, use_graphite: bool = False, dry_run: bool = False):
    """Helper to create test context for rm command tests.

    Args:
        env: Simulated workstack environment
        use_graphite: Whether to enable Graphite integration
        dry_run: Whether to use dry-run mode

    Returns:
        WorkstackContext configured for testing
    """
    git_ops = FakeGitOps(git_common_dirs={env.root_worktree: env.git_dir})

    if dry_run:
        git_ops = DryRunGitOps(git_ops)

    return WorkstackContext.for_test(
        git_ops=git_ops,
        global_config=GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=use_graphite,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        ),
        github_ops=FakeGitHubOps(),
        graphite_ops=FakeGraphiteOps(),
        shell_ops=FakeShellOps(),
        cwd=env.cwd,
        dry_run=dry_run,
    )


def test_rm_force_removes_directory() -> None:
    """Test that rm with --force flag removes the worktree directory."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        repo_name = env.root_worktree.name
        wt = env.workstacks_root / repo_name / "foo"
        wt.mkdir(parents=True)
        (wt / "hello.txt").write_text("hello world", encoding="utf-8")

        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["rm", "foo", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert result.output.strip().endswith(str(wt))
        assert not wt.exists()


def test_rm_prompts_and_aborts_on_no() -> None:
    """Test that rm prompts for confirmation and aborts when user says no."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        repo_name = env.root_worktree.name
        wt = env.workstacks_root / repo_name / "bar"
        wt.mkdir(parents=True)

        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["rm", "bar"], input="n\n", obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert wt.exists()  # Should not remove when user says 'n'


def test_rm_dry_run_does_not_delete() -> None:
    """Test that dry-run mode prints actions but doesn't delete."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        repo_name = env.root_worktree.name
        wt = env.workstacks_root / repo_name / "test-stack"
        wt.mkdir(parents=True)
        (wt / "file.txt").write_text("test content", encoding="utf-8")

        test_ctx = _create_test_context(env, dry_run=True)
        result = runner.invoke(cli, ["rm", "test-stack", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert "Would run: git worktree remove" in result.output
        assert "Would delete directory" in result.output
        assert wt.exists()  # Directory should still exist
        assert (wt / "file.txt").exists()


def test_rm_dry_run_with_delete_stack() -> None:
    """Test dry-run with --delete-stack flag prints but doesn't delete branches."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        repo_name = env.root_worktree.name
        wt = env.workstacks_root / repo_name / "test-stack"
        wt.mkdir(parents=True)

        # Build fake git ops with worktree info
        fake_git_ops = FakeGitOps(
            worktrees={env.root_worktree: [WorktreeInfo(path=wt, branch="feature-2")]},
            git_common_dirs={env.root_worktree: env.git_dir},
        )
        git_ops = DryRunGitOps(fake_git_ops)

        # Build graphite ops with branch metadata
        branches = {
            "main": BranchMetadata.trunk("main", children=["feature-1"]),
            "feature-1": BranchMetadata.branch("feature-1", "main", children=["feature-2"]),
            "feature-2": BranchMetadata.branch("feature-2", "feature-1"),
        }

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
            graphite_ops=FakeGraphiteOps(branches=branches),
            shell_ops=FakeShellOps(),
            cwd=env.cwd,
            dry_run=True,
        )

        result = runner.invoke(cli, ["rm", "test-stack", "-f", "-s"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert "Would run: gt delete" in result.output
        assert len(fake_git_ops.deleted_branches) == 0  # No actual deletion
        assert wt.exists()


def test_rm_rejects_dot_dot() -> None:
    """Test that rm rejects '..' as a worktree name."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["rm", "..", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot remove '..'" in result.output
        assert "directory references not allowed" in result.output


def test_rm_rejects_root_slash() -> None:
    """Test that rm rejects '/' as a worktree name."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["rm", "/", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot remove '/'" in result.output
        assert "absolute paths not allowed" in result.output


def test_rm_rejects_path_with_slash() -> None:
    """Test that rm rejects worktree names containing path separators."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["rm", "foo/bar", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot remove 'foo/bar'" in result.output
        assert "path separators not allowed" in result.output


def test_rm_rejects_root_name() -> None:
    """Test that rm rejects 'root' as a worktree name."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["rm", "root", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot remove 'root'" in result.output
        assert "root worktree name not allowed" in result.output
