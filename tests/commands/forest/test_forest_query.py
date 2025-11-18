"""Integration tests for forest query commands."""

import pytest
from click.testing import CliRunner
from tests.fakes.forest_ops import FakeForestOps
from tests.fakes.gitops import FakeGitOps
from tests.test_utils.env_helpers import erk_inmem_env

from erk.cli.cli import cli
from erk.core.forest_types import Forest, ForestMetadata
from erk.core.gitops import WorktreeInfo

# TODO: These tests need to use erk_isolated_fs_env instead of erk_inmem_env
# because forest commands use find_current_worktree() which requires proper
# path resolution via is_relative_to(). Sentinel paths don't work for this.
# See: https://github.com/anthropics/erk/issues/XXX


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_forest_show_current_in_forest() -> None:
    """Test showing current forest when in a forest."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt_path = worktrees_dir / "my-worktree"

        git_ops = FakeGitOps(
            git_common_dirs={wt_path: env.git_dir},
            default_branches={wt_path: "main"},
            worktrees={wt_path: [WorktreeInfo(path=wt_path, branch="feat-1", is_root=False)]},
        )

        forest_ops = FakeForestOps()
        forest = Forest(
            name="my-forest",
            worktrees=["my-worktree", "other-wt"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"my-forest": forest}))

        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops, cwd=wt_path)

        result = runner.invoke(cli, ["forest"], obj=ctx)

        assert result.exit_code == 0
        assert "Forest: my-forest" in result.output
        assert "you are here" in result.output


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_forest_show_current_not_in_forest() -> None:
    """Test showing current forest when not in a forest."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt_path = worktrees_dir / "my-worktree"

        git_ops = FakeGitOps(
            git_common_dirs={wt_path: env.git_dir},
            worktrees={wt_path: [WorktreeInfo(path=wt_path, branch="feat-1", is_root=False)]},
        )

        forest_ops = FakeForestOps()
        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops, cwd=wt_path)

        result = runner.invoke(cli, ["forest"], obj=ctx)

        assert result.exit_code == 0
        assert "not in a forest" in result.output


def test_forest_list_multiple() -> None:
    """Test listing multiple forests."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        forest_ops = FakeForestOps()
        forests = {
            "forest1": Forest(
                name="forest1",
                worktrees=["wt1", "wt2"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
            "forest2": Forest(
                name="forest2",
                worktrees=["wt3"],
                created_at="2025-01-02T00:00:00Z",
                root_branch="main",
            ),
        }
        forest_ops.save_forests(ForestMetadata(forests=forests))

        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops)

        result = runner.invoke(cli, ["forest", "list"], obj=ctx)

        assert result.exit_code == 0
        assert "forest1" in result.output
        assert "forest2" in result.output
        assert "2 worktrees" in result.output
        assert "1 worktree" in result.output or "1 worktrees" in result.output


def test_forest_list_empty() -> None:
    """Test listing forests when none exist."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
        )

        forest_ops = FakeForestOps()
        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops)

        result = runner.invoke(cli, ["forest", "list"], obj=ctx)

        assert result.exit_code == 0
        assert "No forests" in result.output


@pytest.mark.skip(reason="TODO: Needs erk_isolated_fs_env for path resolution")
def test_forest_show_specific() -> None:
    """Test showing specific forest by name."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
        )

        forest_ops = FakeForestOps()
        forest = Forest(
            name="target-forest",
            worktrees=["wt1", "wt2"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"target-forest": forest}))

        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops)

        result = runner.invoke(cli, ["forest", "show", "target-forest"], obj=ctx)

        assert result.exit_code == 0
        assert "Forest: target-forest" in result.output
        assert "wt1" in result.output
        assert "wt2" in result.output


def test_forest_show_nonexistent() -> None:
    """Test showing nonexistent forest."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
        )

        forest_ops = FakeForestOps()
        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops)

        result = runner.invoke(cli, ["forest", "show", "nonexistent"], obj=ctx)

        assert result.exit_code == 1
        assert "not found" in result.output


def test_forest_rename_success() -> None:
    """Test renaming a forest."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
        )

        forest_ops = FakeForestOps()
        forest = Forest(
            name="old-name",
            worktrees=["wt1"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"old-name": forest}))

        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops)

        result = runner.invoke(cli, ["forest", "rename", "old-name", "new-name"], obj=ctx)

        assert result.exit_code == 0
        assert "Renamed" in result.output
        assert "paths remain unchanged" in result.output

        # Verify metadata updated
        metadata = forest_ops.load_forests()
        assert "new-name" in metadata.forests
        assert "old-name" not in metadata.forests


def test_forest_rename_conflict() -> None:
    """Test renaming to existing forest name."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
        )

        forest_ops = FakeForestOps()
        forests = {
            "forest1": Forest(
                name="forest1",
                worktrees=["wt1"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
            "forest2": Forest(
                name="forest2",
                worktrees=["wt2"],
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
        }
        forest_ops.save_forests(ForestMetadata(forests=forests))

        ctx = env.build_context(git_ops=git_ops, forest_ops=forest_ops)

        result = runner.invoke(cli, ["forest", "rename", "forest1", "forest2"], obj=ctx)

        assert result.exit_code == 1
        assert "already exists" in result.output
