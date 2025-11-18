"""Tests for the sync command."""

import subprocess
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.shell_integration import hidden_shell_cmd
from erk.cli.commands.sync import sync_cmd
from erk.cli.shell_utils import render_cd_script
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext
from erk.core.git import WorktreeInfo
from tests.fakes.git import FakeGit
from tests.fakes.github import FakeGitHub
from tests.fakes.graphite import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils import sentinel_path
from tests.test_utils.env_helpers import erk_inmem_env


def test_sync_requires_graphite() -> None:
    """Test that sync command requires Graphite to be enabled."""
    runner = CliRunner()
    cwd = sentinel_path()
    erk_root = cwd / "erks"

    # Create minimal git repo structure
    repo_root = cwd

    git_ops = FakeGit(
        git_common_dirs={cwd: cwd / ".git"},
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
            ],
        },
    )

    # use_graphite=False: Test that graphite is required
    global_config_ops = GlobalConfig(
        erk_root=erk_root,
        use_graphite=False,
        shell_setup_complete=False,
        show_pr_info=True,
    )

    graphite_ops = FakeGraphite()

    test_ctx = ErkContext.for_test(
        git=git_ops,
        global_config=global_config_ops,
        graphite=graphite_ops,
        github=FakeGitHub(),
        shell=FakeShell(),
        cwd=cwd,
        dry_run=False,
    )

    result = runner.invoke(cli, ["sync"], obj=test_ctx)

    assert result.exit_code == 1
    assert "requires Graphite" in result.output


def test_sync_runs_gt_sync_from_root() -> None:
    """Test that sync runs gt sync from root worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
        )

        graphite_ops = FakeGraphite()

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync"], obj=test_ctx)

        assert result.exit_code == 0
        # Note: "Running: gt sync" message only appears with --verbose flag

        # Verify sync was called with correct arguments
        assert len(graphite_ops.sync_calls) == 1
        cwd_arg, force_arg, quiet_arg = graphite_ops.sync_calls[0]
        assert cwd_arg == env.cwd
        assert force_arg is False
        assert quiet_arg is True  # Default is quiet mode


def test_sync_with_force_flag() -> None:
    """Test that sync passes --force flag to gt sync."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
        )

        graphite_ops = FakeGraphite()

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
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
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
        )

        # Configure graphite_ops to raise FileNotFoundError
        graphite_ops = FakeGraphite(sync_raises=FileNotFoundError())

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync"], obj=test_ctx)

        assert result.exit_code == 1
        assert "'gt' command not found" in result.output
        assert "brew install" in result.output


def test_sync_handles_gt_sync_failure() -> None:
    """Test that sync handles gt sync failure."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
        )

        # Configure graphite_ops to raise CalledProcessError
        graphite_ops = FakeGraphite(sync_raises=subprocess.CalledProcessError(128, ["gt", "sync"]))

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync"], obj=test_ctx)

        assert result.exit_code == 128
        assert "gt sync failed: exit code 128" in result.output


def test_sync_identifies_deletable_erks() -> None:
    """Test that sync identifies merged/closed erks."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / "repos" / repo_name

        # Define worktree paths (sentinel paths, no mkdir needed)
        wt1 = repo_dir / "worktrees" / "feature-1"
        wt2 = repo_dir / "worktrees" / "feature-2"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                    WorktreeInfo(path=wt2, branch="feature-2"),
                ],
            },
        )

        graphite_ops = FakeGraphite()

        # feature-1 is merged, feature-2 is open
        github_ops = FakeGitHub(
            pr_statuses={
                "feature-1": ("MERGED", 123, "Feature 1"),
                "feature-2": ("OPEN", 124, "Feature 2"),
            }
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
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


def test_sync_no_deletable_erks() -> None:
    """Test sync when there are no deletable erks."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
        )

        graphite_ops = FakeGraphite()

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync"], obj=test_ctx)

        assert result.exit_code == 0
        assert "✓ No worktrees to clean up" in result.output


def test_sync_with_confirmation() -> None:
    """Test sync with user confirmation."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / "repos" / repo_name

        # Define worktree path (sentinel path, no mkdir needed)
        wt1 = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        graphite_ops = FakeGraphite()
        github_ops = FakeGitHub(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
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
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / "repos" / repo_name

        wt1 = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        graphite_ops = FakeGraphite()
        github_ops = FakeGitHub(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        # User cancels deletion
        result = runner.invoke(cli, ["sync"], obj=test_ctx, input="n\n")

        assert result.exit_code == 0
        assert "Cleanup cancelled." in result.output
        # Verify worktree was not removed (check git_ops state)
        assert len(git_ops.removed_worktrees) == 0


def test_sync_force_skips_confirmation() -> None:
    """Test sync -f skips confirmation."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / "repos" / repo_name

        wt1 = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        graphite_ops = FakeGraphite()
        github_ops = FakeGitHub(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
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
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / "repos" / repo_name

        wt1 = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        graphite_ops = FakeGraphite()
        github_ops = FakeGitHub(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0
        assert "[DRY RUN] Would run gt sync" in result.output
        assert "[DRY RUN] Would remove worktree: feature-1" in result.output

        # Verify sync was not called
        assert len(graphite_ops.sync_calls) == 0

        # Verify worktree was not removed (check git_ops state)
        assert len(git_ops.removed_worktrees) == 0


def test_sync_return_to_original_worktree() -> None:
    """Test that sync returns to original worktree after running."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Define worktree path
        wt1 = env.erk_root / "feature-1"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        graphite_ops = FakeGraphite()
        github_ops = FakeGitHub(pr_statuses={"feature-1": ("OPEN", 123, "Feature 1")})

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync"], obj=test_ctx)

        assert result.exit_code == 0

        # Note: In isolated_filesystem(), we start at cwd which is not
        # under erk_root, so no "Returning to:" message should appear


def test_sync_original_worktree_deleted() -> None:
    """Test sync when original worktree is deleted during cleanup."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / "repos" / repo_name

        # Define worktree path
        wt1 = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            git_common_dirs={wt1: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        graphite_ops = FakeGraphite()
        github_ops = FakeGitHub(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=wt1,  # Test from the worktree that will be deleted
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "-f"], obj=test_ctx)

        assert result.exit_code == 0
        # Should show that worktree was removed
        assert "✓ Removed: feature-1" in result.output


def test_render_return_to_root_script() -> None:
    """Return-to-root script now uses activation script with environment setup."""
    from erk.cli.activation import render_activation_script

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
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / "repos" / repo_name

        wt1 = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            git_common_dirs={wt1: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        graphite_ops = FakeGraphite()
        github_ops = FakeGitHub(pr_statuses={"feature-1": ("OPEN", 123, "Feature 1")})

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            cwd=wt1,  # Start from the worktree
            dry_run=False,
        )

        result = runner.invoke(
            sync_cmd,
            ["--script"],
            obj=test_ctx,
        )

        assert result.exit_code == 0
        unexpected_script = render_cd_script(
            env.cwd,
            comment="erk sync - return to root",
            success_message="✓ Switched to root worktree.",
        ).strip()
        assert unexpected_script not in result.output
        # Verify worktree was not removed
        assert len(git_ops.removed_worktrees) == 0


def test_hidden_shell_cmd_sync_passthrough_on_help() -> None:
    """Shell integration command signals passthrough for help."""
    runner = CliRunner()
    result = runner.invoke(hidden_shell_cmd, ["sync", "--help"])

    assert result.exit_code == 0
    assert result.output.strip() == "__ERK_PASSTHROUGH__"


def test_sync_force_runs_double_gt_sync() -> None:
    """Test that sync -f runs gt sync twice: once at start, once after cleanup."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / "repos" / repo_name

        # Define worktree path
        wt1 = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        graphite_ops = FakeGraphite()
        # feature-1 is merged
        github_ops = FakeGitHub(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
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
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / "repos" / repo_name

        # Define worktree path
        wt1 = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        graphite_ops = FakeGraphite()
        # feature-1 is merged
        github_ops = FakeGitHub(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
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
        assert "Next step: Run 'gt sync -f'" in result.output


def test_sync_force_dry_run_no_sync_calls() -> None:
    """Test that sync -f --dry-run does not call gt sync at all."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_name = env.cwd.name
        repo_dir = env.erk_root / "repos" / repo_name

        # Define worktree path
        wt1 = repo_dir / "worktrees" / "feature-1"

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=wt1, branch="feature-1"),
                ],
            },
        )

        graphite_ops = FakeGraphite()
        # feature-1 is merged
        github_ops = FakeGitHub(pr_statuses={"feature-1": ("MERGED", 123, "Feature 1")})

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=github_ops,
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
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
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
        )

        graphite_ops = FakeGraphite()

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
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
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
        )

        graphite_ops = FakeGraphite()

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
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
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
        )

        graphite_ops = FakeGraphite()

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
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
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                ],
            },
        )

        graphite_ops = FakeGraphite()

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            graphite=graphite_ops,
            github=FakeGitHub(),
            shell=FakeShell(),
            script_writer=env.script_writer,
            cwd=env.cwd,
            dry_run=False,
        )

        result = runner.invoke(cli, ["sync", "-f", "-v"], obj=test_ctx)

        assert result.exit_code == 0

        # Verify both flags were passed correctly
        assert len(graphite_ops.sync_calls) == 1
        _cwd_arg, force_arg, quiet_arg = graphite_ops.sync_calls[0]
        assert force_arg is True
        assert quiet_arg is False  # Verbose mode = not quiet
