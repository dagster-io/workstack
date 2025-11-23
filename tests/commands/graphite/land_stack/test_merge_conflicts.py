"""Tests for land-stack merge conflict detection."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.git.abc import WorktreeInfo
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.github.types import PRMergeability
from erk.core.graphite.fake import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_stack_fails_when_first_pr_has_conflict() -> None:
    """Test that land-stack fails when first PR has merge conflict."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
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
        graphite_ops = FakeGraphite(
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

        # feat-1 has CONFLICTING status
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="CONFLICTING", merge_state_status="DIRTY"),
                200: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should fail before user confirmation
        assert result.exit_code == 1
        assert "Cannot land stack - PRs have merge conflicts" in result.output
        assert "PR #100 (feat-1): has conflicts with main" in result.output
        assert "gt stack rebase" in result.output


def test_land_stack_fails_when_middle_pr_has_conflict() -> None:
    """Test that land-stack fails when middle PR has merge conflict."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-3"},
            existing_paths={env.cwd, env.git_dir},
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        # Stack: main → feat-1 → feat-2 → feat-3
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2", "feat-1", children=["feat-3"], commit_sha="ghi789"
                ),
                "feat-3": BranchMetadata.branch("feat-3", "feat-2", commit_sha="jkl012"),
            },
            stacks={
                "feat-3": ["main", "feat-1", "feat-2", "feat-3"],
            },
        )

        # feat-2 (middle PR) has CONFLICTING status
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
                200: PRMergeability(mergeable="CONFLICTING", merge_state_status="DIRTY"),
                300: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should fail before user confirmation
        assert result.exit_code == 1
        assert "Cannot land stack - PRs have merge conflicts" in result.output
        assert "PR #200 (feat-2): has conflicts with main" in result.output


def test_land_stack_fails_when_last_pr_has_conflict() -> None:
    """Test that land-stack fails when last PR has merge conflict."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
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
        graphite_ops = FakeGraphite(
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

        # feat-2 (last PR) has CONFLICTING status
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
                200: PRMergeability(mergeable="CONFLICTING", merge_state_status="DIRTY"),
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should fail before user confirmation
        assert result.exit_code == 1
        assert "Cannot land stack - PRs have merge conflicts" in result.output
        assert "PR #200 (feat-2): has conflicts with main" in result.output


def test_land_stack_succeeds_with_unknown_mergeability() -> None:
    """Test that land-stack proceeds with warning when PR mergeability is UNKNOWN."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-1"},
            existing_paths={env.cwd, env.git_dir},
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        # Simple stack: main → feat-1
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        # feat-1 has UNKNOWN status (GitHub hasn't computed it yet)
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="UNKNOWN", merge_state_status="UNKNOWN"),
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should show warning but not fail
        assert "Warning: PR #100 mergeability unknown" in result.output
        # Should proceed to show landing plan (exit code depends on dry-run success)


def test_land_stack_fails_with_conflict_using_master_trunk() -> None:
    """Test that error messages use correct trunk branch name (master)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="master"),
                ],
            },
            current_branches={env.cwd: "feat-1"},
            existing_paths={env.cwd, env.git_dir},
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        # Stack: master → feat-1
        graphite_ops = FakeGraphite(
            branches={
                "master": BranchMetadata.trunk("master", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "master", commit_sha="def456"),
            },
            stacks={
                "feat-1": ["master", "feat-1"],
            },
        )

        # feat-1 has CONFLICTING status
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="CONFLICTING", merge_state_status="DIRTY"),
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should fail with error messages using "master" not "main"
        assert result.exit_code == 1
        assert "Cannot land stack - PRs have merge conflicts" in result.output
        assert "PR #100 (feat-1): has conflicts with master" in result.output
        assert "git fetch origin master" in result.output


def test_land_stack_succeeds_when_all_prs_mergeable() -> None:
    """Test that land-stack succeeds when all PRs are MERGEABLE."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
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
        graphite_ops = FakeGraphite(
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

        # All PRs are MERGEABLE
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
                200: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should pass validation and show landing plan
        assert "Cannot land stack - PRs have merge conflicts" not in result.output
        assert "Landing 2 PRs" in result.output
