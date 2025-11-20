"""Integration tests for forest split command."""

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.git import WorktreeInfo
from tests.fakes.forest_ops import FakeForest
from tests.fakes.git import FakeGit
from tests.fakes.graphite import FakeGraphite
from tests.test_utils.env_helpers import erk_inmem_env

# TODO: These tests need to use erk_isolated_fs_env instead of erk_inmem_env
# because forest commands use find_current_worktree() which requires proper
# path resolution via is_relative_to(). Sentinel paths don't work for this.


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_split_creates_worktrees_and_forest() -> None:
    """Test split command creates worktrees and updates forest metadata."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        current_wt = worktrees_dir / "feat-1"

        git_ops = FakeGit(
            git_common_dirs={current_wt: env.git_dir},
            default_branches={current_wt: "main"},
            current_branches={current_wt: "feat-1"},
            worktrees={current_wt: [WorktreeInfo(path=current_wt, branch="feat-1", is_root=False)]},
        )

        graphite = FakeGraphite(stacks={"feat-1": ["main", "feat-1", "feat-2", "feat-3"]})

        forest_ops = FakeForest()

        ctx = env.build_context(
            git=git_ops,
            graphite=graphite,
            forest=forest_ops,
            use_graphite=True,
            cwd=current_wt,
        )

        result = runner.invoke(cli, ["forest", "split", "-f"], obj=ctx, input="y\n")

        assert result.exit_code == 0
        assert "Created" in result.output or "worktree" in result.output

        # Verify forest metadata updated
        metadata = forest_ops.load_forests()
        assert "feat-1" in metadata.forests


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_split_with_up_flag() -> None:
    """Test split with --up flag only splits upstack branches."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        current_wt = worktrees_dir / "feat-2"

        git_ops = FakeGit(
            git_common_dirs={current_wt: env.git_dir},
            current_branches={current_wt: "feat-2"},
            worktrees={current_wt: [WorktreeInfo(path=current_wt, branch="feat-2", is_root=False)]},
        )

        graphite = FakeGraphite(stacks={"feat-2": ["main", "feat-1", "feat-2", "feat-3"]})

        forest_ops = FakeForest()

        ctx = env.build_context(
            git=git_ops,
            graphite=graphite,
            forest=forest_ops,
            use_graphite=True,
            cwd=current_wt,
        )

        result = runner.invoke(cli, ["forest", "split", "--up", "-f"], obj=ctx)

        assert result.exit_code == 0


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_split_dry_run() -> None:
    """Test split with --dry-run doesn't create worktrees."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        current_wt = worktrees_dir / "feat-1"

        git_ops = FakeGit(
            git_common_dirs={current_wt: env.git_dir},
            current_branches={current_wt: "feat-1"},
            worktrees={current_wt: [WorktreeInfo(path=current_wt, branch="feat-1", is_root=False)]},
        )

        graphite = FakeGraphite(stacks={"feat-1": ["main", "feat-1", "feat-2"]})

        forest_ops = FakeForest()

        ctx = env.build_context(
            git=git_ops,
            graphite=graphite,
            forest=forest_ops,
            use_graphite=True,
            cwd=current_wt,
        )

        result = runner.invoke(cli, ["forest", "split", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "dry run" in result.output

        # Verify no forest created
        metadata = forest_ops.load_forests()
        assert len(metadata.forests) == 0


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_split_nothing_to_split() -> None:
    """Test split when only one branch in worktree."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        current_wt = worktrees_dir / "feat-1"

        git_ops = FakeGit(
            git_common_dirs={current_wt: env.git_dir},
            current_branches={current_wt: "feat-1"},
            worktrees={current_wt: [WorktreeInfo(path=current_wt, branch="feat-1", is_root=False)]},
        )

        graphite = FakeGraphite(stacks={"feat-1": ["main", "feat-1"]})

        forest_ops = FakeForest()

        ctx = env.build_context(
            git=git_ops,
            graphite=graphite,
            forest=forest_ops,
            use_graphite=True,
            cwd=current_wt,
        )

        result = runner.invoke(cli, ["forest", "split"], obj=ctx)

        assert result.exit_code == 0
        assert "Nothing to split" in result.output
