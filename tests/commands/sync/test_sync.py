"""Tests for the sync command."""

import os
import subprocess
from pathlib import Path

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.cli import cli
from workstack.cli.commands.shell_integration import hidden_shell_cmd
from workstack.cli.commands.sync import sync_cmd
from workstack.cli.shell_utils import render_cd_script
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo
from workstack.core.global_config import GlobalConfig


def _test_sentinel_path() -> Path:
    """Return sentinel path for tests that don't need real filesystem.

    Exploration: Investigating pattern where tests use fake paths to eliminate
    filesystem dependencies when only validating CLI logic (exit codes, messages).
    """
    return Path("/test/sentinel/sync")


def test_sync_requires_graphite() -> None:
    """Test that sync command requires Graphite to be enabled."""
    runner = CliRunner()
    cwd = _test_sentinel_path()
    workstacks_root = cwd / "workstacks"

    # Create minimal git repo structure
    repo_root = cwd

    git_ops = FakeGitOps(
        git_common_dirs={cwd: cwd / ".git"},
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
            ],
        },
    )

    # use_graphite=False: Test that graphite is required
    global_config_ops = GlobalConfig(
        workstacks_root=workstacks_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
        show_pr_checks=False,
    )

    graphite_ops = FakeGraphiteOps()

    test_ctx = WorkstackContext.for_test(
        git_ops=git_ops,
        global_config=global_config_ops,
        graphite_ops=graphite_ops,
        github_ops=FakeGitHubOps(),
        shell_ops=FakeShellOps(),
        cwd=cwd,
        dry_run=False,
    )

    result = runner.invoke(cli, ["sync"], obj=test_ctx)

    assert result.exit_code == 1
    assert "requires Graphite" in result.output


def test_sync_runs_gt_sync_from_root() -> None:
    """Test that sync runs gt sync from root worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Create repo structure
        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync"], obj=test_ctx)

        assert result.exit_code == 0
        # Note: "Running: gt sync" message only appears with --verbose flag

        # Verify sync was called with correct arguments
        assert len(graphite_ops.sync_calls) == 1
        cwd_arg, force_arg, quiet_arg = graphite_ops.sync_calls[0]
        assert cwd_arg == repo_root
        assert force_arg is False
        assert quiet_arg is True  # Default is quiet mode


def test_sync_with_force_flag() -> None:
    """Test that sync passes --force flag to gt sync."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "-f"], obj=test_ctx)

        assert result.exit_code == 0
        # Note: "Running: gt sync -f" message only appears with --verbose flag

        # Verify -f was passed
        assert len(graphite_ops.sync_calls) == 1
        _cwd_arg, force_arg, quiet_arg = graphite_ops.sync_calls[0]
        assert force_arg is True
        assert quiet_arg is True  # Default is quiet mode


def test_sync_handles_gt_not_installed() -> None:
    """Test that sync handles gt command not found."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Configure graphite_ops to raise FileNotFoundError
        graphite_ops = FakeGraphiteOps(sync_raises=FileNotFoundError())

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync"], obj=test_ctx)

        assert result.exit_code == 1
        assert "'gt' command not found" in result.output
        assert "brew install" in result.output


def test_sync_handles_gt_sync_failure() -> None:
    """Test that sync handles gt sync failure."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        # Configure graphite_ops to raise CalledProcessError
        graphite_ops = FakeGraphiteOps(
            sync_raises=subprocess.CalledProcessError(128, ["gt", "sync"])
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync"], obj=test_ctx)

        assert result.exit_code == 128
        assert "gt sync failed: exit code 128" in result.output


def test_sync_identifies_deletable_workstacks() -> None:
    """Test that sync identifies merged/closed workstacks."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_name = cwd.name
        workstacks_dir = workstacks_root / repo_name
        workstacks_dir.mkdir(parents=True)

        repo_root = cwd
        (repo_root / ".git").mkdir()

        # Create worktree directories under workstacks_dir
        wt1 = workstacks_dir / "feature-1"
        wt2 = workstacks_dir / "feature-2"
        wt1.mkdir()
        wt2.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                    WorktreeInfo(path=wt2, branch="feature-2"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()

        # feature-1 is merged, feature-2 is open
        github_ops = FakeGitHubOps(
            pr_statuses={
                "feature-1": ("MERGED", 123, "Feature 1"),
                "feature-2": ("OPEN", 124, "Feature 2"),
            }
        )

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        # User cancels (just want to see the list, not actually delete)
        result = runner.invoke(cli, ["sync"], obj=test_ctx, input="n\n")

        assert result.exit_code == 0
        assert "feature-1" in result.output
        assert "merged" in result.output
        assert "PR #123" in result.output
        # feature-2 should not be in deletable list
        assert "feature-2" not in result.output or "merged" not in result.output


def test_sync_no_deletable_workstacks() -> None:
    """Test sync when there are no deletable workstacks."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync"], obj=test_ctx)

        assert result.exit_code == 0
        assert "✓ No worktrees to clean up" in result.output


def test_sync_with_confirmation() -> None:
    """Test sync with user confirmation."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_name = cwd.name
        workstacks_dir = workstacks_root / repo_name
        workstacks_dir.mkdir(parents=True)

        repo_root = cwd
        (repo_root / ".git").mkdir()

        # Create worktree directory under workstacks_dir
        wt1 = workstacks_dir / "feature-1"
        wt1.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        # User confirms deletion
        result = runner.invoke(cli, ["sync"], obj=test_ctx, input="y\n")

        assert result.exit_code == 0
        assert "Remove 1 worktree(s)?" in result.output
        assert "✓ Removed: feature-1" in result.output


def test_sync_user_cancels() -> None:
    """Test sync when user cancels."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_name = cwd.name
        workstacks_dir = workstacks_root / repo_name
        workstacks_dir.mkdir(parents=True)

        repo_root = cwd
        (repo_root / ".git").mkdir()

        wt1 = workstacks_dir / "feature-1"
        wt1.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        # User cancels deletion
        result = runner.invoke(cli, ["sync"], obj=test_ctx, input="n\n")

        assert result.exit_code == 0
        assert "Cleanup cancelled." in result.output
        # Worktree should still exist
        assert wt1.exists()


def test_sync_force_skips_confirmation() -> None:
    """Test sync -f skips confirmation."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_name = cwd.name
        workstacks_dir = workstacks_root / repo_name
        workstacks_dir.mkdir(parents=True)

        repo_root = cwd
        (repo_root / ".git").mkdir()

        wt1 = workstacks_dir / "feature-1"
        wt1.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "-f"], obj=test_ctx)

        assert result.exit_code == 0
        # Should not prompt for confirmation
        assert "Remove 1 worktree(s)?" not in result.output
        assert "✓ Removed: feature-1" in result.output


def test_sync_dry_run() -> None:
    """Test sync --dry-run shows operations without executing."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_name = cwd.name
        workstacks_dir = workstacks_root / repo_name
        workstacks_dir.mkdir(parents=True)

        repo_root = cwd
        (repo_root / ".git").mkdir()

        wt1 = workstacks_dir / "feature-1"
        wt1.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0
        assert "[DRY RUN] Would run gt sync" in result.output
        assert "[DRY RUN] Would remove worktree: feature-1" in result.output

        # Verify sync was not called
        assert len(graphite_ops.sync_calls) == 0

        # Worktree should still exist
        assert wt1.exists()


def test_sync_return_to_original_worktree() -> None:
    """Test that sync returns to original worktree after running."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        workstacks_root.mkdir()

        repo_root = cwd
        (repo_root / ".git").mkdir()

        # Create worktree directory
        wt1 = workstacks_root / "feature-1"
        wt1.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("OPEN", 123, "Feature 1")})

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync"], obj=test_ctx)

        assert result.exit_code == 0

        # Note: In isolated_filesystem(), we start at cwd which is not
        # under workstacks_root, so no "Returning to:" message should appear


def test_sync_original_worktree_deleted() -> None:
    """Test sync when original worktree is deleted during cleanup."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_name = cwd.name
        workstacks_dir = workstacks_root / repo_name
        workstacks_dir.mkdir(parents=True)

        repo_root = cwd
        (repo_root / ".git").mkdir()

        # Create worktree directory that we'll start in
        wt1 = workstacks_dir / "feature-1"
        wt1.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={wt1: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        os.chdir(wt1)
        try:
            result = runner.invoke(cli, ["sync", "-f"], obj=test_ctx)
        finally:
            os.chdir(cwd)

        assert result.exit_code == 0
        # Should show that worktree was removed and switched to root
        assert "✓ Removed: feature-1" in result.output
        assert str(repo_root) in result.output  # Shows root path after switching


def test_render_return_to_root_script() -> None:
    """Return-to-root script now uses activation script with environment setup."""
    from workstack.cli.activation import render_activation_script

    root = Path("/example/repo/root")
    script = render_activation_script(
        worktree_path=root,
        comment="return to root",
        final_message='echo "✓ Switched to root worktree."',
    )

    # Verify the activation script contains expected elements
    assert "# return to root" in script
    # shlex.quote only adds quotes when needed, /example/repo/root doesn't need them
    assert f"cd {root}" in script
    assert 'echo "✓ Switched to root worktree."' in script
    # Additional elements from activation script
    assert "unset VIRTUAL_ENV" in script  # Clears previous venv
    assert ".venv/bin/activate" in script  # Activates venv if exists


def test_sync_script_mode_when_worktree_exists() -> None:
    """--script outputs nothing when worktree still exists."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_name = cwd.name
        workstacks_dir = workstacks_root / repo_name
        workstacks_dir.mkdir(parents=True)

        repo_root = cwd
        (repo_root / ".git").mkdir()

        wt1 = workstacks_dir / "feature-1"
        wt1.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={wt1: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("OPEN", 123, "Feature 1")})

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        os.chdir(wt1)
        try:
            result = runner.invoke(
                sync_cmd,
                ["--script"],
                obj=test_ctx,
            )
        finally:
            os.chdir(cwd)

        assert result.exit_code == 0
        unexpected_script = render_cd_script(
            repo_root,
            comment="workstack sync - return to root",
            success_message="✓ Switched to root worktree.",
        ).strip()
        assert unexpected_script not in result.output
        assert wt1.exists()


def test_hidden_shell_cmd_sync_passthrough_on_help() -> None:
    """Shell integration command signals passthrough for help."""
    runner = CliRunner()
    result = runner.invoke(hidden_shell_cmd, ["sync", "--help"])

    assert result.exit_code == 0
    assert result.output.strip() == "__WORKSTACK_PASSTHROUGH__"


def test_sync_force_runs_double_gt_sync() -> None:
    """Test that sync -f runs gt sync twice: once at start, once after cleanup."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_name = cwd.name
        workstacks_dir = workstacks_root / repo_name
        workstacks_dir.mkdir(parents=True)

        repo_root = cwd
        (repo_root / ".git").mkdir()

        # Create worktree directory
        wt1 = workstacks_dir / "feature-1"
        wt1.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()
        # feature-1 is merged
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "-f"], obj=test_ctx)

        assert result.exit_code == 0
        # Verify sync was called twice
        assert len(graphite_ops.sync_calls) == 2
        # Both calls should have force=True and quiet=True
        _cwd1, force1, quiet1 = graphite_ops.sync_calls[0]
        _cwd2, force2, quiet2 = graphite_ops.sync_calls[1]
        assert force1 is True
        assert quiet1 is True
        assert force2 is True
        assert quiet2 is True
        # Verify branch cleanup message appeared
        assert "✓ Deleted merged branches" in result.output


def test_sync_without_force_runs_single_gt_sync() -> None:
    """Test that sync without -f only runs gt sync once and shows manual instruction."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_name = cwd.name
        workstacks_dir = workstacks_root / repo_name
        workstacks_dir.mkdir(parents=True)

        repo_root = cwd
        (repo_root / ".git").mkdir()

        # Create worktree directory
        wt1 = workstacks_dir / "feature-1"
        wt1.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()
        # feature-1 is merged
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        # User confirms deletion
        result = runner.invoke(cli, ["sync"], obj=test_ctx, input="y\n")

        assert result.exit_code == 0
        # Verify sync was called only once
        assert len(graphite_ops.sync_calls) == 1
        _cwd, force, quiet = graphite_ops.sync_calls[0]
        assert force is False
        assert quiet is True  # Default is quiet mode
        # Verify manual instruction is still shown
        assert "Next step: Run 'workstack sync -f'" in result.output


def test_sync_force_dry_run_no_sync_calls() -> None:
    """Test that sync -f --dry-run does not call gt sync at all."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"
        repo_name = cwd.name
        workstacks_dir = workstacks_root / repo_name
        workstacks_dir.mkdir(parents=True)

        repo_root = cwd
        (repo_root / ".git").mkdir()

        # Create worktree directory
        wt1 = workstacks_dir / "feature-1"
        wt1.mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()
        # feature-1 is merged
        github_ops = FakeGitHubOps(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=github_ops,
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "-f", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0
        # Verify sync was not called at all
        assert len(graphite_ops.sync_calls) == 0
        # Should show dry-run messages
        assert "[DRY RUN] Would run gt sync -f" in result.output
        assert "[DRY RUN] Would remove worktree: feature-1" in result.output


def test_sync_force_no_deletable_single_sync() -> None:
    """Test that sync -f with no deletable worktrees only runs gt sync once."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
        )

        # use_graphite=True: Feature requires graphite
        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "-f"], obj=test_ctx)

        assert result.exit_code == 0
        # Verify sync was called only once (initial sync, no cleanup needed)
        assert len(graphite_ops.sync_calls) == 1
        _cwd, force, quiet = graphite_ops.sync_calls[0]
        assert force is True
        assert quiet is True  # Default is quiet mode
        # No cleanup message
        assert "✓ Deleted merged branches" not in result.output
        assert "✓ No worktrees to clean up" in result.output


def test_sync_verbose_flag() -> None:
    """Test that sync --verbose passes quiet=False to graphite_ops.sync()."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "--verbose"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Running: gt sync" in result.output

        # Verify quiet=False was passed
        assert len(graphite_ops.sync_calls) == 1
        _cwd_arg, force_arg, quiet_arg = graphite_ops.sync_calls[0]
        assert force_arg is False
        assert quiet_arg is False  # Verbose mode = not quiet


def test_sync_verbose_short_flag() -> None:
    """Test that sync -v (short form) passes quiet=False to graphite_ops.sync()."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "-v"], obj=test_ctx)

        assert result.exit_code == 0

        # Verify quiet=False was passed
        assert len(graphite_ops.sync_calls) == 1
        _cwd_arg, force_arg, quiet_arg = graphite_ops.sync_calls[0]
        assert force_arg is False
        assert quiet_arg is False  # Verbose mode = not quiet


def test_sync_force_verbose_combination() -> None:
    """Test that sync -f -v combines both flags correctly."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        repo_root = cwd
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={cwd: cwd / ".git"},
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
        )

        global_config_ops = GlobalConfig(
            workstacks_root=workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        )

        graphite_ops = FakeGraphiteOps()

        test_ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            global_config=global_config_ops,
            graphite_ops=graphite_ops,
            github_ops=FakeGitHubOps(),
            shell_ops=FakeShellOps(),
            cwd=cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "-f", "-v"], obj=test_ctx)

        assert result.exit_code == 0

        # Verify both flags were passed correctly
        assert len(graphite_ops.sync_calls) == 1
        _cwd_arg, force_arg, quiet_arg = graphite_ops.sync_calls[0]
        assert force_arg is True
        assert quiet_arg is False  # Verbose mode = not quiet
