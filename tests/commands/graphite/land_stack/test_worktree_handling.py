"""Tests for land-stack worktree handling."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.git.abc import WorktreeInfo
from tests.fakes.git import FakeGit
from tests.fakes.github import FakeGitHub
from tests.fakes.graphite import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_stack_with_down_flag_includes_flag_in_error_suggestions() -> None:
    """Test that land-stack --down includes --down in retry suggestion."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create linked worktrees (automatically tracked) - only for downstack branches
        env.create_linked_worktree(name="feat-1", branch="feat-1", chdir=False)
        env.create_linked_worktree(name="feat-2", branch="feat-2", chdir=False)
        # Start from feat-3
        env.create_linked_worktree(name="feat-3", branch="feat-3", chdir=True)

        # Build both ops (automatically includes all created worktrees)
        git_ops, graphite = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2", "feat-1", children=["feat-3"], commit_sha="ghi789"
                ),
                "feat-3": BranchMetadata.branch("feat-3", "feat-2", commit_sha="jkl012"),
            },
            current_branch="feat-3",
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
            },
            pr_bases={
                100: "main",  # feat-1 base is main
                200: "main",  # feat-2 base is main (after feat-1 lands and restacks)
                300: "main",  # feat-3 base is main (after feat-2 lands and restacks)
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack", "--down"], obj=test_ctx)

        # Should fail with multi-worktree error including --down flag
        assert result.exit_code == 1
        assert "Cannot land stack - branches are checked out in multiple worktrees" in result.output
        assert "feat-1" in result.output
        assert "feat-2" in result.output
        # Key assertion: forest merge suggestion (no --down flag) and retry with --down
        assert "erk forest merge" in result.output
        assert "erk land-stack --down" in result.output


def test_land_stack_fails_when_branches_in_multiple_worktrees() -> None:
    """Test that land-stack fails when stack branches are checked out in multiple worktrees."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create linked worktrees (automatically tracked)
        env.create_linked_worktree(name="feat-1", branch="feat-1", chdir=False)
        env.create_linked_worktree(name="feat-2", branch="feat-2", chdir=False)
        env.create_linked_worktree(name="feat-3", branch="feat-3", chdir=True)

        # Build both ops (automatically includes all created worktrees)
        git_ops, graphite = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2", "feat-1", children=["feat-3"], commit_sha="ghi789"
                ),
                "feat-3": BranchMetadata.branch("feat-3", "feat-2", commit_sha="jkl012"),
            },
            current_branch="feat-3",
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
            },
            pr_bases={
                100: "main",  # feat-1 base is main
                200: "main",  # feat-2 base is main (after feat-1 lands and restacks)
                300: "main",  # feat-3 base is main (after feat-2 lands and restacks)
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        # Should fail with multi-worktree error
        assert result.exit_code == 1
        assert "Cannot land stack - branches are checked out in multiple worktrees" in result.output
        assert "feat-1" in result.output
        assert "feat-2" in result.output
        # Key assertion: forest merge suggestion and retry without --down
        assert "erk forest merge" in result.output
        assert "erk land-stack" in result.output
        # Verify --down is NOT included in retry suggestion
        assert "erk land-stack --down" not in result.output


def test_land_stack_succeeds_when_all_branches_in_current_worktree() -> None:
    """Test that land-stack succeeds when all stack branches are only in current worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Only main branch in repo root, current branch is feat-2
        # feat-1 and feat-2 not checked out in other worktrees
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-2"},
            existing_paths={env.cwd, env.git_dir},
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        # Stack: main → feat-1 → feat-2
        # Current: feat-2
        # Should land: feat-1, feat-2
        graphite = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            stacks={
                "feat-2": ["main", "feat-1", "feat-2"],
            },
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_bases={
                100: "main",  # feat-1 base is main
                200: "main",  # feat-2 base is main (after feat-1 lands and restacks)
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        # Use --dry-run to avoid actual merging
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Should succeed and show landing plan
        assert "Landing 2 PRs" in result.output
        assert "feat-1" in result.output
        assert "feat-2" in result.output
        # Should NOT show worktree conflict error
        assert "multiple worktrees" not in result.output


def test_land_stack_from_linked_worktree_on_branch_being_landed() -> None:
    """Test that land-stack succeeds when run from current worktree on branch being landed.

    Scenario: User is in a linked worktree on feat-1 and wants to land that PR.
    The validation should EXCLUDE the current branch in the current worktree from conflicts.

    After fix: Validation correctly excludes the current branch in the current worktree,
    only flagging branches checked out in OTHER worktrees as conflicts.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Create linked worktree for feat-1 (chdir is ignored in pure mode)
        linked_wt = env.create_linked_worktree(name="feat-1-work", branch="feat-1", chdir=False)

        # Build ops for simple stack: main → feat-1
        git_ops, graphite = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
            current_worktree=linked_wt,
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            },
            pr_bases={
                100: "main",  # feat-1 base is main
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite,
            github=github_ops,
            shell=FakeShell(),
            dry_run=False,
            cwd=linked_wt,
        )

        # Try to land feat-1 from the linked worktree
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Should succeed - current branch in current worktree is not a conflict
        assert result.exit_code == 0

        # Should NOT show worktree conflict error
        assert (
            "Cannot land stack - branches are checked out in multiple worktrees"
            not in result.output
        )
