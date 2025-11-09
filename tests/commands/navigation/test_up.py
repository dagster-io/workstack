"""Tests for workstack up command."""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.repo_setup import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.graphite_ops import BranchMetadata


def test_up_with_existing_worktree() -> None:
    """Test up command when child branch has a worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktrees for feature-1 and feature-2
        env.create_linked_worktree("feature-1", "feature-1", chdir=False)
        feature_2_path = env.create_linked_worktree("feature-2", "feature-2", chdir=False)

        # Build ops with feature-1 as current branch (in root worktree)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature-1"], sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", children=["feature-2"], sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", parent="feature-1", sha="ghi789"),
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

        # Navigate up from feature-1 to feature-2
        result = runner.invoke(cli, ["up", "--script"], obj=test_ctx, catch_exceptions=False)

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0
        # Should generate script for feature-2
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        assert str(feature_2_path) in script_content


def test_up_at_top_of_stack() -> None:
    """Test up command when at the top of stack (no children)."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktree for feature-2
        env.create_linked_worktree("feature-2", "feature-2", chdir=False)

        # Build ops with feature-2 as current branch (at top of stack)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature-1"], sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", children=["feature-2"], sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", parent="feature-1", sha="ghi789"),
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

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Already at the top of the stack" in result.stderr


def test_up_child_has_no_worktree() -> None:
    """Test up command when child branch exists but has no worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Only create worktree for feature-1, not feature-2
        env.create_linked_worktree("feature-1", "feature-1", chdir=False)

        # Build ops with feature-1 as current branch
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature-1"], sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", children=["feature-2"], sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", parent="feature-1", sha="ghi789"),
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

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "feature-2" in result.stderr
        assert "no worktree" in result.stderr
        assert "workstack create feature-2" in result.stderr


def test_up_graphite_not_enabled() -> None:
    """Test up command requires Graphite to be enabled."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build ops with just main branch
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(sha="abc123"),
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

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "requires Graphite to be enabled" in result.stderr
        assert "workstack config set use_graphite true" in result.stderr


def test_up_detached_head() -> None:
    """Test up command fails gracefully on detached HEAD.

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

        result = runner.invoke(cli, ["up"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 1
        assert "Not currently on a branch" in result.stderr
        assert "detached HEAD" in result.stderr


def test_up_script_flag() -> None:
    """Test up command with --script flag generates activation script."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktrees for feature-1 and feature-2
        env.create_linked_worktree("feature-1", "feature-1", chdir=False)
        feature_2_path = env.create_linked_worktree("feature-2", "feature-2", chdir=False)

        # Build ops with feature-1 as current branch
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature-1"], sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", children=["feature-2"], sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", parent="feature-1", sha="ghi789"),
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

        result = runner.invoke(cli, ["up", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Output should be a script path
        script_path = Path(result.stdout.strip())
        assert script_path.exists()
        script_content = script_path.read_text()
        # Verify script contains the target worktree path
        assert str(feature_2_path) in script_content


def test_up_multiple_children_fails_explicitly() -> None:
    """Test up command fails when branch has multiple children."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create worktrees for all branches
        env.create_linked_worktree("feature-1", "feature-1", chdir=False)
        env.create_linked_worktree("feature-2a", "feature-2a", chdir=False)
        env.create_linked_worktree("feature-2b", "feature-2b", chdir=False)

        # Build ops with feature-1 as current branch
        # feature-1 has TWO children (feature-2a and feature-2b)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature-1"], sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", children=["feature-2a", "feature-2b"], sha="def456"
                ),
                "feature-2a": BranchMetadata.branch("feature-2a", parent="feature-1", sha="ghi789"),
                "feature-2b": BranchMetadata.branch("feature-2b", parent="feature-1", sha="jkl012"),
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
        # Worktree directories use different naming than branch names
        # Branch: feature/auth -> Worktree: auth-work
        # Branch: feature/auth-tests -> Worktree: auth-tests-work
        env.create_linked_worktree("auth-work", "feature/auth", chdir=False)
        auth_tests_path = env.create_linked_worktree(
            "auth-tests-work", "feature/auth-tests", chdir=False
        )

        # Build ops with feature/auth as current branch
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.main(children=["feature/auth"], sha="abc123"),
                "feature/auth": BranchMetadata.branch(
                    "feature/auth", children=["feature/auth-tests"], sha="def456"
                ),
                "feature/auth-tests": BranchMetadata.branch(
                    "feature/auth-tests", parent="feature/auth", sha="ghi789"
                ),
            },
            current_branch="feature/auth",
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
        assert str(auth_tests_path) in script_content
