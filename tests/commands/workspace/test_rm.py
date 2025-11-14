"""Tests for workstack rm command.

This file tests the rm command which removes a worktree workspace.
"""

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import pure_workstack_env
from workstack.cli.cli import cli
from workstack.core.gitops import NoopGitOps, WorktreeInfo
from workstack.core.graphite_ops import BranchMetadata


def _create_test_context(env, use_graphite: bool = False, dry_run: bool = False, **kwargs):
    """Helper to create test context for rm command tests.

    Args:
        env: Pure workstack environment
        use_graphite: Whether to enable Graphite integration
        dry_run: Whether to use dry-run mode
        **kwargs: Additional arguments to pass to env.build_context()

    Returns:
        WorkstackContext configured for testing
    """
    git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})

    if dry_run:
        git_ops = NoopGitOps(git_ops)

    return env.build_context(
        use_graphite=use_graphite,
        git_ops=git_ops,
        github_ops=FakeGitHubOps(),
        graphite_ops=FakeGraphiteOps(),
        shell_ops=FakeShellOps(),
        dry_run=dry_run,
        **kwargs,
    )


def test_rm_force_removes_directory() -> None:
    """Test that rm with --force flag removes the worktree directory."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.workstacks_root / repo_name / "foo"

        test_ctx = _create_test_context(env, existing_paths={wt})
        result = runner.invoke(cli, ["rm", "foo", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert result.output.strip().endswith(str(wt))


def test_rm_prompts_and_aborts_on_no() -> None:
    """Test that rm prompts for confirmation and aborts when user says no."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.workstacks_root / repo_name / "bar"

        test_ctx = _create_test_context(env, existing_paths={wt})
        result = runner.invoke(cli, ["rm", "bar"], input="n\n", obj=test_ctx)

        assert result.exit_code == 0, result.output
        # User aborted, so worktree should still exist (check via git_ops state)
        assert test_ctx.git_ops.path_exists(wt)


def test_rm_dry_run_does_not_delete() -> None:
    """Test that dry-run mode prints actions but doesn't delete."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.workstacks_root / repo_name / "test-stack"

        test_ctx = _create_test_context(env, dry_run=True, existing_paths={wt})
        result = runner.invoke(cli, ["rm", "test-stack", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert "Would run: git worktree remove" in result.output
        assert "Would delete directory" in result.output
        # Directory should still exist (check via git_ops state)
        assert test_ctx.git_ops.path_exists(wt)


def test_rm_dry_run_with_delete_stack() -> None:
    """Test dry-run with --delete-stack flag prints but doesn't delete branches."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.workstacks_root / repo_name / "test-stack"

        # Build fake git ops with worktree info
        fake_git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="feature-2")]},
            git_common_dirs={env.cwd: env.git_dir},
        )
        git_ops = NoopGitOps(fake_git_ops)

        # Build graphite ops with branch metadata
        branches = {
            "main": BranchMetadata.trunk("main", children=["feature-1"]),
            "feature-1": BranchMetadata.branch("feature-1", "main", children=["feature-2"]),
            "feature-2": BranchMetadata.branch("feature-2", "feature-1"),
        }

        test_ctx = env.build_context(
            use_graphite=True,
            git_ops=git_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(branches=branches),
            shell_ops=FakeShellOps(),
            dry_run=True,
            existing_paths={wt},
        )

        result = runner.invoke(cli, ["rm", "test-stack", "-f", "-s"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert "Would run: gt delete" in result.output
        assert len(fake_git_ops.deleted_branches) == 0  # No actual deletion
        # Directory should still exist (check via git_ops state)
        assert test_ctx.git_ops.path_exists(wt)


def test_rm_rejects_dot_dot() -> None:
    """Test that rm rejects '..' as a worktree name."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["rm", "..", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot remove '..'" in result.output
        assert "directory references not allowed" in result.output


def test_rm_rejects_root_slash() -> None:
    """Test that rm rejects '/' as a worktree name."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["rm", "/", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot remove '/'" in result.output
        assert "absolute paths not allowed" in result.output


def test_rm_rejects_path_with_slash() -> None:
    """Test that rm rejects worktree names containing path separators."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["rm", "foo/bar", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot remove 'foo/bar'" in result.output
        assert "path separators not allowed" in result.output


def test_rm_rejects_root_name() -> None:
    """Test that rm rejects 'root' as a worktree name."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["rm", "root", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot remove 'root'" in result.output
        assert "root worktree name not allowed" in result.output


def test_rm_changes_directory_when_in_target_worktree() -> None:
    """Test that rm automatically changes to repo root when user is in target worktree."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        repo_name = env.cwd.name
        wt_path = env.workstacks_root / repo_name / "feature"

        # Set up worktree paths
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt_path, branch="feature", is_root=False),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, wt_path: env.git_dir},
            current_branches={env.cwd: "main", wt_path: "feature"},
        )

        # Build context with cwd set to the worktree being removed
        test_ctx = env.build_context(git_ops=git_ops, cwd=wt_path, existing_paths={wt_path})

        # Execute remove command with --force to skip confirmation
        result = runner.invoke(cli, ["rm", "feature", "-f"], obj=test_ctx)

        # Should succeed
        assert result.exit_code == 0, result.output

        # Should show directory change message
        assert "Changing directory to repository root" in result.output
        assert str(env.cwd) in result.output
