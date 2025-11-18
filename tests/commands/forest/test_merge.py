"""Integration tests for forest merge command."""

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.forest_types import Forest, ForestMetadata
from erk.core.gitops import WorktreeInfo
from tests.fakes.forest_ops import FakeForestOps
from tests.fakes.gitops import FakeGitOps
from tests.test_utils.env_helpers import erk_inmem_env

# TODO: These tests need to use erk_isolated_fs_env instead of erk_inmem_env
# because forest commands use find_current_worktree() which requires proper
# path resolution via is_relative_to(). Sentinel paths don't work for this.


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_merge_removes_worktrees() -> None:
    """Test merge removes worktrees and forest metadata."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt1_path = worktrees_dir / "wt1"
        wt2_path = worktrees_dir / "wt2"

        git_ops = FakeGitOps(
            git_common_dirs={wt1_path: env.git_dir},
            worktrees={
                wt1_path: [
                    WorktreeInfo(path=wt1_path, branch="feat-1", is_root=False),
                    WorktreeInfo(path=wt2_path, branch="feat-2", is_root=False),
                ]
            },
            file_statuses={},  # No uncommitted changes
        )

        # Add wt1_path and wt2_path to existing paths
        git_ops._existing_paths = {wt1_path, wt2_path}

        forest_ops = FakeForestOps()
        forest = Forest(
            name="my-forest",
            worktrees=["wt1", "wt2"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"my-forest": forest}))

        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops, cwd=wt1_path)

        result = runner.invoke(cli, ["forest", "merge", "-f"], obj=ctx)

        assert result.exit_code == 0
        assert "Merge complete" in result.output

        # Verify forest removed
        metadata = forest_ops.load_forests()
        assert "my-forest" not in metadata.forests


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_merge_with_explicit_target() -> None:
    """Test merge with --into flag."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt1_path = worktrees_dir / "wt1"
        wt2_path = worktrees_dir / "wt2"

        git_ops = FakeGitOps(
            git_common_dirs={wt1_path: env.git_dir},
            worktrees={
                wt1_path: [
                    WorktreeInfo(path=wt1_path, branch="feat-1", is_root=False),
                    WorktreeInfo(path=wt2_path, branch="feat-2", is_root=False),
                ]
            },
        )

        git_ops._existing_paths = {wt1_path, wt2_path}

        forest_ops = FakeForestOps()
        forest = Forest(
            name="my-forest",
            worktrees=["wt1", "wt2"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"my-forest": forest}))

        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops, cwd=wt1_path)

        result = runner.invoke(cli, ["forest", "merge", "--into", "wt2", "-f"], obj=ctx)

        assert result.exit_code == 0


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_merge_dry_run() -> None:
    """Test merge with --dry-run doesn't remove worktrees."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt1_path = worktrees_dir / "wt1"

        git_ops = FakeGitOps(
            git_common_dirs={wt1_path: env.git_dir},
            worktrees={wt1_path: [WorktreeInfo(path=wt1_path, branch="feat-1", is_root=False)]},
        )

        forest_ops = FakeForestOps()
        forest = Forest(
            name="my-forest",
            worktrees=["wt1", "wt2"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"my-forest": forest}))

        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops, cwd=wt1_path)

        result = runner.invoke(cli, ["forest", "merge", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "dry run" in result.output

        # Verify forest not removed
        metadata = forest_ops.load_forests()
        assert "my-forest" in metadata.forests


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_merge_uncommitted_changes_error() -> None:
    """Test merge fails when worktrees have uncommitted changes."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt1_path = worktrees_dir / "wt1"
        wt2_path = worktrees_dir / "wt2"

        git_ops = FakeGitOps(
            git_common_dirs={wt1_path: env.git_dir},
            worktrees={
                wt1_path: [
                    WorktreeInfo(path=wt1_path, branch="feat-1", is_root=False),
                    WorktreeInfo(path=wt2_path, branch="feat-2", is_root=False),
                ]
            },
            file_statuses={
                wt2_path: ([], ["file.txt"], [])  # wt2 has modified files
            },
        )

        git_ops._existing_paths = {wt1_path, wt2_path}

        forest_ops = FakeForestOps()
        forest = Forest(
            name="my-forest",
            worktrees=["wt1", "wt2"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"my-forest": forest}))

        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops, cwd=wt1_path)

        result = runner.invoke(cli, ["forest", "merge", "-f"], obj=ctx)

        assert result.exit_code == 1
        assert "Uncommitted changes" in result.output


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_merge_single_worktree_nothing_to_do() -> None:
    """Test merge when forest has only one worktree."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt1_path = worktrees_dir / "wt1"

        git_ops = FakeGitOps(
            git_common_dirs={wt1_path: env.git_dir},
            worktrees={wt1_path: [WorktreeInfo(path=wt1_path, branch="feat-1", is_root=False)]},
        )

        forest_ops = FakeForestOps()
        forest = Forest(
            name="my-forest",
            worktrees=["wt1"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"my-forest": forest}))

        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops, cwd=wt1_path)

        result = runner.invoke(cli, ["forest", "merge"], obj=ctx)

        assert result.exit_code == 0
        assert "Nothing to merge" in result.output
