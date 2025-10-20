"""CLI tests for workstack status command.

This file focuses on CLI-specific concerns for the status command:
- Command execution and exit codes
- Output formatting and display
- Path resolution (subdirectories, worktree detection)
- Error handling and messages

The status command orchestrates multiple collectors (git, PR, stack, plan).
The business logic of these collectors is tested in their respective unit test files:
- tests/unit/status/test_github_pr_collector.py - PR collector logic
- tests/unit/status/test_graphite_stack_collector.py - Stack collector logic
- tests/unit/status/test_plan_collector.py - Plan collector logic
- tests/unit/status/test_orchestrator.py - Collector orchestration

This file trusts that unit layer and only tests CLI integration.
"""

import os
from pathlib import Path

from click.testing import CliRunner

from tests.fakes.context import create_test_context
from tests.fakes.gitops import FakeGitOps, WorktreeInfo
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.test_utils.builders import WorktreeScenario
from workstack.cli.commands.status import status_cmd


def test_status_cmd_in_main_worktree(simple_repo: WorktreeScenario) -> None:
    """Test status command when in the main worktree (CLI layer)."""
    runner = CliRunner()
    original_dir = os.getcwd()
    os.chdir(simple_repo.repo_root)

    try:
        result = runner.invoke(status_cmd, obj=simple_repo.ctx, catch_exceptions=False)
    finally:
        os.chdir(original_dir)

    # Assert - CLI integration
    assert result.exit_code == 0
    assert "main" in result.output
    assert "Git Status:" in result.output


def test_status_cmd_in_feature_worktree(repo_with_feature: WorktreeScenario) -> None:
    """Test status command when in a feature worktree (CLI layer)."""
    runner = CliRunner()
    worktree_path = repo_with_feature.workstacks_dir / "feature"
    original_dir = os.getcwd()
    os.chdir(worktree_path)

    try:
        result = runner.invoke(status_cmd, obj=repo_with_feature.ctx, catch_exceptions=False)
    finally:
        os.chdir(original_dir)

    # Assert - CLI integration
    assert result.exit_code == 0
    assert "feature" in result.output
    assert "Git Status:" in result.output


def test_status_cmd_in_subdirectory_of_worktree(tmp_path: Path) -> None:
    """Test status command finds worktree when run from subdirectory (CLI layer)."""
    # Arrange - Create subdirectory structure
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    git_dir = repo_root / ".git"
    git_dir.mkdir()

    worktree_path = tmp_path / "workstacks" / "repo" / "feature"
    worktree_path.mkdir(parents=True)
    subdir = worktree_path / "src" / "nested"
    subdir.mkdir(parents=True)

    git_ops = FakeGitOps(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=worktree_path, branch="feature"),
            ]
        },
        current_branches={worktree_path: "feature", subdir: "feature"},
        git_common_dirs={worktree_path: git_dir, subdir: git_dir},
        file_statuses={worktree_path: ([], [], []), subdir: ([], [], [])},
        ahead_behind={(worktree_path, "feature"): (0, 0), (subdir, "feature"): (0, 0)},
        recent_commits={worktree_path: [], subdir: []},
    )
    global_config_ops = FakeGlobalConfigOps(
        workstacks_root=tmp_path / "workstacks",
        use_graphite=False,
        show_pr_info=False,
    )
    ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

    runner = CliRunner()
    original_dir = os.getcwd()
    os.chdir(subdir)  # Run from nested subdirectory

    try:
        result = runner.invoke(status_cmd, obj=ctx, catch_exceptions=False)
    finally:
        os.chdir(original_dir)

    # Assert - Should find worktree and succeed
    assert result.exit_code == 0
    assert "feature" in result.output


def test_status_cmd_displays_all_collector_sections(tmp_path: Path) -> None:
    """Smoke test: status command integrates all collectors (CLI layer).

    This is a thin integration test that verifies all collector outputs appear in
    the CLI display. The actual collector logic is tested in unit layer.
    """
    # Arrange - Use WorktreeScenario builder for cleaner setup
    scenario = (
        WorktreeScenario(tmp_path)
        .with_main_branch()
        .with_feature_branch("feature")
        .with_pr("feature", number=123, checks_passing=True)
        .with_graphite_stack(["main", "feature"])
    )

    # Create .PLAN.md file
    plan_file = scenario.workstacks_dir / "feature" / ".PLAN.md"
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.write_text("# Feature Plan\n## Overview\nImplement new feature", encoding="utf-8")

    scenario = scenario.build()

    runner = CliRunner()
    original_dir = os.getcwd()
    os.chdir(scenario.workstacks_dir / "feature")

    try:
        result = runner.invoke(status_cmd, obj=scenario.ctx, catch_exceptions=False)
    finally:
        os.chdir(original_dir)

    # Assert - Just verify sections are present (trust unit layer for content)
    assert result.exit_code == 0
    assert "Git Status:" in result.output
    assert "#123" in result.output or "123" in result.output  # PR section
    assert "Stack:" in result.output or "Graphite" in result.output  # Stack section
    assert "Plan:" in result.output or "Feature Plan" in result.output  # Plan section


def test_status_cmd_not_in_git_repo(tmp_path: Path) -> None:
    """Test status command fails when not in a git repository (error handling)."""
    # Arrange
    non_git_dir = tmp_path / "not-a-repo"
    non_git_dir.mkdir()

    git_ops = FakeGitOps(
        git_common_dirs={},  # No git directories
        worktrees={},
    )

    global_config_ops = FakeGlobalConfigOps(
        workstacks_root=tmp_path / "workstacks",
    )

    ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

    runner = CliRunner()
    original_dir = os.getcwd()
    os.chdir(non_git_dir)

    try:
        result = runner.invoke(status_cmd, obj=ctx)
    finally:
        os.chdir(original_dir)

    # Assert - CLI error handling
    assert result.exit_code != 0
