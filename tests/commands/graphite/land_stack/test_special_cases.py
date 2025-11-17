"""Tests for land-stack special cases and edge conditions."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import ErkContext
from erk.core.github_ops import PullRequestInfo
from erk.core.gitops import WorktreeInfo
from erk.core.global_config import GlobalConfig
from erk.core.graphite_ops import BranchMetadata
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import pure_workstack_env


def test_land_stack_ignores_root_worktree_changes_on_unrelated_branch() -> None:
    """Test that land-stack doesn't check root worktree when it's on unrelated branch."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Set up two worktrees:
        # - Root worktree: on branch "test-docs" with uncommitted changes
        # - Current worktree: on branch "feat-1" (clean)
        root_path = Path("/root")
        current_path = env.cwd

        from tests.fakes.gitops import FakeGitOps

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
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
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

        test_ctx = ErkContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(
                pr_statuses={
                    "feat-1": ("OPEN", 123, "Add feature 1"),
                },
                pr_bases={
                    123: "main",
                },
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


def test_land_stack_script_mode_accepts_flag() -> None:
    """Verify land-stack accepts --script flag for shell integration."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Build test environment with a simple stack
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
                "feature-1": BranchMetadata.branch("feature-1", "main", commit_sha="def456"),
            },
            current_branch="feature-1",
        )

        # Setup GitHub ops with an open PR
        github_ops = FakeGitHubOps(
            pr_statuses={"feature-1": ("OPEN", 123, "Feature 1")},
            pr_bases={
                123: "main",
            },
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        test_ctx = ErkContext.for_test(
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
