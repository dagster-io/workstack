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
from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps, WorktreeInfo
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.cli import cli
from workstack.cli.config import LoadedConfig
from workstack.core.context import WorkstackContext
from workstack.core.global_config import GlobalConfig
from workstack.core.repo_discovery import NoRepoSentinel


@pytest.mark.parametrize("trunk_branch", ["main", "master"])
def test_list_with_trunk_branch(trunk_branch: str) -> None:
    """List command handles trunk branches correctly (CLI layer)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        git_dir = Path(".git")
        git_dir.mkdir()

        graphite_cache = {
            "branches": [
                [trunk_branch, {"validationResult": "TRUNK", "children": ["feature"]}],
                ["feature", {"parentBranchName": trunk_branch, "children": []}],
            ]
        }
        (git_dir / ".graphite_cache_persist").write_text(
            json.dumps(graphite_cache), encoding="utf-8"
        )

        workstacks_root = cwd / "workstacks"
        feature_dir = workstacks_root / cwd.name / "feature"
        feature_dir.mkdir(parents=True)

        git_ops = FakeGitOps(
            worktrees={
                cwd: [
                    WorktreeInfo(path=cwd, branch=trunk_branch),
                    WorktreeInfo(path=feature_dir, branch="feature"),
                ],
            },
            git_common_dirs={cwd: git_dir, feature_dir: git_dir},
            current_branches={cwd: trunk_branch, feature_dir: "feature"},
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=False,
            show_pr_checks=False,
        )

        ctx = WorkstackContext(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=FakeGraphiteOps(),
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            repo_config=LoadedConfig(env={}, post_create_commands=[], post_create_shell=None),
            repo=NoRepoSentinel(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["list", "--stacks"], obj=ctx)

        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert trunk_branch in output or "feature" in output
