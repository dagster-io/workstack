"""CLI tests for trunk branch handling in list command.

This file tests CLI-specific behavior of how trunk branches are displayed
or filtered in the list command output.

The business logic of trunk detection (_is_trunk_branch function) is tested in:
- tests/unit/detection/test_trunk_detection.py

This file trusts that unit layer and only tests CLI integration.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from tests.commands.display.list import strip_ansi
from tests.fakes.gitops import FakeGitOps, WorktreeInfo
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.global_config import GlobalConfig


@pytest.mark.parametrize("trunk_branch", ["main", "master"])
def test_list_with_trunk_branch(trunk_branch: str) -> None:
    """List command handles trunk branches correctly (CLI layer)."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        graphite_cache = {
            "branches": [
                [trunk_branch, {"validationResult": "TRUNK", "children": ["feature"]}],
                ["feature", {"parentBranchName": trunk_branch, "children": []}],
            ]
        }
        (env.git_dir / ".graphite_cache_persist").write_text(
            json.dumps(graphite_cache), encoding="utf-8"
        )

        feature_dir = env.workstacks_root / env.cwd.name / "feature"
        feature_dir.mkdir(parents=True)

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

        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=False,
            show_pr_checks=False,
        )

        ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config,
            cwd=Path("/test/default/cwd"),
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=ctx)

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert trunk_branch in output or "feature" in output
