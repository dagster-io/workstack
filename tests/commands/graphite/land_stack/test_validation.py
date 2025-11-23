"""Tests for land-stack validation phase."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.branch_metadata import BranchMetadata
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.git.abc import WorktreeInfo
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from erk.core.github.types import PullRequestInfo
from erk.core.graphite.fake import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_inmem_env


def test_land_stack_requires_graphite() -> None:
    """Test that land-stack command requires Graphite to be enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
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
            erk_root=env.erk_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
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
    with erk_inmem_env(runner) as env:
        # current_branches={env.cwd: None} indicates detached HEAD
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch=None),
                ],
            },
            current_branches={env.cwd: None},
            existing_paths={env.cwd, env.git_dir},
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        graphite_ops = FakeGraphite()

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
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
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                ],
            },
            current_branches={env.cwd: "feat-1"},
            file_statuses={env.cwd: (["file.txt"], [], [])},  # Has staged changes
            existing_paths={env.cwd, env.git_dir},
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
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
    with erk_inmem_env(runner) as env:
        # Set up two worktrees:
        # - Root worktree: on branch "test-docs" with uncommitted changes
        # - Current worktree: on branch "feat-1" (clean)
        root_path = Path("/root")
        current_path = env.cwd

        git_ops = FakeGit(
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

        graphite_ops = FakeGraphite(
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
                    title=None,
                    checks_passing=True,
                    owner="owner",
                    repo="repo",
                ),
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=FakeGitHub(
                pr_statuses={
                    "feat-1": ("OPEN", 123, "Add feature 1"),
                }
            ),
            shell=FakeShell(),
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
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "main"},
            existing_paths={env.cwd, env.git_dir},
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            },
            stacks={
                "main": ["main"],
            },
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
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
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
            current_branches={env.cwd: "untracked-branch"},
            existing_paths={env.cwd, env.git_dir},
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        # Branch not in graphite stack
        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", commit_sha="abc123"),
            },
            stacks={},
        )

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
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

        graphite_ops = FakeGraphite(
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
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("NONE", None, None),
                "feat-2": ("OPEN", 123, "Add feature 2"),
            }
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

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "No PR found" in result.output
        assert "feat-1" in result.output


def test_land_stack_fails_when_pr_closed() -> None:
    """Test that land-stack fails when a branch's PR is closed."""
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

        graphite_ops = FakeGraphite(
            branches={
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            stacks={
                "feat-1": ["main", "feat-1"],
            },
        )

        # feat-1 PR is closed
        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("CLOSED", 100, "Closed feature"),
            }
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

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        assert result.exit_code == 1
        assert "closed" in result.output


def test_land_stack_excludes_current_branch_from_worktree_conflicts() -> None:
    """Test that current branch in current worktree is not flagged as conflict."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Current worktree has feat-1 checked out (which is in the stack)
        # This should NOT be considered a conflict
        git_ops, graphite_ops = env.build_ops_from_branches(
            {
                "main": BranchMetadata.trunk("main", children=["feat-1"], commit_sha="abc123"),
                "feat-1": BranchMetadata.branch("feat-1", "main", commit_sha="def456"),
            },
            current_branch="feat-1",
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        github_ops = FakeGitHub(
            pr_statuses={
                "feat-1": ("OPEN", 123, "Add feature 1"),
            },
            pr_bases={
                123: "main",
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
            dry_run=True,
        )

        result = runner.invoke(cli, ["land-stack", "--dry-run"], obj=test_ctx)

        # Should NOT fail with worktree conflict error
        assert "branches are checked out in multiple worktrees" not in result.output


def test_land_stack_detects_worktree_conflicts_in_other_worktrees() -> None:
    """Test that branches in OTHER worktrees are correctly flagged as conflicts."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Set up two worktrees:
        # - Current worktree (env.cwd): feat-1 (current branch, OK)
        # - Other worktree: feat-2 (conflict!)
        other_worktree = Path("/other/worktree")

        git_ops = FakeGit(
            git_common_dirs={
                env.cwd: env.git_dir,
                other_worktree: env.git_dir,
            },
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="feat-1", is_root=True),
                    WorktreeInfo(path=other_worktree, branch="feat-2", is_root=False),
                ],
                other_worktree: [
                    WorktreeInfo(path=env.cwd, branch="feat-1", is_root=True),
                    WorktreeInfo(path=other_worktree, branch="feat-2", is_root=False),
                ],
            },
            current_branches={
                env.cwd: "feat-1",
                other_worktree: "feat-2",
            },
            existing_paths={env.cwd, env.git_dir, other_worktree},
        )

        global_config_ops = GlobalConfig(
            erk_root=env.erk_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
        )

        graphite_ops = FakeGraphite(
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

        test_ctx = ErkContext.for_test(
            git=git_ops,
            global_config=global_config_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["land-stack"], obj=test_ctx)

        # Should fail with worktree conflict error
        assert result.exit_code == 1
        assert "branches are checked out in multiple worktrees" in result.output
        # Should mention feat-2 (the conflict), but NOT feat-1 (current branch)
        assert "feat-2" in result.output
        assert str(other_worktree) in result.output
        # Make sure feat-1 is NOT listed as a conflict
        # Check that feat-1 doesn't appear in the conflict listing
        conflict_section_started = False
        for line in result.output.split("\n"):
            if "checked out in other worktrees" in line:
                conflict_section_started = True
            if conflict_section_started and "feat-1" in line and "•" in line:
                # feat-1 should not be listed as a conflict
                msg = "feat-1 should not be listed as worktree conflict"
                raise AssertionError(msg)
