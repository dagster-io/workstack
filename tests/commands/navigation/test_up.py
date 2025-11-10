"""Tests for workstack up command."""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils.env_helpers import simulated_workstack_env
from tests.test_utils.graphite_helpers import setup_graphite_stack
from workstack.cli.cli import cli
from workstack.core.branch_metadata import BranchMetadata
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo
from workstack.core.global_config import GlobalConfig


def test_up_with_existing_worktree() -> None:
    """Test up command when child branch has a worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name

        # Set up worktrees
        feature_1_path = workstacks_dir / "feature-1"
        feature_1_path.mkdir(parents=True, exist_ok=True)

        # The test runs from cwd, so we simulate being in feature-1 by setting
        # cwd's current branch to feature-1
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "feature-1", branch="feature-1"),
                    WorktreeInfo(path=workstacks_dir / "feature-2", branch="feature-2"),
                ]
            },
            current_branches={
                env.cwd: "feature-1",  # Simulate being in feature-1 worktree
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={
                env.cwd: env.git_dir,
            },
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.cwd / "workstacks",
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Set up stack: main -> feature-1 -> feature-2
        FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=env.cwd,
        )

        # Navigate up from feature-1 to feature-2
        # Run from feature-1 worktree
        (workstacks_dir / "feature-1").mkdir(parents=True, exist_ok=True)
        (workstacks_dir / "feature-2").mkdir(parents=True, exist_ok=True)

        result = runner.invoke(cli, ["up", "--script"], obj=test_ctx, catch_exceptions=False)

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0
        # Should generate script for feature-2
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(workstacks_dir / "feature-2") in script_content


def test_up_at_top_of_stack() -> None:
    """Test up command when at the top of stack (no children)."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "feature-2", branch="feature-2"),
                ]
            },
            current_branches={env.cwd: "feature-2"},  # Simulate being in feature-2 worktree
            git_common_dirs={env.cwd: env.git_dir},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.cwd / "workstacks",
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Set up stack: main -> feature-1 -> feature-2 (at top)
        FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Already at the top of the stack" in result.stderr


def test_up_child_has_no_worktree() -> None:
    """Test up command when child branch exists but has no worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name

        # Only feature-1 has a worktree, feature-2 does not
        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "feature-1", branch="feature-1"),
                ]
            },
            current_branches={env.cwd: "feature-1"},  # Simulate being in feature-1 worktree
            git_common_dirs={env.cwd: env.git_dir},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.cwd / "workstacks",
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Set up stack: main -> feature-1 -> feature-2
        FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "feature-2" in result.stderr
        assert "no worktree" in result.stderr
        assert "workstack create feature-2" in result.stderr


def test_up_graphite_not_enabled() -> None:
    """Test up command requires Graphite to be enabled."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main")]},
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Graphite is NOT enabled
        global_config_ops = GlobalConfig(
            workstacks_root=env.cwd / "workstacks",
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "requires Graphite to be enabled" in result.stderr
        assert "workstack config set use_graphite true" in result.stderr


def test_up_detached_head() -> None:
    """Test up command fails gracefully on detached HEAD."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Current branch is None (detached HEAD)
        git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch=None)]},
            current_branches={env.cwd: None},
            git_common_dirs={env.cwd: env.git_dir},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.cwd / "workstacks",
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Not currently on a branch" in result.stderr
        assert "detached HEAD" in result.stderr


def test_up_script_flag() -> None:
    """Test up command with --script flag generates activation script."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name

        # Set up worktrees
        (workstacks_dir / "feature-1").mkdir(parents=True, exist_ok=True)
        (workstacks_dir / "feature-2").mkdir(parents=True, exist_ok=True)

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "feature-1", branch="feature-1"),
                    WorktreeInfo(path=workstacks_dir / "feature-2", branch="feature-2"),
                ]
            },
            current_branches={env.cwd: "feature-1"},  # Simulate being in feature-1 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.cwd / "workstacks",
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Set up stack: main -> feature-1 -> feature-2
        FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["up", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Output should be a script path
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        # Verify script contains the target worktree path
        assert str(workstacks_dir / "feature-2") in script_content


def test_up_multiple_children_fails_explicitly() -> None:
    """Test up command fails when branch has multiple children."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name

        # Set up stack: main -> feature-1 -> [feature-2a, feature-2b]
        # feature-1 has TWO children
        setup_graphite_stack(
            env.git_dir,
            {
                "main": {"parent": None, "children": ["feature-1"], "is_trunk": True},
                "feature-1": {"parent": "main", "children": ["feature-2a", "feature-2b"]},
                "feature-2a": {"parent": "feature-1", "children": []},
                "feature-2b": {"parent": "feature-1", "children": []},
            },
        )

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "feature-1", branch="feature-1"),
                    WorktreeInfo(path=workstacks_dir / "feature-2a", branch="feature-2a"),
                    WorktreeInfo(path=workstacks_dir / "feature-2b", branch="feature-2b"),
                ]
            },
            current_branches={env.cwd: "feature-1"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.cwd / "workstacks",
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Error: Branch 'feature-1' has multiple children" in result.stderr
        assert "'feature-2a'" in result.stderr
        assert "'feature-2b'" in result.stderr
        assert "workstack create" in result.stderr


def test_up_with_mismatched_worktree_name() -> None:
    """Test up command when worktree directory name differs from branch name.

    This is a regression test for the bug where branch names from Graphite navigation
    were passed directly to _activate_worktree(), which expects worktree paths.
    The fix uses find_worktree_for_branch() to resolve branch -> worktree path.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name

        # Worktree directories use different naming than branch names
        # Branch: feature/auth -> Worktree: auth-work
        # Branch: feature/auth-tests -> Worktree: auth-tests-work
        (workstacks_dir / "auth-work").mkdir(parents=True, exist_ok=True)
        (workstacks_dir / "auth-tests-work").mkdir(parents=True, exist_ok=True)

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=workstacks_dir / "auth-work", branch="feature/auth"),
                    WorktreeInfo(
                        path=workstacks_dir / "auth-tests-work", branch="feature/auth-tests"
                    ),
                ]
            },
            current_branches={env.cwd: "feature/auth"},  # Simulate being in feature/auth worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.cwd / "workstacks",
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Set up stack: main -> feature/auth -> feature/auth-tests
        # Branch names contain slashes, but worktree dirs don't
        FakeGraphiteOps(
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

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            cwd=env.cwd,
        )

        # Navigate up from feature/auth to feature/auth-tests
        # This would fail before the fix because it would try to find a worktree named
        # "feature/auth-tests" instead of resolving to "auth-tests-work"
        result = runner.invoke(cli, ["up", "--script"], obj=test_ctx, catch_exceptions=False)

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Should generate script for auth-tests-work (not feature/auth-tests)
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(workstacks_dir / "auth-tests-work") in script_content
