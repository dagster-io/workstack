"""Tests for workstack jump command."""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.gitops import FakeGitOps
from tests.test_utils.env_helpers import pure_workstack_env, simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.gitops import WorktreeInfo
from workstack.core.repo_discovery import RepoContext


def test_jump_to_branch_in_single_worktree() -> None:
    """Test jumping to a branch that is checked out in exactly one worktree.

    This test uses pure_workstack_env() for in-memory testing without filesystem I/O.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name

        # Use sentinel paths (no mkdir() needed in pure mode)
        feature_wt = work_dir / "feature-wt"
        other_wt = work_dir / "other-wt"

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=other_wt, branch="other-feature"),
                    # feature-2 is checked out here
                    WorktreeInfo(path=feature_wt, branch="feature-2"),
                ]
            },
            current_branches={env.cwd: "other-feature"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Create RepoContext to avoid filesystem checks in discover_repo_context
        repo = RepoContext(
            root=env.cwd,
            repo_name="repo",
            workstacks_dir=env.workstacks_root / "repo",
        )

        test_ctx = env.build_context(git_ops=git_ops, repo=repo)

        # Jump to feature-2 which is checked out in feature_wt
        result = runner.invoke(
            cli, ["jump", "feature-2", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Should not checkout (already on the branch)
        assert len(git_ops.checked_out_branches) == 0
        # Should generate activation script (verify in-memory)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(feature_wt) in script_content


def test_jump_to_branch_not_found() -> None:
    """Test jumping to a branch that is not checked out in any worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=work_dir / "feature-1-wt", branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Jump to a branch that doesn't exist
        result = runner.invoke(
            cli, ["jump", "nonexistent-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "is not checked out in any worktree" in result.stderr
        assert "workstack create --from-branch nonexistent-branch" in result.stderr


def test_jump_to_branch_in_stack_but_not_checked_out() -> None:
    """Test that jump fails when branch exists in repo but is not checked out.

    With exact-match behavior, branches that exist in Graphite stacks but are not
    directly checked out should fail with appropriate error message.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name

        wt1 = work_dir / "feature-1-wt"
        wt1.mkdir(parents=True, exist_ok=True)

        # feature-1 is checked out, but feature-base is not
        # (even though it might exist in the stack)
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Jump to feature-base which exists in repo but is not checked out in any worktree
        result = runner.invoke(cli, ["jump", "feature-base"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "is not checked out in any worktree" in result.stderr


def test_jump_works_without_graphite() -> None:
    """Test that jump works without Graphite enabled."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name

        feature_wt = work_dir / "feature-1-wt"
        feature_wt.mkdir(parents=True, exist_ok=True)

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=feature_wt, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Graphite is NOT enabled - jump should still work
        test_ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(
            cli, ["jump", "feature-1", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should succeed - jump no longer requires Graphite
        assert result.exit_code == 0
        script_path = Path(result.stdout.strip())
        assert script_path.exists()


def test_jump_already_on_target_branch() -> None:
    """Test jumping when the target branch is already checked out in a single worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name

        feature_wt = work_dir / "feature-1-wt"
        other_wt = work_dir / "other-wt"
        feature_wt.mkdir(parents=True, exist_ok=True)
        other_wt.mkdir(parents=True, exist_ok=True)

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=other_wt, branch="other-feature"),
                    WorktreeInfo(path=feature_wt, branch="feature-1"),  # Already on feature-1
                ]
            },
            current_branches={env.cwd: "other-feature"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Jump to feature-1 which is already checked out
        result = runner.invoke(
            cli, ["jump", "feature-1", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should succeed without checking out (already on the branch)
        assert result.exit_code == 0
        # Should not have checked out (it's already checked out)
        assert len(git_ops.checked_out_branches) == 0


def test_jump_succeeds_when_branch_exactly_checked_out() -> None:
    """Test that jump succeeds when branch is exactly checked out in a worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name

        feature_wt = work_dir / "feature-wt"
        other_wt = work_dir / "other-wt"
        feature_wt.mkdir(parents=True, exist_ok=True)
        other_wt.mkdir(parents=True, exist_ok=True)

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=other_wt, branch="other-feature"),
                    WorktreeInfo(path=feature_wt, branch="feature-2"),  # feature-2 is checked out
                ]
            },
            current_branches={env.cwd: "other-feature"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Jump to feature-2 which is checked out in feature_wt
        result = runner.invoke(
            cli, ["jump", "feature-2", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        # Should not checkout (already on feature-2)
        assert len(git_ops.checked_out_branches) == 0
        # Should generate activation script
        script_path = Path(result.stdout.strip())
        assert script_path.exists()


def test_jump_with_multiple_worktrees_same_branch() -> None:
    """Test error when multiple worktrees have the same branch checked out.

    This is an edge case that shouldn't happen in normal use (git prevents it),
    but our code should handle it gracefully.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name

        wt1 = work_dir / "wt1"
        wt2 = work_dir / "wt2"
        wt1.mkdir(parents=True, exist_ok=True)
        wt2.mkdir(parents=True, exist_ok=True)

        # Edge case: same branch checked out in multiple worktrees
        # (shouldn't happen in real git, but test our handling)
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=wt1, branch="feature-2"),
                    WorktreeInfo(path=wt2, branch="feature-2"),  # Same branch
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git_ops=git_ops)

        # Jump to feature-2 which is checked out in multiple worktrees
        result = runner.invoke(
            cli, ["jump", "feature-2", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should show error about multiple worktrees
        assert result.exit_code == 1
        assert "exists in multiple worktrees" in result.stderr
