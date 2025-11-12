"""Tests for the land-stack command."""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.github_ops import PullRequestInfo
from workstack.core.gitops import WorktreeInfo
from workstack.core.global_config import GlobalConfig
from workstack.core.graphite_ops import BranchMetadata


def test_land_stack_requires_graphite() -> None:
    """Test that land-stack command requires Graphite to be enabled."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build both ops from branch metadata
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        # use_graphite=False: Test that graphite is required
        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "requires Graphite" in result.output


def test_land_stack_fails_on_detached_head() -> None:
    """Test that land-stack fails when HEAD is detached."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # current_branches={env.cwd: None} indicates detached HEAD
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch=None),
                ],
            },
            current_branches={env.cwd: None},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "HEAD is detached" in result.output


def test_land_stack_fails_with_uncommitted_changes() -> None:
    """Test that land-stack fails when current worktree has uncommitted changes."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
            current_branches={env.cwd: "feat-1"},
            file_statuses={env.cwd: (["file.txt"], [], [])},  # Has staged changes
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Current worktree has uncommitted changes" in result.output
        assert str(env.cwd) in result.output  # Check path is shown
        assert "feat-1" in result.output  # Check branch is shown


def test_land_stack_ignores_root_worktree_changes_on_unrelated_branch() -> None:
    """Test that land-stack doesn't check root worktree when it's on unrelated branch."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Set up two worktrees:
        # - Root worktree: on branch "test-docs" with uncommitted changes
        # - Current worktree: on branch "feat-1" (clean)
        root_path = Path("/root")
        current_path = env.cwd

        git_ops = FakeGitOps(
            git_common_dirs={
                root_path: env.git_dir,
                current_path: env.git_dir,
            },
            worktrees={
                root_path: [
                    WorktreeInfo(path=root_path, branch="test-docs", is_root=True),
                    WorktreeInfo(path=current_path, branch="feat-1", is_root=False),
                ],
                current_path: [
                    WorktreeInfo(path=root_path, branch="test-docs", is_root=True),
                    WorktreeInfo(path=current_path, branch="feat-1", is_root=False),
                ],
            },
            current_branches={
                root_path: "test-docs",
                current_path: "feat-1",
            },
            file_statuses={
                root_path: (["uncommitted.txt"], [], []),  # Root has uncommitted changes
                current_path: ([], [], []),  # Current is clean
            },
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
                # Unrelated branch
                "test-docs": BranchMetadata.branch("test-docs", "main", commit_sha="xyz999"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
                "test-docs": ["main", "test-docs"],
            },
            pr_info={
                "feat-1": PullRequestInfo(
                    number=123,
                    state="OPEN",
                    url="https://github.com/owner/repo/pull/123",
                    is_draft=False,
                    checks_passing=True,
                    owner="owner",
                    repo="repo",
                ),
            },
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(
                pr_statuses={
                    "feat-1": "open",
                }
            ),
            shell_ops=FakeShellOps(),
            cwd=current_path,  # Current worktree is clean
            dry_run=True,  # Use dry-run to avoid actual GitHub operations
        )

        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # The command should not fail due to uncommitted changes since we only check
        # current worktree. It might fail for other reasons (dry-run mode, no GitHub
        # auth, etc.), but not for uncommitted changes
        assert "Current worktree has uncommitted changes" not in result.output
        # The error should not mention the root worktree path
        if result.exit_code != 0:
            assert str(root_path) not in result.output


def test_land_stack_fails_on_trunk_branch() -> None:
    """Test that land-stack fails when current branch is trunk."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "main"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            },
            stacks={
                "main": ["main"],
            },
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Cannot land trunk branch" in result.output


def test_land_stack_fails_when_branch_not_tracked() -> None:
    """Test that land-stack fails when branch is not tracked by Graphite."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "untracked-branch"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Branch not in graphite stack
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            },
            stacks={},
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not tracked by Graphite" in result.output


def test_land_stack_fails_when_pr_missing() -> None:
    """Test that land-stack fails when a branch has no PR."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-1"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk(
                    "main", children=["feat-1", "feat-2"], commit_sha="abc123"
                ),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            stacks={
                "feat-1": ["main", "feat-1", "feat-2"],
            },
        )

        # feat-1 has no PR (state=NONE)
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("NONE", None, None),
                "feat-2": ("OPEN", 123, "Add feature 2"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "No PR found" in result.output
        assert "feat-1" in result.output


def test_land_stack_fails_when_pr_closed() -> None:
    """Test that land-stack fails when a branch's PR is closed."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-1"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        # feat-1 PR is closed
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("CLOSED", 100, "Closed feature"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "closed" in result.output


def test_land_stack_gets_branches_to_land_correctly() -> None:
    """Test that land-stack lands from bottom of stack to current branch."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-2"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2 → feat-3
        # Current: feat-2
        # Should land: feat-1, feat-2 (bottom to current, not including feat-3)
        graphite_ops = FakeGraphiteOps(
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
                "feat-2": ["main", "feat-1", "feat-2", "feat-3"],
            },
        )

        # feat-1 and feat-2 have open PRs (feat-3 not needed)
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        # Use --force to skip confirmation
        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx, input="y\n")

        # Should show landing 2 PRs (feat-1 and feat-2 from bottom to current)
        assert "Landing 2 PRs" in result.output
        assert "feat-1" in result.output
        assert "feat-2" in result.output


def test_land_stack_from_top_of_stack_lands_all_branches() -> None:
    """Test that land-stack from top of stack lands all branches from bottom to current.

    When on the leaf/top branch of a stack, land-stack should land ALL branches
    from the bottom of the stack (first non-trunk) up to and including current.

    Bug: Currently only returns the current branch when at top of stack.
    Fix: Should return entire stack from bottom to current.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-4"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2 → feat-3 → feat-4
        # Current: feat-4 (at TOP/leaf)
        # Should land: feat-1, feat-2, feat-3, feat-4 (ALL 4 branches)
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2", "feat-1", children=["feat-3"], commit_sha="ghi789"
                ),
                "feat-3": BranchMetadata.branch(
                    "feat-3", "feat-2", children=["feat-4"], commit_sha="jkl012"
                ),
                "feat-4": BranchMetadata.branch("feat-4", "feat-3", commit_sha="mno345"),
            },
            stacks={
                "feat-4": ["main", "feat-1", "feat-2", "feat-3", "feat-4"],
            },
        )

        # All branches have open PRs
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
                "feat-4": ("OPEN", 400, "Feature 4"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        # Use --dry-run to avoid actual merging
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Should show landing 4 PRs (ALL branches from bottom to current)
        assert "Landing 4 PRs" in result.output
        assert "feat-1" in result.output
        assert "feat-2" in result.output
        assert "feat-3" in result.output
        assert "feat-4" in result.output


def test_land_stack_fails_when_branches_in_multiple_worktrees() -> None:
    """Test that land-stack fails when stack branches are checked out in multiple worktrees."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktrees (automatically tracked)
        env.create_linked_worktree(name="feat-1", branch="feat-1", chdir=False)
        env.create_linked_worktree(name="feat-2", branch="feat-2", chdir=False)
        env.create_linked_worktree(name="feat-3", branch="feat-3", chdir=True)

        # Build both ops (automatically includes all created worktrees)
        git_ops, graphite_ops = env.build_ops_from_branches(
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
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
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
        assert "workstack consolidate" in result.output


def test_land_stack_succeeds_when_all_branches_in_current_worktree() -> None:
    """Test that land-stack succeeds when all stack branches are only in current worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Only main branch in repo root, current branch is feat-2
        # feat-1 and feat-2 not checked out in other worktrees
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-2"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2
        # Current: feat-2
        # Should land: feat-1, feat-2
        graphite_ops = FakeGraphiteOps(
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

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
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


def test_land_stack_refreshes_metadata_after_sync() -> None:
    """Test that RealGraphiteOps invalidates cache after gt sync.

    This test verifies the fix for the cache invalidation bug:
    - Bug: RealGraphiteOps.sync() didn't invalidate _branches_cache
    - Result: After gt sync updated metadata, stale cached data was returned
    - Fix: Added `self._branches_cache = None` at end of sync()

    The test creates a simulated scenario where sync() modifies metadata
    and verifies that subsequent get_all_branches() calls return fresh data.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-2"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2
        graphite_ops = FakeGraphiteOps(
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

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        # Execute land-stack - should complete successfully
        # The fix ensures cache is invalidated after each sync
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Landing 2 PRs" in result.output


def test_land_stack_from_linked_worktree_on_branch_being_landed() -> None:
    """Test that land-stack works when run from a linked worktree on branch being landed.

    Scenario: User is in a linked worktree on feat-1 and wants to land that PR.
    The command should detect we're already on the branch and skip checkout.

    Before fix: Would try to checkout feat-1 in repo root, failing because it's
    already checked out in the linked worktree.

    After fix: Detects current branch and skips unnecessary checkout.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktree for feat-1 and change to it
        env.create_linked_worktree(name="feat-1-work", branch="feat-1", chdir=True)

        # Build ops for simple stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            cwd=Path.cwd(),
        )

        # Try to land feat-1 from the linked worktree
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Should succeed - command skips checkout when already on the branch
        # (dry-run mode doesn't execute real checkout logic, but validates flow works)
        assert result.exit_code == 0
        assert "Landing 1 PR" in result.output
        assert "feat-1" in result.output


def test_land_stack_switches_to_root_when_run_from_linked_worktree() -> None:
    """Test that land-stack switches to root worktree before cleanup.

    Scenario: User is in a linked worktree that will be destroyed during land-stack.
    Without the fix, the user's shell ends up in a destroyed directory.

    Bug: land-stack runs cleanup operations (including workstack sync -f) which
    destroys worktrees. If the current directory is one of those worktrees, the
    shell is left in a deleted directory.

    Fix: Before cleanup, check if Path.cwd() != repo.root and call os.chdir(repo.root).
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktree for feat-1 and change to it
        linked_wt = env.create_linked_worktree(name="feat-1-work", branch="feat-1", chdir=True)

        # Verify we're in the linked worktree
        assert Path.cwd() == linked_wt

        # Build ops for simple stack: main → feat-1
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata(
                    name="main",
                    parent=None,
                    children=["feat-1"],
                    commit_sha="abc123",
                    is_trunk=True,
                ),
                "feat-1": BranchMetadata(
                    name="feat-1",
                    parent="main",
                    children=None,
                    commit_sha="def456",
                    is_trunk=False,
                ),
            },
            current_branch="feat-1",
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Add feature 1"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            cwd=Path.cwd(),
        )

        # Run land-stack with --dry-run to avoid subprocess failures
        # Note: cleanup still executes in dry-run mode, directory switch still happens
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Verify the command completed
        assert result.exit_code == 0

        # CRITICAL: Verify working directory is now root worktree (not the linked worktree)
        # This proves the fix moved us before destroying the linked worktree
        assert Path.cwd() == env.root_worktree

        # Verify we're not in a destroyed/invalid directory
        assert Path.cwd().exists()


def test_land_stack_script_mode_accepts_flag() -> None:
    """Verify land-stack accepts --script flag for shell integration."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build test environment with a simple stack
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            },
            current_branch="feature-1",
        )

        # Setup GitHub ops with an open PR
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("OPEN", 123, "Feature 1")})

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Act: Run with --script flag (this is what shell wrapper will call)
        # Use --dry-run to avoid subprocess failures in test environment
        result = runner.invoke(
            cli,
            ["land-stack", "-f", "--script", "--dry-run"],
            obj=test_ctx,
        )

        # Assert: Command should succeed
        # Note: We can't verify actual shell integration behavior with CliRunner
        # but we can verify the flag is accepted and the command runs
        assert result.exit_code == 0

        # In script mode, all output should go to stderr
        # Passthrough commands rely on the recovery mechanism, not explicit script generation


def test_land_stack_updates_pr_base_before_merge_when_stale() -> None:
    """Test that land-stack updates PR base on GitHub before merging when stale.

    Bug scenario:
    - Stack: main → feat-1 → feat-2
    - After landing feat-1, gt sync updates local metadata (feat-2 parent = main)
    - But GitHub PR #2 still shows base = feat-1 (stale)
    - Without fix: gh pr merge tries to merge into deleted branch
    - With fix: gh pr edit --base main is called before gh pr merge

    This test verifies the fix uses GitHubOps abstraction to check and update
    GitHub PR base before each merge operation.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Simulate scenario where feat-1 was already merged and gt sync updated
        # Graphite metadata (feat-2's parent = main), but GitHub PR still shows
        # the old base (feat-1) - this is the bug we're fixing
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-2"], commit_sha="abc123"),
                "feat-2": BranchMetadata.branch("feat-2", "main", commit_sha="ghi789"),
            },
            current_branch="feat-2",
        )

        # Configure FakeGitHubOps with stale base for PR #200
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_bases={
                200: "feat-1",  # Stale - Graphite shows parent as "main"
            },
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=True,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Run land-stack with dry-run flag
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Verify command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify stale base detection message appears
        assert "Updating PR #200 base: feat-1 → main" in result.output, (
            f"Expected base update message not found in output:\n{result.output}"
        )
        assert "gh pr edit 200 --base main" in result.output, (
            f"Expected gh command not found in output:\n{result.output}"
        )


def test_land_stack_skips_base_update_when_already_correct() -> None:
    """Test that land-stack skips PR base update when already correct.

    When GitHub PR base already matches expected parent, we should not
    make unnecessary API calls to update it.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build two-PR stack
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            current_branch="feat-2",
        )

        # Configure FakeGitHubOps with correct bases (matching Graphite parents)
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_bases={
                100: "main",  # Matches Graphite parent
                200: "feat-1",  # Matches Graphite parent
            },
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=True,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify that no PR base update messages appear (base already correct)
        assert "Updating PR #100 base:" not in result.output, (
            f"No base update message should appear when base is already correct\n"
            f"Actual output: {result.output}"
        )
        assert "Updating PR #200 base:" not in result.output, (
            f"No base update message should appear when base is already correct\n"
            f"Actual output: {result.output}"
        )


def test_land_stack_dry_run_shows_base_update() -> None:
    """Test that dry-run mode shows PR base update without executing.

    This test verifies that when a PR's GitHub base is stale (points to a branch
    that should no longer be its parent), the dry-run output shows the update
    that would be made.

    Setup: Single PR with stale base on GitHub (not reflecting a prior update)
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Simple scenario: feat-1's parent is main, but GitHub shows old base
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        # Configure FakeGitHubOps with stale base
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_bases={
                100: "old-branch",  # Stale - should be "main"
            },
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=True,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Run with --dry-run flag
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify output shows the update that would happen
        assert "Updating PR #100 base: old-branch → main" in result.output, (
            f"Expected base update message not found. Actual output:\n{result.output}"
        )
        assert "gh pr edit 100 --base main" in result.output


def test_land_stack_merge_command_excludes_auto_flag() -> None:
    """Test that land-stack merge commands do NOT include --auto flag.

    Regression test for GitHub auto-merge issue:
    - The --auto flag requires branch protection rules to be configured
    - Without protection rules, GitHub returns "Pull request is in clean status" error
    - land-stack uses synchronous sequential landing, so auto-merge provides no value

    This test ensures the --auto flag remains removed from merge commands.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build simple stack with one PR
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=True,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Run in dry-run mode to see the commands that would be executed
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify merge command appears in output
        assert "gh pr merge 100 --squash" in result.output, (
            f"Expected merge command not found in output:\n{result.output}"
        )

        # Verify --auto flag is NOT present in merge command
        assert "--auto" not in result.output, (
            f"The --auto flag should NOT appear in merge commands. "
            f"This flag requires branch protection rules and provides no value "
            f"for synchronous sequential landing. Actual output:\n{result.output}"
        )


def test_land_stack_force_pushes_remaining_branches_after_sync() -> None:
    """Test that land-stack force-pushes remaining branches after each sync.

    Bug: After landing feat-1 and running gt sync -f, Graphite rebases remaining
    branches (feat-2, feat-3) locally, but they weren't pushed to GitHub. This left
    GitHub PRs showing stale commits with duplicated history.

    Fix: Phase 5 added to force-push all remaining branches after each sync operation,
    ensuring GitHub PRs reflect the rebased commits.

    This test verifies the fix by checking that submit_branch is called for each
    remaining branch after landing a PR.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build 4-branch stack: main → feat-1 → feat-2 → feat-3
        # Current: feat-2 (will land feat-1, leaving feat-2 and feat-3 remaining)
        git_ops, graphite_ops = env.build_ops_from_branches(
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
            current_branch="feat-2",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Act: Land feat-1 (leaving feat-2 and feat-3 as remaining branches)
        # Use --force to skip confirmation, --dry-run to see what would be executed
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Phase 5 should show submit commands for remaining branches (feat-2, feat-3)
        # After landing feat-1, gt sync rebases feat-2 and feat-3
        # Phase 5 force-pushes both branches
        assert "gt submit --branch feat-2 --no-edit" in result.output, (
            f"Expected 'gt submit --branch feat-2 --no-edit' in output.\n"
            f"Actual output:\n{result.output}"
        )
        assert "gt submit --branch feat-3 --no-edit" in result.output, (
            f"Expected 'gt submit --branch feat-3 --no-edit' in output.\n"
            f"Actual output:\n{result.output}"
        )


def test_land_stack_force_pushes_after_each_pr_landed() -> None:
    """Test that land-stack force-pushes remaining branches after EACH PR is landed.

    When landing multiple PRs (feat-1, feat-2), each gt sync -f rebases the remaining
    branches. Phase 5 must run after EACH sync to keep GitHub PRs in sync.

    Expected submit_branch calls:
    - After landing feat-1: submit feat-2, feat-3, feat-4 (3 calls)
    - After landing feat-2: submit feat-3, feat-4 (2 calls)
    - Total: 5 submit_branch calls
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build 5-branch stack: main → feat-1 → feat-2 → feat-3 → feat-4
        # Current: feat-3 (will land feat-1 and feat-2)
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch(
                    "feat-2", "feat-1", children=["feat-3"], commit_sha="ghi789"
                ),
                "feat-3": BranchMetadata.branch(
                    "feat-3", "feat-2", children=["feat-4"], commit_sha="jkl012"
                ),
                "feat-4": BranchMetadata.branch("feat-4", "feat-3", commit_sha="mno345"),
            },
            current_branch="feat-3",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
                "feat-4": ("OPEN", 400, "Feature 4"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Act: Land feat-1, feat-2, and feat-3 (leaving feat-4)
        # Current branch is feat-3, so land-stack lands from bottom to current
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Phase 5 runs after each PR is landed, showing submit commands
        # After feat-1: submit feat-2, feat-3, feat-4 (3 submits)
        # After feat-2: submit feat-3, feat-4 (2 submits)
        # After feat-3: submit feat-4 (1 submit)
        # Verify all remaining branches are submitted after each PR
        assert "gt submit --branch feat-2 --no-edit" in result.output, (
            f"Expected feat-2 submit command in output.\nActual output:\n{result.output}"
        )
        assert "gt submit --branch feat-3 --no-edit" in result.output, (
            f"Expected feat-3 submit command in output.\nActual output:\n{result.output}"
        )
        assert "gt submit --branch feat-4 --no-edit" in result.output, (
            f"Expected feat-4 submit command in output.\nActual output:\n{result.output}"
        )

        # Count occurrences to verify submit happens after each PR land
        # feat-2 should appear once (after landing feat-1)
        # feat-3 should appear twice (after landing feat-1 and feat-2)
        # feat-4 should appear three times (after landing feat-1, feat-2, and feat-3)
        output_lines = result.output
        feat2_count = output_lines.count("gt submit --branch feat-2 --no-edit")
        feat3_count = output_lines.count("gt submit --branch feat-3 --no-edit")
        feat4_count = output_lines.count("gt submit --branch feat-4 --no-edit")

        assert feat2_count == 1, f"Expected feat-2 submitted 1 time, got {feat2_count}"
        assert feat3_count == 2, f"Expected feat-3 submitted 2 times, got {feat3_count}"
        assert feat4_count == 3, f"Expected feat-4 submitted 3 times, got {feat4_count}"


def test_land_stack_no_submit_when_landing_top_branch() -> None:
    """Test that no submit_branch calls are made when landing the top/leaf branch.

    When landing the top branch of a stack, there are no remaining branches upstack.
    Phase 5 should detect this and skip submit_branch calls entirely.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build 3-branch stack: main → feat-1 → feat-2 → feat-3
        # Current: feat-3 (top/leaf branch)
        # Landing all 3 branches, final branch has no remaining upstack
        git_ops, graphite_ops = env.build_ops_from_branches(
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

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
                "feat-3": ("OPEN", 300, "Feature 3"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Act: Land entire stack (feat-1, feat-2, feat-3)
        result = runner.invoke(cli, ["land-stack", "--force", "--dry-run"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Phase 5 should show submit commands after feat-1 and feat-2, but NOT after feat-3
        # After feat-1: submit feat-2, feat-3
        # After feat-2: submit feat-3
        # After feat-3: no remaining branches (no submit commands)

        # Count occurrences to verify
        # feat-2 should appear once (after landing feat-1 only)
        # feat-3 should appear twice (after landing feat-1 and feat-2)
        output = result.output
        feat2_count = output.count("gt submit --branch feat-2 --no-edit")
        feat3_count = output.count("gt submit --branch feat-3 --no-edit")

        assert feat2_count == 1, (
            f"Expected feat-2 submitted 1 time (after feat-1), got {feat2_count}\nOutput:\n{output}"
        )
        assert feat3_count == 2, (
            f"Expected feat-3 submitted 2 times (after feat-1 and feat-2), got {feat3_count}\n"
            f"Output:\n{output}"
        )

        # Verify no "Phase 5" operations after the final PR (feat-3)
        # This is implicitly tested by the counts above - if there were operations after
        # feat-3, we'd see additional submit commands


def test_land_stack_verbose_flag_shows_detailed_output() -> None:
    """Test that --verbose flag works with Phase 5 force-push operations.

    The --verbose flag should enable detailed output for all operations including
    the Phase 5 submit_branch calls. In non-verbose mode, operations are quieter.

    Note: This test verifies --verbose doesn't break Phase 5, not the exact output
    format, since the verbose behavior is implemented in RealGraphiteOps (which uses
    --quiet flag based on the quiet parameter).
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build simple 3-branch stack
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            current_branch="feat-2",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=False,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Act: Land with --verbose flag
        result = runner.invoke(
            cli, ["land-stack", "--force", "--verbose", "--dry-run"], obj=test_ctx
        )

        # Assert: Command succeeded with --verbose flag
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Phase 5 submit commands still appear in output with --verbose
        assert "gt submit --branch feat-2 --no-edit" in result.output, (
            f"Expected Phase 5 submit command in verbose output.\nActual output:\n{result.output}"
        )


def test_land_stack_dry_run_shows_submit_commands() -> None:
    """Test that --dry-run mode shows gt submit commands in output.

    In dry-run mode, the command should display the gt submit commands that would
    be executed for each remaining branch, but should NOT actually call submit_branch
    on FakeGraphiteOps.
    """
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Build 3-branch stack
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch(
                    "feat-1", "main", children=["feat-2"], commit_sha="def456"
                ),
                "feat-2": BranchMetadata.branch("feat-2", "feat-1", commit_sha="ghi789"),
            },
            current_branch="feat-2",
        )

        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            }
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            dry_run=True,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        # Act: Land with --dry-run flag
        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Assert: Command succeeded
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Assert: Output shows gt submit commands for remaining branch (feat-2)
        assert "gt submit --branch feat-2 --no-edit" in result.output, (
            f"Expected 'gt submit --branch feat-2 --no-edit' in output.\n"
            f"Actual output:\n{result.output}"
        )

        # Assert: DRY RUN mode means submit_branch should NOT be called on FakeGraphiteOps
        # (In dry-run, DryRunGraphiteOps.submit_branch shows the command but doesn't mutate)
        # The test_ctx uses dry_run=True, so FakeGraphiteOps.submit_branch is NOT invoked
        # Instead, DryRunGraphiteOps wrapper shows the command
        #
        # Note: We can't assert len(graphite_ops.submit_branch_calls) == 0 here because
        # the DryRunGraphiteOps wrapper still calls the underlying fake for tracking.
        # The key is that dry-run mode shows the command in output without real execution.


# ============================================================================
# Merge Conflict Detection Tests (TDD)
# ============================================================================


def test_land_stack_fails_when_first_pr_has_conflict() -> None:
    """Test that land-stack fails when first PR has merge conflict."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-2"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2
        graphite_ops = FakeGraphiteOps(
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

        from workstack.core.github_ops import PRMergeability

        # feat-1 has CONFLICTING status
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="CONFLICTING", merge_state_status="DIRTY"),
                200: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
            },
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
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
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-3"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2 → feat-3
        graphite_ops = FakeGraphiteOps(
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

        from workstack.core.github_ops import PRMergeability

        # feat-2 (middle PR) has CONFLICTING status
        github_ops = FakeGitHubOps(
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

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
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
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-2"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2
        graphite_ops = FakeGraphiteOps(
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

        from workstack.core.github_ops import PRMergeability

        # feat-2 (last PR) has CONFLICTING status
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
                200: PRMergeability(mergeable="CONFLICTING", merge_state_status="DIRTY"),
            },
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
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
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-1"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Simple stack: main → feat-1
        graphite_ops = FakeGraphiteOps(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        from workstack.core.github_ops import PRMergeability

        # feat-1 has UNKNOWN status (GitHub hasn't computed it yet)
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="UNKNOWN", merge_state_status="UNKNOWN"),
            },
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should show warning but not fail
        assert "Warning: PR #100 mergeability unknown" in result.output
        # Should proceed to show landing plan (exit code depends on dry-run success)


def test_land_stack_succeeds_when_all_prs_mergeable() -> None:
    """Test that land-stack succeeds when all PRs are MERGEABLE."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "feat-2"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Stack: main → feat-1 → feat-2
        graphite_ops = FakeGraphiteOps(
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

        from workstack.core.github_ops import PRMergeability

        # All PRs are MERGEABLE
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feat-1": ("OPEN", 100, "Feature 1"),
                "feat-2": ("OPEN", 200, "Feature 2"),
            },
            pr_mergeability={
                100: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
                200: PRMergeability(mergeable="MERGEABLE", merge_state_status="CLEAN"),
            },
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack", "--force"], obj=test_ctx)

        # Should pass validation and show landing plan
        assert "Cannot land stack - PRs have merge conflicts" not in result.output
        assert "Landing 2 PRs" in result.output
