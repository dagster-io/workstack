"""Tests for workstack down command."""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.branch_metadata import BranchMetadata
from workstack.core.gitops import WorktreeInfo


def test_down_with_existing_worktree() -> None:
    """Test down command when parent branch has a worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        work_dir = env.workstacks_root / env.cwd.name

        # Set up worktrees
        (work_dir / "feature-1").mkdir(parents=True, exist_ok=True)
        (work_dir / "feature-2").mkdir(parents=True, exist_ok=True)

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=work_dir / "feature-1", branch="feature-1"),
                    WorktreeInfo(path=work_dir / "feature-2", branch="feature-2"),
                ]
            },
            current_branches={env.cwd: "feature-2"},  # Simulate being in feature-2 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        test_ctx = env.build_context(git_ops=git_ops, graphite_ops=graphite_ops, use_graphite=True)

        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should generate script for feature-1
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(work_dir / "feature-1") in script_content


def test_down_to_trunk_root() -> None:
    """Test down command when parent is trunk checked out in root."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        work_dir = env.workstacks_root / env.cwd.name

        # Main is checked out in root, feature-1 has its own worktree
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=work_dir / "feature-1", branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "feature-1"},  # Simulate being in feature-1 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        test_ctx = env.build_context(git_ops=git_ops, graphite_ops=graphite_ops, use_graphite=True)

        # Navigate down from feature-1 to root (main)
        (work_dir / "feature-1").mkdir(parents=True, exist_ok=True)

        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should generate script for root
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(env.cwd) in script_content
        assert "root" in script_content.lower()


def test_down_at_trunk() -> None:
    """Test down command when already at trunk."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main")]},
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main (only trunk)
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            }
        )

        test_ctx = env.build_context(git_ops=git_ops, graphite_ops=graphite_ops, use_graphite=True)

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Already at the bottom of the stack" in result.stderr
        assert "trunk branch 'main'" in result.stderr


def test_down_parent_has_no_worktree() -> None:
    """Test down command when parent branch exists but has no worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        work_dir = env.workstacks_root / env.cwd.name

        # Only feature-2 has a worktree, feature-1 does not
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=work_dir / "feature-2", branch="feature-2"),
                ]
            },
            current_branches={env.cwd: "feature-2"},  # Simulate being in feature-2 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        test_ctx = env.build_context(git_ops=git_ops, graphite_ops=graphite_ops, use_graphite=True)

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "feature-1" in result.stderr or "parent branch" in result.stderr
        assert "no worktree" in result.stderr
        assert "workstack create feature-1" in result.stderr


def test_down_graphite_not_enabled() -> None:
    """Test down command requires Graphite to be enabled."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main")]},
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Graphite is NOT enabled
        test_ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "requires Graphite to be enabled" in result.stderr
        assert "workstack config set use_graphite true" in result.stderr


def test_down_detached_head() -> None:
    """Test down command fails gracefully on detached HEAD."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Current branch is None (detached HEAD)
        git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=None)]},
            current_branches={env.cwd: None},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git_ops=git_ops, use_graphite=True)

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Not currently on a branch" in result.stderr
        assert "detached HEAD" in result.stderr


def test_down_script_flag() -> None:
    """Test down command with --script flag generates activation script."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        work_dir = env.workstacks_root / env.cwd.name

        # Set up worktrees
        (work_dir / "feature-1").mkdir(parents=True, exist_ok=True)
        (work_dir / "feature-2").mkdir(parents=True, exist_ok=True)

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=work_dir / "feature-1", branch="feature-1"),
                    WorktreeInfo(path=work_dir / "feature-2", branch="feature-2"),
                ]
            },
            current_branches={env.cwd: "feature-2"},  # Simulate being in feature-2 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        test_ctx = env.build_context(git_ops=git_ops, graphite_ops=graphite_ops, use_graphite=True)

        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Output should be a script path
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        # Verify script contains the target worktree path
        assert str(work_dir / "feature-1") in script_content


def test_down_with_mismatched_worktree_name() -> None:
    """Test down command when worktree directory name differs from branch name.

    This is a regression test for the bug where branch names from Graphite navigation
    were passed directly to _activate_worktree(), which expects worktree paths.
    The fix uses find_worktree_for_branch() to resolve branch -> worktree path.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Work dir is constructed as workstacks_root / repo_name, where repo_name = cwd.name
        work_dir = env.workstacks_root / env.cwd.name

        # Worktree directories use different naming than branch names
        # Branch: feature/auth -> Worktree: auth-work
        # Branch: feature/auth-tests -> Worktree: auth-tests-work
        (work_dir / "auth-work").mkdir(parents=True, exist_ok=True)
        (work_dir / "auth-tests-work").mkdir(parents=True, exist_ok=True)

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=work_dir / "auth-work", branch="feature/auth"),
                    WorktreeInfo(path=work_dir / "auth-tests-work", branch="feature/auth-tests"),
                ]
            },
            current_branches={
                env.cwd: "feature/auth-tests"
            },  # Simulate being in feature/auth-tests worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature/auth -> feature/auth-tests
        # Branch names contain slashes, but worktree dirs use different names
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk(
                    "main", children=["feature/auth"], commit_sha="abc123"
                ),
                "feature/auth": BranchMetadata.branch(
                    "feature/auth", "main", children=["feature/auth-tests"], commit_sha="def456"
                ),
                "feature/auth-tests": BranchMetadata.branch(
                    "feature/auth-tests", "feature/auth", commit_sha="ghi789"
                ),
            }
        )

        test_ctx = env.build_context(git_ops=git_ops, graphite_ops=graphite_ops, use_graphite=True)

        # Navigate down from feature/auth-tests to feature/auth
        # This would fail before the fix because it would try to find a worktree named
        # "feature/auth" instead of resolving to "auth-work"
        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Should generate script for auth-work (not feature/auth)
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(work_dir / "auth-work") in script_content
