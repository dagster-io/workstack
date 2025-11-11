"""Tests for the current command using fakes (fast integration tests).

These tests use FakeGitOps with pre-configured WorktreeInfo data instead of
real git operations, providing 5-10x speedup while maintaining full CLI coverage.
"""

import os
from pathlib import Path

from click.testing import CliRunner

from tests.fakes.gitops import FakeGitOps
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo
from workstack.core.global_config import GlobalConfig, InMemoryGlobalConfigOps


def test_current_returns_worktree_name() -> None:
    """Test that current returns worktree name when in named worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktree for "feature-x"
        feature_x_path = env.create_linked_worktree("feature-x", "feature-x", chdir=True)

        # Configure FakeGitOps with worktrees - feature-x is current
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                    WorktreeInfo(path=feature_x_path, branch="feature-x", is_root=False),
                ]
            },
            current_branches={
                env.root_worktree: "main",
                feature_x_path: "feature-x",
            },
            git_common_dirs={
                env.root_worktree: env.git_dir,
                feature_x_path: env.git_dir,
            },
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context - note cwd is feature_x_path since we changed dir
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            cwd=feature_x_path,  # Current directory is the feature-x worktree
            trunk_branch="main",
        )

        # Run current command
        result = runner.invoke(cli, ["current"], obj=test_ctx)

        assert result.exit_code == 0
        assert result.output.strip() == "feature-x"


def test_current_returns_root_in_root_repository() -> None:
    """Test that current returns 'root' when in root repository."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure FakeGitOps with just root worktree
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context - cwd is root worktree
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            cwd=env.root_worktree,  # Current directory is root
            trunk_branch="main",
        )

        # Run current command
        result = runner.invoke(cli, ["current"], obj=test_ctx)

        assert result.exit_code == 0
        assert result.output.strip() == "root"


def test_current_exits_with_error_when_not_in_worktree() -> None:
    """Test that current exits with code 1 when not in any worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create a directory outside any worktree
        outside_dir = env.root_worktree.parent / "outside"
        outside_dir.mkdir()

        # Configure FakeGitOps with worktrees, but we'll run from outside
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                ]
            },
            current_branches={env.root_worktree: "main"},
            git_common_dirs={env.root_worktree: env.git_dir},
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context - cwd is outside any worktree
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            cwd=outside_dir,  # Current directory is outside any worktree
            trunk_branch="main",
        )

        # Run current command from outside directory
        os.chdir(outside_dir)
        result = runner.invoke(cli, ["current"], obj=test_ctx)

        assert result.exit_code == 1
        assert result.output.strip() == ""


def test_current_works_from_subdirectory() -> None:
    """Test that current returns worktree name from subdirectory within worktree."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Create linked worktree for "feature-y"
        feature_y_path = env.create_linked_worktree("feature-y", "feature-y", chdir=False)

        # Create subdirectory within worktree
        subdir = feature_y_path / "src" / "nested"
        subdir.mkdir(parents=True)

        # Configure FakeGitOps with worktrees
        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                    WorktreeInfo(path=feature_y_path, branch="feature-y", is_root=False),
                ]
            },
            current_branches={
                env.root_worktree: "main",
                feature_y_path: "feature-y",
            },
            git_common_dirs={
                env.root_worktree: env.git_dir,
                feature_y_path: env.git_dir,
                subdir: env.git_dir,  # Subdirectory also maps to same git dir
            },
            default_branches={env.root_worktree: "main"},
        )

        # Create global config with workstacks_root
        global_config = GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=False,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )
        global_config_ops = InMemoryGlobalConfigOps(config=global_config)

        # Create test context - cwd is subdirectory within worktree
        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config_ops=global_config_ops,
            global_config=global_config,
            cwd=subdir,  # Current directory is subdirectory
            trunk_branch="main",
        )

        # Run current command from subdirectory
        os.chdir(subdir)
        result = runner.invoke(cli, ["current"], obj=test_ctx)

        assert result.exit_code == 0
        assert result.output.strip() == "feature-y"


def test_current_handles_missing_git_gracefully(tmp_path: Path) -> None:
    """Test that current exits with code 1 when not in a git repository."""
    non_git_dir = tmp_path / "not-git"
    non_git_dir.mkdir()
    workstacks_root = tmp_path / "workstacks"

    # No git_common_dir configured = not in git repo
    git_ops = FakeGitOps(git_common_dirs={})

    # Create global config
    global_config = GlobalConfig(
        workstacks_root=workstacks_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )
    global_config_ops = InMemoryGlobalConfigOps(config=global_config)

    ctx = WorkstackContext.for_test(
        cwd=non_git_dir,
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        global_config=global_config,
        repo=None,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["current"], obj=ctx)

    assert result.exit_code == 1
    assert result.output.strip() == ""


def test_current_handles_nested_worktrees(tmp_path: Path) -> None:
    """Test that current returns deepest worktree for nested structures."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    workstacks_root = tmp_path / "workstacks"
    parent_wt = workstacks_root / "repo" / "parent"
    parent_wt.mkdir(parents=True)
    nested_wt = parent_wt / "nested"
    nested_wt.mkdir()
    target_dir = nested_wt / "src"
    target_dir.mkdir()

    # Set up nested worktrees: root contains parent, parent contains nested
    git_ops = FakeGitOps(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main", is_root=True),
                WorktreeInfo(path=parent_wt, branch="parent", is_root=False),
                WorktreeInfo(path=nested_wt, branch="nested", is_root=False),
            ]
        },
        git_common_dirs={
            target_dir: repo_root / ".git",
        },
    )

    # Create global config
    global_config = GlobalConfig(
        workstacks_root=workstacks_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )
    global_config_ops = InMemoryGlobalConfigOps(config=global_config)

    ctx = WorkstackContext.for_test(
        cwd=target_dir,
        git_ops=git_ops,
        global_config_ops=global_config_ops,
        global_config=global_config,
        trunk_branch="main",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["current"], obj=ctx)

    # Should return the deepest (most specific) worktree
    assert result.exit_code == 0
    assert result.output.strip() == "nested"
