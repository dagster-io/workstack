"""Tests for erk delete command.

This file tests the delete command which removes a worktree workspace.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.git.abc import WorktreeInfo
from erk.core.git.noop import NoopGit
from tests.fakes.git import FakeGit
from tests.fakes.github import FakeGitHub
from tests.fakes.graphite import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_inmem_env


def _create_test_context(env, use_graphite: bool = False, dry_run: bool = False, **kwargs):
    """Helper to create test context for delete command tests.

    Args:
        env: Pure erk environment
        use_graphite: Whether to enable Graphite integration
        dry_run: Whether to use dry-run mode
        **kwargs: Additional arguments to pass to env.build_context()

    Returns:
        ErkContext configured for testing
    """
    git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})

    if dry_run:
        git_ops = NoopGit(git_ops)

    return env.build_context(
        use_graphite=use_graphite,
        git=git_ops,
        github=FakeGitHub(),
        graphite=FakeGraphite(),
        shell=FakeShell(),
        dry_run=dry_run,
        **kwargs,
    )


def test_delete_force_removes_directory() -> None:
    """Test that delete with --force flag removes the worktree directory."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "foo"

        test_ctx = _create_test_context(env, existing_paths={wt})
        result = runner.invoke(cli, ["delete", "foo", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert result.output.strip().endswith(str(wt))


def test_delete_prompts_and_aborts_on_no() -> None:
    """Test that delete prompts for confirmation and aborts when user says no."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "bar"

        test_ctx = _create_test_context(env, existing_paths={wt})
        result = runner.invoke(cli, ["delete", "bar"], input="n\n", obj=test_ctx)

        assert result.exit_code == 0, result.output
        # User aborted, so worktree should still exist (check via git_ops state)
        assert test_ctx.git.path_exists(wt)


def test_delete_dry_run_does_not_delete() -> None:
    """Test that dry-run mode prints actions but doesn't delete."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-stack"

        test_ctx = _create_test_context(env, dry_run=True, existing_paths={wt})
        result = runner.invoke(cli, ["delete", "test-stack", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert "Would run: git worktree remove" in result.output
        assert "Would delete directory" in result.output
        # Directory should still exist (check via git_ops state)
        assert test_ctx.git.path_exists(wt)


def test_delete_dry_run_with_delete_stack() -> None:
    """Test dry-run with --delete-stack flag prints but doesn't delete branches."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-stack"

        # Build fake git ops with worktree info
        fake_git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="feature-2")]},
            git_common_dirs={env.cwd: env.git_dir},
        )
        git_ops = NoopGit(fake_git_ops)

        # Build graphite ops with branch metadata
        branches = {
            "main": BranchMetadata.trunk("main", children=["feature-1"]),
            "feature-1": BranchMetadata.branch("feature-1", "main", children=["feature-2"]),
            "feature-2": BranchMetadata.branch("feature-2", "feature-1"),
        }

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(branches=branches),
            shell=FakeShell(),
            dry_run=True,
            existing_paths={wt},
        )

        result = runner.invoke(cli, ["delete", "test-stack", "-f", "-s"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert "Would run: gt delete" in result.output
        assert len(fake_git_ops.deleted_branches) == 0  # No actual deletion
        # Directory should still exist (check via git_ops state)
        assert test_ctx.git.path_exists(wt)


def test_delete_rejects_dot_dot() -> None:
    """Test that delete rejects '..' as a worktree name."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["delete", "..", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot delete '..'" in result.output
        assert "directory references not allowed" in result.output


def test_delete_rejects_root_slash() -> None:
    """Test that delete rejects '/' as a worktree name."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["delete", "/", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot delete '/'" in result.output
        assert "absolute paths not allowed" in result.output


def test_delete_rejects_path_with_slash() -> None:
    """Test that delete rejects worktree names containing path separators."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["delete", "foo/bar", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot delete 'foo/bar'" in result.output
        assert "path separators not allowed" in result.output


def test_delete_rejects_root_name() -> None:
    """Test that delete rejects 'root' as a worktree name."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        test_ctx = _create_test_context(env)
        result = runner.invoke(cli, ["delete", "root", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error: Cannot delete 'root'" in result.output
        assert "root worktree name not allowed" in result.output


def test_delete_changes_directory_when_in_target_worktree() -> None:
    """Test that delete automatically changes to repo root when user is in target worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt_path = env.erk_root / "repos" / repo_name / "worktrees" / "feature"

        # Set up worktree paths
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt_path, branch="feature", is_root=False),
                ]
            },
            git_common_dirs={env.cwd: env.git_dir, wt_path: env.git_dir},
            current_branches={env.cwd: "main", wt_path: "feature"},
        )

        # Build context with cwd set to the worktree being deleted
        test_ctx = env.build_context(git=git_ops, cwd=wt_path, existing_paths={wt_path})

        # Execute delete command with --force to skip confirmation
        result = runner.invoke(cli, ["delete", "feature", "-f"], obj=test_ctx)

        # Should succeed
        assert result.exit_code == 0, result.output

        # Should show directory change message
        assert "Changing directory to repository root" in result.output
        assert str(env.cwd) in result.output


def test_delete_with_delete_stack_handles_user_decline() -> None:
    """Test that delete -s gracefully handles user declining gt delete prompt."""
    import subprocess

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-stack"

        # Build fake git ops with worktree info and configured exception
        fake_git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="feature-2")]},
            git_common_dirs={env.cwd: env.git_dir},
            delete_branch_raises={
                "feature-1": subprocess.CalledProcessError(
                    returncode=1,
                    cmd=["gt", "delete", "feature-1"],
                    stderr=None,  # User decline doesn't produce stderr
                )
            },
        )

        # Build graphite ops with branch metadata
        branches = {
            "main": BranchMetadata.trunk("main", children=["feature-1"]),
            "feature-1": BranchMetadata.branch("feature-1", "main", children=["feature-2"]),
            "feature-2": BranchMetadata.branch("feature-2", "feature-1"),
        }

        test_ctx = env.build_context(
            use_graphite=True,
            git=fake_git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(branches=branches),
            shell=FakeShell(),
            existing_paths={wt},
        )

        result = runner.invoke(cli, ["delete", "test-stack", "-s"], obj=test_ctx, input="y\n")

        # Should NOT crash - should exit gracefully
        assert result.exit_code == 0, result.output
        assert "Skipped deletion" in result.output or "user declined" in result.output.lower()
        assert "feature-2" not in fake_git_ops.deleted_branches  # Remaining branch not deleted


def test_delete_with_delete_stack_handles_gt_not_found() -> None:
    """Test that delete -s shows installation instructions when gt not found."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        wt = env.erk_root / "repos" / repo_name / "worktrees" / "test-stack"

        fake_git_ops = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=wt, branch="feature-1")]},
            git_common_dirs={env.cwd: env.git_dir},
            delete_branch_raises={
                "feature-1": FileNotFoundError("gt command not found"),
            },
        )

        branches = {
            "main": BranchMetadata.trunk("main", children=["feature-1"]),
            "feature-1": BranchMetadata.branch("feature-1", "main"),
        }

        test_ctx = env.build_context(
            use_graphite=True,
            git=fake_git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(branches=branches),
            shell=FakeShell(),
            existing_paths={wt},
        )

        result = runner.invoke(cli, ["delete", "test-stack", "-f", "-s"], obj=test_ctx)

        assert result.exit_code == 1, result.output
        assert "gt" in result.output.lower()
        assert "install" in result.output.lower() or "brew" in result.output.lower()
