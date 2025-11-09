"""Tests for workstack down command."""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.repo_setup import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.graphite_ops import BranchMetadata


def test_down_with_existing_worktree() -> None:
    """Test down command when parent branch has a worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktrees for feature-1 and feature-2
        feature_1_path = env.create_linked_worktree("feature-1", "feature-1", chdir=False)
        env.create_linked_worktree("feature-2", "feature-2", chdir=False)

        # Build ops with feature-2 as current branch
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature-1"],
                    is_trunk=True,
                    commit_sha="abc123",
                ),
                "feature-1": BranchMetadata(
                    name="feature-1",
                    parent="main",
                    children=["feature-2"],
                    is_trunk=False,
                    commit_sha="def456",
                ),
                "feature-2": BranchMetadata(
                    name="feature-2",
                    parent="feature-1",
                    children=[],
                    is_trunk=False,
                    commit_sha="ghi789",
                ),
            },
            current_branch="feature-2",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should generate script for feature-1
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(feature_1_path) in script_content


def test_down_to_trunk_root() -> None:
    """Test down command when parent is trunk checked out in root."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktree for feature-1
        env.create_linked_worktree("feature-1", "feature-1", chdir=False)

        # Build ops with feature-1 as current branch
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature-1"],
                    is_trunk=True,
                    commit_sha="abc123",
                ),
                "feature-1": BranchMetadata(
                    name="feature-1",
                    parent="main",
                    children=[],
                    is_trunk=False,
                    commit_sha="def456",
                ),
            },
            current_branch="feature-1",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Navigate down from feature-1 to root (main)
        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should generate script for root
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(env.root_worktree) in script_content
        assert "root" in script_content.lower()


def test_down_at_trunk() -> None:
    """Test down command when already at trunk."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build ops with main as current branch (at trunk)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=[],
                    is_trunk=True,
                    commit_sha="abc123",
                ),
            },
            current_branch="main",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Already at the bottom of the stack" in result.stderr
        assert "trunk branch 'main'" in result.stderr


def test_down_parent_has_no_worktree() -> None:
    """Test down command when parent branch exists but has no worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Only create worktree for feature-2, not feature-1
        env.create_linked_worktree("feature-2", "feature-2", chdir=False)

        # Build ops with feature-2 as current branch
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature-1"],
                    is_trunk=True,
                    commit_sha="abc123",
                ),
                "feature-1": BranchMetadata(
                    name="feature-1",
                    parent="main",
                    children=["feature-2"],
                    is_trunk=False,
                    commit_sha="def456",
                ),
                "feature-2": BranchMetadata(
                    name="feature-2",
                    parent="feature-1",
                    children=[],
                    is_trunk=False,
                    commit_sha="ghi789",
                ),
            },
            current_branch="feature-2",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "feature-1" in result.stderr or "parent branch" in result.stderr
        assert "no worktree" in result.stderr
        assert "workstack create feature-1" in result.stderr


def test_down_graphite_not_enabled() -> None:
    """Test down command requires Graphite to be enabled."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build ops with just main branch
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=[],
                    is_trunk=True,
                    commit_sha="abc123",
                ),
            },
            current_branch="main",
        )

        # Graphite is NOT enabled
        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
            use_graphite=False,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "requires Graphite to be enabled" in result.stderr
        assert "workstack config set use_graphite true" in result.stderr


def test_down_detached_head() -> None:
    """Test down command fails gracefully on detached HEAD.

    Note: This is an edge case that requires manual FakeGitOps construction
    because SimulatedWorkstackEnv's build_ops_from_branches() doesn't support
    detached HEAD (current_branch=None).
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Manually construct FakeGitOps for detached HEAD scenario
        from tests.fakes.gitops import FakeGitOps
        from workstack.core.gitops import WorktreeInfo

        # Current branch is None (detached HEAD)
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [WorktreeInfo(path=env.root_worktree, branch=None, is_root=True)]
            },
            current_branches={env.root_worktree: None},
            git_common_dirs={env.root_worktree: env.root_worktree / ".git"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
            use_graphite=True,
        )

        # Empty graphite ops since we're not on a branch
        from tests.fakes.graphite_ops import FakeGraphiteOps

        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Not currently on a branch" in result.stderr
        assert "detached HEAD" in result.stderr


def test_down_script_flag() -> None:
    """Test down command with --script flag generates activation script."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktrees for feature-1 and feature-2
        feature_1_path = env.create_linked_worktree("feature-1", "feature-1", chdir=False)
        env.create_linked_worktree("feature-2", "feature-2", chdir=False)

        # Build ops with feature-2 as current branch
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature-1"],
                    is_trunk=True,
                    commit_sha="abc123",
                ),
                "feature-1": BranchMetadata(
                    name="feature-1",
                    parent="main",
                    children=["feature-2"],
                    is_trunk=False,
                    commit_sha="def456",
                ),
                "feature-2": BranchMetadata(
                    name="feature-2",
                    parent="feature-1",
                    children=[],
                    is_trunk=False,
                    commit_sha="ghi789",
                ),
            },
            current_branch="feature-2",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Output should be a script path
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        # Verify script contains the target worktree path
        assert str(feature_1_path) in script_content


def test_down_with_mismatched_worktree_name() -> None:
    """Test down command when worktree directory name differs from branch name.

    This is a regression test for the bug where branch names from Graphite navigation
    were passed directly to _activate_worktree(), which expects worktree paths.
    The fix uses find_worktree_for_branch() to resolve branch -> worktree path.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Worktree directories use different naming than branch names
        # Branch: feature/auth -> Worktree: auth-work
        # Branch: feature/auth-tests -> Worktree: auth-tests-work
        auth_work_path = env.create_linked_worktree("auth-work", "feature/auth", chdir=False)
        env.create_linked_worktree("auth-tests-work", "feature/auth-tests", chdir=False)

        # Build ops with feature/auth-tests as current branch
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feature/auth"],
                    is_trunk=True,
                    commit_sha="abc123",
                ),
                "feature/auth": BranchMetadata(
                    name="feature/auth",
                    parent="main",
                    children=["feature/auth-tests"],
                    is_trunk=False,
                    commit_sha="def456",
                ),
                "feature/auth-tests": BranchMetadata(
                    name="feature/auth-tests",
                    parent="feature/auth",
                    children=[],
                    is_trunk=False,
                    commit_sha="ghi789",
                ),
            },
            current_branch="feature/auth-tests",
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=env.root_worktree.parent / "workstacks",
            use_graphite=True,
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

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
        assert str(auth_work_path) in script_content
