"""Tests for workstack jump command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.gitops import WorktreeInfo
from erk.core.repo_discovery import RepoContext
from tests.fakes.gitops import FakeGitOps
from tests.test_utils.env_helpers import pure_workstack_env, simulated_workstack_env


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
    """Test jumping to a branch that doesn't exist in git."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
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
            # nonexistent-branch is NOT in this list
            local_branches={env.cwd: ["main", "feature-1"]},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )

        test_ctx = env.build_context(git_ops=git_ops, repo=repo)

        # Jump to a branch that doesn't exist
        result = runner.invoke(
            cli, ["jump", "nonexistent-branch"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 1
        assert "does not exist" in result.stderr
        assert "erk create --branch nonexistent-branch" in result.stderr


def test_jump_creates_worktree_for_unchecked_branch() -> None:
    """Test that jump auto-creates worktree when branch exists but is not checked out."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name

        # Branch 'existing-branch' exists in git but is not checked out
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "existing-branch"]},  # exists in git
            default_branches={env.cwd: "main"},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )

        test_ctx = env.build_context(git_ops=git_ops, repo=repo)

        # Jump to branch that exists but is not checked out
        result = runner.invoke(
            cli, ["jump", "existing-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        # Should succeed and create worktree
        assert result.exit_code == 0
        assert "creating worktree" in result.stderr
        assert "✓ Created worktree" in result.stderr

        # Verify worktree was created
        assert len(git_ops.added_worktrees) == 1
        added_wt_path, added_wt_branch = git_ops.added_worktrees[0]
        assert added_wt_branch == "existing-branch"

        # Should generate activation script (output path to stdout)
        assert result.stdout.strip() != ""
        script_path = Path(result.stdout.strip())
        assert script_path.exists()


def test_jump_to_branch_in_stack_but_not_checked_out() -> None:
    """Test that jump auto-creates worktree when branch exists in repo but is not checked out.

    With auto-creation behavior, branches that exist in Graphite stacks but are not
    directly checked out will have a worktree created automatically.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name
        wt1 = work_dir / "feature-1-wt"

        # feature-1 is checked out, but feature-base is not
        # (even though it exists in git)
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main", "feature-1", "feature-base"]},  # feature-base exists
            default_branches={env.cwd: "main"},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )

        test_ctx = env.build_context(git_ops=git_ops, repo=repo)

        # Jump to feature-base which exists in repo but is not checked out
        result = runner.invoke(
            cli, ["jump", "feature-base", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        # Should succeed and create worktree
        assert result.exit_code == 0
        assert "creating worktree" in result.stderr

        # Verify worktree was created
        assert len(git_ops.added_worktrees) == 1


def test_jump_works_without_graphite() -> None:
    """Test that jump works without Graphite enabled."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name
        feature_wt = work_dir / "feature-1-wt"

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

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )

        # Graphite is NOT enabled - jump should still work
        test_ctx = env.build_context(git_ops=git_ops, repo=repo)

        result = runner.invoke(
            cli, ["jump", "feature-1", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should succeed - jump no longer requires Graphite
        assert result.exit_code == 0
        script_path = Path(result.stdout.strip())
        # Verify script was written to in-memory store
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None


def test_jump_already_on_target_branch() -> None:
    """Test jumping when the target branch is already checked out in a single worktree."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name
        feature_wt = work_dir / "feature-1-wt"
        other_wt = work_dir / "other-wt"

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

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )

        test_ctx = env.build_context(git_ops=git_ops, repo=repo)

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
    with pure_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name
        feature_wt = work_dir / "feature-wt"
        other_wt = work_dir / "other-wt"

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

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )

        test_ctx = env.build_context(git_ops=git_ops, repo=repo)

        # Jump to feature-2 which is checked out in feature_wt
        result = runner.invoke(
            cli, ["jump", "feature-2", "--script"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        # Should not checkout (already on feature-2)
        assert len(git_ops.checked_out_branches) == 0
        # Should generate activation script (verify in-memory)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None


def test_jump_with_multiple_worktrees_same_branch() -> None:
    """Test error when multiple worktrees have the same branch checked out.

    This is an edge case that shouldn't happen in normal use (git prevents it),
    but our code should handle it gracefully.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name
        wt1 = work_dir / "wt1"
        wt2 = work_dir / "wt2"

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

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )

        test_ctx = env.build_context(git_ops=git_ops, repo=repo)

        # Jump to feature-2 which is checked out in multiple worktrees
        result = runner.invoke(
            cli, ["jump", "feature-2", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should show error about multiple worktrees
        assert result.exit_code == 1
        assert "exists in multiple worktrees" in result.stderr


def test_jump_creates_worktree_for_remote_only_branch() -> None:
    """Test jump auto-creates worktree when branch exists only on origin."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name

        # Branch exists on origin but not locally
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},  # feature-remote NOT here
            remote_branches={env.cwd: ["origin/main", "origin/feature-remote"]},  # But here
            default_branches={env.cwd: "main"},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )

        test_ctx = env.build_context(git_ops=git_ops, repo=repo)

        # Jump to remote branch
        result = runner.invoke(
            cli, ["jump", "feature-remote", "--script"], obj=test_ctx, catch_exceptions=False
        )

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        # Should succeed with worktree creation
        assert result.exit_code == 0, f"Expected success, got: {result.stderr}"
        assert "exists on origin, creating local tracking branch" in result.stderr
        assert "creating worktree" in result.stderr
        assert "✓ Created worktree" in result.stderr

        # Verify worktree was created
        assert len(git_ops.added_worktrees) == 1
        added_wt_path, added_wt_branch = git_ops.added_worktrees[0]
        assert added_wt_branch == "feature-remote"

        # Should generate activation script (output path to stdout)
        assert result.stdout.strip() != ""
        script_path = Path(result.stdout.strip())
        assert script_path.exists()


def test_jump_fails_when_branch_not_on_origin() -> None:
    """Test jump shows error when branch doesn't exist locally or on origin."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        work_dir = env.workstacks_root / env.cwd.name

        # Branch doesn't exist locally or remotely
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            local_branches={env.cwd: ["main"]},
            remote_branches={env.cwd: ["origin/main"]},  # nonexistent-branch NOT here
            default_branches={env.cwd: "main"},
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            workstacks_dir=work_dir,
        )

        test_ctx = env.build_context(git_ops=git_ops, repo=repo)

        # Jump to nonexistent branch
        result = runner.invoke(
            cli, ["jump", "nonexistent-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should fail with error message
        assert result.exit_code == 1
        assert "does not exist" in result.stderr
        assert "erk create --branch nonexistent-branch" in result.stderr
