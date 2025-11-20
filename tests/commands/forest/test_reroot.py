"""Integration tests for forest reroot command."""

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.forest_types import Forest, ForestMetadata, RerootState
from erk.core.git import WorktreeInfo
from tests.fakes.forest_ops import FakeForest
from tests.fakes.git import FakeGit
from tests.fakes.graphite import FakeGraphite
from tests.test_utils.env_helpers import erk_inmem_env


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_reroot_clean_success() -> None:
    """Test reroot with no conflicts."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt1_path = worktrees_dir / "feat-1"
        wt2_path = worktrees_dir / "feat-2"

        git_ops = FakeGit(
            git_common_dirs={wt1_path: env.git_dir},
            current_branches={wt1_path: "feat-1"},
            worktrees={
                wt1_path: [
                    WorktreeInfo(path=wt1_path, branch="feat-1", is_root=False),
                    WorktreeInfo(path=wt2_path, branch="feat-2", is_root=False),
                ]
            },
            file_statuses={},  # No uncommitted changes
        )

        graphite = FakeGraphite(
            stacks={"feat-1": ["main", "feat-1", "feat-2"]},
        )

        forest_ops = FakeForest()
        forest = Forest(
            name="my-forest",
            worktrees=["feat-1", "feat-2"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"my-forest": forest}))

        ctx = env.build_context(
            git=git_ops,
            graphite=graphite,
            forest=forest_ops,
            use_graphite=True,
            cwd=wt1_path,
        )

        result = runner.invoke(cli, ["forest", "reroot", "-f"], obj=ctx)

        assert result.exit_code == 0
        assert "complete" in result.output.lower()


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_reroot_dry_run() -> None:
    """Test reroot with --dry-run doesn't execute."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt1_path = worktrees_dir / "feat-1"

        git_ops = FakeGit(
            git_common_dirs={wt1_path: env.git_dir},
            current_branches={wt1_path: "feat-1"},
            worktrees={wt1_path: [WorktreeInfo(path=wt1_path, branch="feat-1", is_root=False)]},
        )

        graphite = FakeGraphite(
            stacks={"feat-1": ["main", "feat-1"]},
        )

        forest_ops = FakeForest()
        forest = Forest(
            name="my-forest",
            worktrees=["feat-1"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"my-forest": forest}))

        ctx = env.build_context(
            git=git_ops,
            graphite=graphite,
            forest=forest_ops,
            use_graphite=True,
            cwd=wt1_path,
        )

        result = runner.invoke(cli, ["forest", "reroot", "--dry-run"], obj=ctx)

        assert result.exit_code == 0
        assert "dry run" in result.output

        # Verify no state saved
        assert forest_ops.load_reroot_state() is None


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_reroot_graphite_not_enabled() -> None:
    """Test reroot fails when Graphite not enabled."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
        )

        forest_ops = FakeForest()

        ctx = env.build_context(
            git=git_ops,
            forest=forest_ops,
            use_graphite=False,  # Graphite disabled
        )

        result = runner.invoke(cli, ["forest", "reroot"], obj=ctx)

        assert result.exit_code == 1
        assert "requires Graphite" in result.output


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_reroot_uncommitted_changes_error() -> None:
    """Test reroot fails with uncommitted changes."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt1_path = worktrees_dir / "feat-1"

        git_ops = FakeGit(
            git_common_dirs={wt1_path: env.git_dir},
            current_branches={wt1_path: "feat-1"},
            file_statuses={
                wt1_path: ([], ["file.txt"], [])  # Has uncommitted changes
            },
        )

        forest_ops = FakeForest()
        forest = Forest(
            name="my-forest",
            worktrees=["feat-1"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"my-forest": forest}))

        ctx = env.build_context(
            git=git_ops,
            forest=forest_ops,
            use_graphite=True,
            cwd=wt1_path,
        )

        result = runner.invoke(cli, ["forest", "reroot"], obj=ctx)

        assert result.exit_code == 1
        assert "Uncommitted changes" in result.output


def test_reroot_continue_no_state_error() -> None:
    """Test --continue without active rebase shows error."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
        )

        forest_ops = FakeForest()

        ctx = env.build_context(git=git_ops, forest=forest_ops, use_graphite=True)

        result = runner.invoke(cli, ["forest", "reroot", "--continue"], obj=ctx)

        assert result.exit_code == 1
        assert "No rebase state found" in result.output


def test_reroot_abort_no_state_error() -> None:
    """Test --abort without active rebase shows error."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
        )

        forest_ops = FakeForest()

        ctx = env.build_context(git=git_ops, forest=forest_ops, use_graphite=True)

        result = runner.invoke(cli, ["forest", "reroot", "--abort"], obj=ctx)

        assert result.exit_code == 1
        assert "No rebase in progress" in result.output


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_reroot_abort_clears_state() -> None:
    """Test --abort clears reroot state."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt1_path = worktrees_dir / "feat-1"

        git_ops = FakeGit(
            git_common_dirs={wt1_path: env.git_dir},
            worktrees={wt1_path: [WorktreeInfo(path=wt1_path, branch="feat-1", is_root=False)]},
        )

        forest_ops = FakeForest()

        # Set up existing state
        state = RerootState(
            forest="my-forest",
            current_branch="feat-1",
            parent_branch="main",
            parent_sha="abc123",
            remaining_branches=["feat-2"],
            paused_on_conflicts=True,
            started_at="2025-01-01T00:00:00Z",
        )
        forest_ops.save_reroot_state(state)

        ctx = env.build_context(git=git_ops, forest=forest_ops, use_graphite=True, cwd=wt1_path)

        result = runner.invoke(cli, ["forest", "reroot", "--abort"], obj=ctx)

        assert result.exit_code == 0
        assert "aborted" in result.output.lower()

        # Verify state cleared
        assert forest_ops.load_reroot_state() is None
