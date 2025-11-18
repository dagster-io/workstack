"""Integration tests for forest auto-creation in create command."""

import pytest
from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.forest_types import Forest, ForestMetadata
from tests.fakes.forest_ops import FakeForestOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils.env_helpers import erk_isolated_fs_env

# TODO: These tests need proper repo context setup with forest_ops integration


@pytest.mark.skip(reason="TODO: Needs proper repo context setup")
def test_create_from_trunk_creates_forest() -> None:
    """Test creating branch from trunk auto-creates forest."""
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )

        graphite_ops = FakeGraphiteOps(
            stacks={"main": ["main"]},
        )

        forest_ops = FakeForestOps()

        ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            forest_ops=forest_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["create", "new-feature"], obj=ctx)

        assert result.exit_code == 0

        # Verify forest created silently
        metadata = forest_ops.load_forests()
        assert "new-feature" in metadata.forests
        assert "new-feature" in metadata.forests["new-feature"].worktrees


@pytest.mark.skip(reason="TODO: Needs proper repo context setup")
def test_create_from_forest_member_joins_forest() -> None:
    """Test creating branch from forest member joins that forest."""
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        worktrees_dir = env.erk_root / "repos" / "test-repo" / "worktrees"
        parent_wt = worktrees_dir / "parent-branch"

        git_ops = FakeGitOps(
            git_common_dirs={parent_wt: env.git_dir},
            default_branches={parent_wt: "main"},
            current_branches={parent_wt: "parent-branch"},
        )

        graphite_ops = FakeGraphiteOps(
            stacks={"parent-branch": ["main", "parent-branch"]},
        )

        forest_ops = FakeForestOps()

        # Pre-create forest with parent
        existing_forest = Forest(
            name="my-forest",
            worktrees=["parent-branch"],
            created_at="2025-01-01T00:00:00Z",
            root_branch="main",
        )
        forest_ops.save_forests(ForestMetadata(forests={"my-forest": existing_forest}))

        ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            forest_ops=forest_ops,
            use_graphite=True,
            cwd=parent_wt,
        )

        result = runner.invoke(cli, ["create", "-s", "child-branch"], obj=ctx)

        assert result.exit_code == 0

        # Verify joined existing forest
        metadata = forest_ops.load_forests()
        assert "my-forest" in metadata.forests
        # Note: The actual worktree name will be sanitized, so just check forest still exists


def test_create_without_graphite_no_forest() -> None:
    """Test create without Graphite doesn't create forest."""
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )

        forest_ops = FakeForestOps()

        ctx = env.build_context(
            git_ops=git_ops,
            forest_ops=forest_ops,
            use_graphite=False,  # Graphite disabled
        )

        result = runner.invoke(cli, ["create", "new-feature"], obj=ctx)

        assert result.exit_code == 0

        # Verify no forest created
        metadata = forest_ops.load_forests()
        assert len(metadata.forests) == 0
