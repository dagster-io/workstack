"""CLI tests for trunk branch handling in list command.

This file tests CLI-specific behavior of how trunk branches are displayed
or filtered in the list command output.

The business logic of trunk detection (_is_trunk_branch function) is tested in:
- tests/unit/detection/test_trunk_detection.py

This file trusts that unit layer and only tests CLI integration.
"""

import pytest
from click.testing import CliRunner

from tests.commands.display.list import strip_ansi
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.test_utils.env_helpers import pure_workstack_env
from workstack.cli.cli import cli
from workstack.core.gitops import WorktreeInfo
from workstack.core.graphite_ops import BranchMetadata


@pytest.mark.parametrize("trunk_branch", ["main", "master"])
def test_list_with_trunk_branch(trunk_branch: str) -> None:
    """List command handles trunk branches correctly (CLI layer)."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Construct sentinel path without filesystem operations
        feature_dir = env.workstacks_root / env.cwd.name / "feature"

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch=trunk_branch),
                    WorktreeInfo(path=feature_dir, branch="feature"),
                ],
            },
            git_common_dirs={env.cwd: env.git_dir, feature_dir: env.git_dir},
            current_branches={env.cwd: trunk_branch, feature_dir: "feature"},
        )

        # Configure FakeGraphiteOps with branch metadata instead of writing cache file
        graphite_ops = FakeGraphiteOps(
            branches={
                trunk_branch: BranchMetadata.trunk(trunk_branch, children=["feature"]),
                "feature": BranchMetadata.branch("feature", trunk_branch, children=[]),
            }
        )

        ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            repo=env.repo,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=ctx)

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert trunk_branch in output or "feature" in output
