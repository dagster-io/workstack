"""Integration tests for forest auto-cleanup in sync command."""

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.forest_types import Forest as ForestData
from erk.core.forest_types import ForestMetadata
from erk.core.git import WorktreeInfo
from tests.fakes.forest_ops import FakeForest
from tests.fakes.git import FakeGit
from tests.fakes.graphite import FakeGraphite
from tests.test_utils.env_helpers import erk_inmem_env

# TODO: These tests need proper repo context setup with forest_ops integration


@pytest.mark.skip(reason="TODO: Needs proper repo context setup")
def test_sync_removes_empty_forests() -> None:
    """Test sync removes forests with no worktrees."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )

        graphite_ops = FakeGraphite()

        forest_ops = FakeForest()

        # Create forests - one empty, one with worktrees
        forests = {
            "empty-forest": ForestData(
                name="empty-forest",
                worktrees=["deleted-wt"],  # This worktree doesn't exist
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
            "full-forest": ForestData(
                name="full-forest",
                worktrees=["main"],  # Root worktree exists
                created_at="2025-01-01T00:00:00Z",
                root_branch="main",
            ),
        }
        forest_ops.save_forests(ForestMetadata(forests=forests))

        ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            forest=forest_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["sync"], obj=ctx)

        assert result.exit_code == 0
        assert "Cleaned up empty forests" in result.output

        # Verify empty forest removed
        metadata = forest_ops.load_forests()
        assert "empty-forest" not in metadata.forests
        assert "full-forest" in metadata.forests


def test_sync_preserves_non_empty_forests() -> None:
    """Test sync doesn't remove forests with existing worktrees."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        wt_path = worktrees_dir / "my-wt"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=wt_path, branch="feat-1", is_root=False),
                ]
            },
        )

        graphite_ops = FakeGraphite()

        forest_ops = FakeForest()
        forest = ForestData(
            name="active-forest",
            worktrees=["my-wt"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"active-forest": forest}))

        ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            forest=forest_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["sync"], obj=ctx)

        assert result.exit_code == 0

        # Verify forest preserved
        metadata = forest_ops.load_forests()
        assert "active-forest" in metadata.forests


def test_sync_no_forests_no_cleanup_message() -> None:
    """Test sync with no forests doesn't show cleanup message."""
    runner = CliRunner()

    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main", is_root=True)]},
        )

        graphite_ops = FakeGraphite()
        forest_ops = FakeForest()

        ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            forest=forest_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["sync"], obj=ctx)

        assert result.exit_code == 0
        assert "Cleaned up empty forests" not in result.output
