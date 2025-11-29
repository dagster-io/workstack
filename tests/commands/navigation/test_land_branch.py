"""Tests for erk land-branch command."""

from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.types import PullRequestInfo
from erk_shared.integrations.graphite.fake import FakeGraphite
from erk_shared.integrations.graphite.types import BranchMetadata

from erk.cli.cli import cli
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.repo_discovery import RepoContext
from tests.test_utils.cli_helpers import assert_cli_error
from tests.test_utils.env_helpers import erk_inmem_env


def _make_pr(number: int, state: str = "OPEN", title: str = "Feature") -> PullRequestInfo:
    """Helper to create PullRequestInfo for tests."""
    return PullRequestInfo(
        number=number,
        state=state,
        url=f"https://github.com/owner/repo/pull/{number}",
        is_draft=False,
        title=title,
        checks_passing=None,
        owner="owner",
        repo="repo",
    )


def test_land_branch_success_navigates_to_child() -> None:
    """Test land-branch merges PR and navigates to single child branch."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Set up worktrees: main (root), feature-1 (current), feature-2 (child)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "feature-1",  # Currently on feature-1
            },
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

        # Set up GitHub with open PR for feature-1
        github_ops = FakeGitHub(prs={"feature-1": _make_pr(123)})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        # Execute: land-branch should merge PR and navigate to feature-2
        result = runner.invoke(
            cli, ["land-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Assert: Success
        assert result.exit_code == 0

        # Assert: PR was merged
        assert github_ops.merged_prs == [123]

        # Assert: Navigated to feature-2
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo_dir / "worktrees" / "feature-2") in script_content


def test_land_branch_success_navigates_to_parent_with_down_flag() -> None:
    """Test land-branch --down merges PR and navigates to parent (trunk)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Set up worktrees: main (root), feature-1 (current)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "feature-1",  # Currently on feature-1
            },
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

        # Set up GitHub with open PR for feature-1
        github_ops = FakeGitHub(prs={"feature-1": _make_pr(456)})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        # Execute: land-branch --down should merge PR and navigate to trunk/root
        result = runner.invoke(
            cli, ["land-branch", "--down", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Assert: Success
        assert result.exit_code == 0

        # Assert: PR was merged
        assert github_ops.merged_prs == [456]

        # Assert: Navigated to root (trunk is in root repo)
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(env.cwd) in script_content  # Root repo path


def test_land_branch_multiple_children_skips_navigation() -> None:
    """Test land-branch skips navigation when multiple children exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Set up worktrees: main (root), feature-1 (current), feature-2a, feature-2b
        git_ops = FakeGit(
            worktrees=env.build_worktrees(
                "main", ["feature-1", "feature-2a", "feature-2b"], repo_dir=repo_dir
            ),
            current_branches={
                env.cwd: "feature-1",  # Currently on feature-1
            },
            default_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        # Set up stack: main -> feature-1 -> [feature-2a, feature-2b]
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch(
                    "feature-1", "main", children=["feature-2a", "feature-2b"], commit_sha="def456"
                ),
                "feature-2a": BranchMetadata.branch("feature-2a", "feature-1", commit_sha="ghi789"),
                "feature-2b": BranchMetadata.branch("feature-2b", "feature-1", commit_sha="jkl012"),
            }
        )

        # Set up GitHub with open PR for feature-1
        github_ops = FakeGitHub(prs={"feature-1": _make_pr(789)})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        # Execute: land-branch should merge PR but not navigate (multiple children)
        result = runner.invoke(cli, ["land-branch"], obj=test_ctx, catch_exceptions=False)

        # Assert: Success (exit code 0 because merge succeeded)
        assert result.exit_code == 0

        # Assert: PR was merged
        assert github_ops.merged_prs == [789]


def test_land_branch_with_cleanup_deletes_worktree() -> None:
    """Test land-branch --cleanup deletes merged branch and worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Set up worktrees: main (root), feature-1 (current), feature-2 (child)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "feature-1",  # Currently on feature-1
            },
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

        # Set up GitHub with open PR for feature-1
        github_ops = FakeGitHub(prs={"feature-1": _make_pr(321)})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        # Execute: land-branch --cleanup should merge, navigate, and delete worktree
        result = runner.invoke(
            cli, ["land-branch", "--cleanup", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Assert: Success
        assert result.exit_code == 0

        # Assert: PR was merged
        assert github_ops.merged_prs == [321]

        # Assert: Branch was deleted
        assert "feature-1" in git_ops.deleted_branches

        # Assert: Worktree was removed
        feature_1_wt = repo_dir / "worktrees" / "feature-1"
        assert feature_1_wt in git_ops.removed_worktrees

        # Assert: Navigated to feature-2
        script_path = Path(result.stdout.strip())
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert str(repo_dir / "worktrees" / "feature-2") in script_content


def test_land_branch_error_parent_not_trunk() -> None:
    """Test land-branch fails when parent is not trunk."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Set up worktrees: main (root), feature-1, feature-2 (current)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "feature-2",  # Currently on feature-2 (parent is feature-1, not trunk)
            },
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

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, repo=repo, use_graphite=True
        )

        # Execute: land-branch should fail because parent is not trunk
        result = runner.invoke(cli, ["land-branch"], obj=test_ctx, catch_exceptions=False)

        # Assert: Error
        assert_cli_error(result, 1, "Branch must be exactly one level up from main")
        assert_cli_error(result, 1, "Parent branch: feature-1")


def test_land_branch_error_no_pr() -> None:
    """Test land-branch fails when no PR exists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Set up worktrees: main (root), feature-1 (current)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "feature-1",  # Currently on feature-1
            },
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

        # No PR for feature-1
        github_ops = FakeGitHub(prs={})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        # Execute: land-branch should fail because no PR exists
        result = runner.invoke(cli, ["land-branch"], obj=test_ctx, catch_exceptions=False)

        # Assert: Error
        assert_cli_error(result, 1, "No pull request found for this branch")


def test_land_branch_error_pr_not_open() -> None:
    """Test land-branch fails when PR is not OPEN."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Set up worktrees: main (root), feature-1 (current)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "feature-1",  # Currently on feature-1
            },
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

        # PR for feature-1 is MERGED, not OPEN
        github_ops = FakeGitHub(prs={"feature-1": _make_pr(654, state="MERGED")})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        # Execute: land-branch should fail because PR is not OPEN
        result = runner.invoke(cli, ["land-branch"], obj=test_ctx, catch_exceptions=False)

        # Assert: Error
        assert_cli_error(result, 1, "Pull request is not open")
        assert_cli_error(result, 1, "state: MERGED")


def test_land_branch_script_mode_outputs_activation_path() -> None:
    """Test land-branch --script outputs activation script path for shell integration."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Set up worktrees: main (root), feature-1 (current), feature-2 (child)
        git_ops = FakeGit(
            worktrees=env.build_worktrees("main", ["feature-1", "feature-2"], repo_dir=repo_dir),
            current_branches={
                env.cwd: "feature-1",  # Currently on feature-1
            },
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

        # Set up GitHub with open PR for feature-1
        github_ops = FakeGitHub(prs={"feature-1": _make_pr(987)})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops, graphite=graphite_ops, github=github_ops, repo=repo, use_graphite=True
        )

        # Execute: land-branch --script should output activation script path
        result = runner.invoke(
            cli, ["land-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Assert: Success
        assert result.exit_code == 0

        # Assert: Output is a script path
        script_path = Path(result.stdout.strip())

        # Assert: Script contains activation for feature-2
        script_content = env.script_writer.get_script_content(script_path)
        assert script_content is not None
        assert "cd" in script_content
        assert str(repo_dir / "worktrees" / "feature-2") in script_content
