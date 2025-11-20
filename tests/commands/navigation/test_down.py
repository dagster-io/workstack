"""Tests for erk down command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.git.abc import WorktreeInfo
from erk.core.repo_discovery import RepoContext
from tests.fakes.git import FakeGit
from tests.fakes.graphite import FakeGraphite
from tests.test_utils.cli_helpers import assert_cli_error
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_down_with_existing_worktree() -> None:
    """Test down command when parent branch has a worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-2"},  # Simulate being in feature-2 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should generate script for feature-1 (verify in-memory)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo_dir / "worktrees" / "feature-1") in script_content


def test_down_to_trunk_root() -> None:
    """Test down command when parent is trunk checked out in root."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Main is checked out in root, feature-1 has its own worktree
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-1"},  # Simulate being in feature-1 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            }
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        # Navigate down from feature-1 to root (main)
        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Should generate script for root (verify in-memory)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(env.cwd) in script_content
        assert "root" in script_content.lower()


def test_down_at_trunk() -> None:
    """Test down command when already at trunk."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main (only trunk)
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            }
        )

        test_ctx = env.build_context(git=git_ops, graphite=graphite_ops, use_graphite=True)

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(result, 1, "Already at the bottom of the stack", "trunk branch 'main'")


def test_down_parent_has_no_worktree() -> None:
    """Test down command when parent branch exists but has no worktree - should auto-create."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Only feature-2 has a worktree, feature-1 does not (will be auto-created)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-2"},  # Simulate being in feature-2 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
            # feature-1 exists locally
            local_branches={env.cwd: ["main", "feature-1", "feature-2"]},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir,
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        # Should succeed and create worktree
        assert result.exit_code == 0

        # Verify worktree was created for feature-1
        # added_worktrees is a list of (path, branch) tuples
        assert any(branch == "feature-1" for _path, branch in git_ops.added_worktrees)


def test_down_graphite_not_enabled() -> None:
    """Test down command requires Graphite to be enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Graphite is NOT enabled
        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(
            result,
            1,
            "requires Graphite to be enabled",
            "erk config set use_graphite true",
        )


def test_down_detached_head() -> None:
    """Test down command fails gracefully on detached HEAD."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Current branch is None (detached HEAD)
        git_ops = FakeGit(
            worktrees=env.build_worktrees(None),
            current_branches={env.cwd: None},
            git_common_dirs={env.cwd: env.git_dir},
        )

        test_ctx = env.build_context(git=git_ops, use_graphite=True)

        result = runner.invoke(cli, ["down"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(result, 1, "Not currently on a branch", "detached HEAD")


def test_down_script_flag() -> None:
    """Test down command with --script flag generates activation script."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={env.cwd: "feature-2"},  # Simulate being in feature-2 worktree
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1 -> feature-2
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2"], commit_sha="def456"
                ),
                "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
            }
        )

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        assert result.exit_code == 0
        # Output should be a script path (verify in-memory)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        # Verify script contains the target worktree path
        assert str(repo_dir / "worktrees" / "feature-1") in script_content


def test_down_with_mismatched_worktree_name() -> None:
    """Test down command when worktree directory name differs from branch name.

    This is a regression test for the bug where branch names from Graphite navigation
    were passed directly to _activate_worktree(), which expects worktree paths.
    The fix uses find_worktree_for_branch() to resolve branch -> worktree path.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Worktree directories use different naming than branch names
        # Branch: feature/auth -> Worktree: auth-work
        # Branch: feature/auth-tests -> Worktree: auth-tests-work
        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=repo_dir / "auth-work", branch="feature/auth", is_root=False),
                    WorktreeInfo(
                        path=repo_dir / "auth-tests-work",
                        branch="feature/auth-tests",
                        is_root=False,
                    ),
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
        graphite_ops = FakeGraphite(
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

        # Create RepoContext to avoid filesystem checks
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        # Navigate down from feature/auth-tests to feature/auth
        # This would fail before the fix because it would try to find a worktree named
        # "feature/auth" instead of resolving to "auth-work"
        result = runner.invoke(cli, ["down", "--script"], obj=test_ctx, catch_exceptions=False)

        if result.exit_code != 0:
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")
        assert result.exit_code == 0

        # Should generate script for auth-work (not feature/auth) (verify in-memory)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo_dir / "auth-work") in script_content
