"""Tests for the workstack move command."""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.context import create_test_context
from tests.fakes.gitops import FakeGitOps
from workstack.cli.cli import cli
from workstack.core.gitops import WorktreeInfo


def test_move_from_current_to_new_worktree() -> None:
    """Test moving branch from current worktree to a new worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        source_wt = repo_root
        target_wt = workstacks_dir / "target-wt"

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=source_wt, branch="feature-x"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(cli, ["move", "target-wt"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Moving 'feature-x'" in result.output
        assert "✓ Moved 'feature-x'" in result.output

        worktrees = git_ops.list_worktrees(repo_root)
        assert len(worktrees) == 2
        assert any(
            wt.path.resolve() == target_wt.resolve() and wt.branch == "feature-x"
            for wt in worktrees
        )


def test_move_with_explicit_current_flag() -> None:
    """Test move with explicit --current flag."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="feature-y"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(cli, ["move", "--current", "new-wt"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Moving 'feature-y'" in result.output


def test_move_with_branch_flag_auto_detect() -> None:
    """Test move with --branch flag to auto-detect source worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        source_wt = workstacks_dir / "old-wt"
        source_wt.mkdir(parents=True)

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=source_wt, branch="feature-auth"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(cli, ["move", "--branch", "feature-auth", "new-wt"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Moving 'feature-auth'" in result.output


def test_move_with_worktree_flag() -> None:
    """Test move with explicit --worktree flag."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        source_wt = workstacks_dir / "source-wt"
        source_wt.mkdir(parents=True)

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=source_wt, branch="feature-db"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(cli, ["move", "--worktree", "source-wt", "target-wt"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Moving 'feature-db'" in result.output


def test_move_swap_between_two_worktrees() -> None:
    """Test swapping branches between two existing worktrees."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        source_wt = workstacks_dir / "wt1"
        source_wt.mkdir(parents=True)
        target_wt = workstacks_dir / "wt2"
        target_wt.mkdir(parents=True)

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=source_wt, branch="branch-a"),
                    WorktreeInfo(path=target_wt, branch="branch-b"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                source_wt: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(cli, ["move", "--worktree", "wt1", "wt2", "--force"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Swapping branches between 'wt1' and 'wt2'" in result.output
        assert "✓ Swapped 'branch-a' ↔ 'branch-b'" in result.output


def test_move_swap_requires_confirmation() -> None:
    """Test that swap operation requires confirmation without --force."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        source_wt = workstacks_dir / "wt1"
        source_wt.mkdir(parents=True)
        target_wt = workstacks_dir / "wt2"
        target_wt.mkdir(parents=True)

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=source_wt, branch="branch-a"),
                    WorktreeInfo(path=target_wt, branch="branch-b"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                source_wt: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(cli, ["move", "--worktree", "wt1", "wt2"], input="n\n", obj=test_ctx)

        assert result.exit_code == 0
        assert "This will swap branches between worktrees:" in result.output
        assert "Swap cancelled" in result.output


def test_move_with_custom_ref() -> None:
    """Test move with custom --ref fallback branch."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="feature-x"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "develop"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(cli, ["move", "new-wt", "--ref", "develop"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Moving 'feature-x'" in result.output


def test_move_error_multiple_source_flags() -> None:
    """Test error when multiple source flags are specified."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={
                cwd: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(
            cli,
            ["move", "--current", "--branch", "feature", "target"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Only one of --current, --branch, or --worktree can be specified" in result.output


def test_move_error_branch_not_found() -> None:
    """Test error when specified branch is not found in any worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(
            cli,
            ["move", "--branch", "nonexistent", "target"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Branch 'nonexistent' not found in any worktree" in result.output


def test_move_error_worktree_not_found() -> None:
    """Test error when specified worktree does not exist."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            git_common_dirs={
                cwd: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(
            cli,
            ["move", "--worktree", "nonexistent", "target"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Worktree 'nonexistent' does not exist" in result.output


def test_move_error_source_and_target_same() -> None:
    """Test error when source and target are the same worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        wt = workstacks_dir / "same-wt"
        wt.mkdir(parents=True)

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=wt, branch="feature"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                wt: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(
            cli,
            ["move", "--worktree", "same-wt", "same-wt"],
            obj=test_ctx,
        )

        assert result.exit_code == 1
        assert "Source and target worktrees are the same" in result.output


def test_move_error_source_in_detached_head() -> None:
    """Test error when source worktree is in detached HEAD state."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch=None),  # Detached HEAD
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(cli, ["move", "target"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Source worktree is in detached HEAD state" in result.output


def test_move_to_existing_worktree_in_detached_head() -> None:
    """Test moving to an existing worktree in detached HEAD (should checkout branch there)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        source_wt = workstacks_dir / "source"
        source_wt.mkdir(parents=True)
        target_wt = workstacks_dir / "target"
        target_wt.mkdir(parents=True)

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=source_wt, branch="feature-x"),
                    WorktreeInfo(path=target_wt, branch=None),  # Detached HEAD
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                source_wt: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        result = runner.invoke(cli, ["move", "--worktree", "source", "target"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Moving 'feature-x'" in result.output
        assert "✓ Moved 'feature-x'" in result.output


def test_move_to_root() -> None:
    """Test moving branch from current worktree to root."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        source_wt = workstacks_dir / "feature-wt"
        source_wt.mkdir(parents=True)

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=source_wt, branch="feature-x"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                source_wt: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        # Move from feature-wt to root (should swap branches)
        result = runner.invoke(
            cli, ["move", "--worktree", "feature-wt", "root", "--force"], obj=test_ctx
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Swapping branches" in result.output
        assert "✓ Swapped 'feature-x' ↔ 'main'" in result.output


def test_move_to_root_with_explicit_current() -> None:
    """Test moving from current worktree to root with --current flag."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        repo_root = Path.cwd()
        workstacks_root = repo_root / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        source_wt = workstacks_dir / "feature-wt"
        source_wt.mkdir(parents=True)

        # Simulate current directory being source_wt
        import os

        os.chdir(source_wt)
        # Get the resolved current directory after chdir
        current_dir = Path.cwd().resolve()

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=current_dir, branch="feature-y"),  # Use resolved current_dir
                ],
            },
            git_common_dirs={
                current_dir: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        # Execute from within source_wt (now we're already there due to os.chdir)
        result = runner.invoke(cli, ["move", "root", "--force"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Swapping branches" in result.output or "Moved" in result.output


def test_move_to_root_when_root_is_detached_head() -> None:
    """Test moving to root when root is in detached HEAD state (move operation)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        source_wt = workstacks_dir / "feature-wt"
        source_wt.mkdir(parents=True)

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch=None),  # Detached HEAD at root
                    WorktreeInfo(path=source_wt, branch="feature-x"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                source_wt: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        # Move from feature-wt to root (should be a move, not swap, since root is detached)
        result = runner.invoke(cli, ["move", "--worktree", "feature-wt", "root"], obj=test_ctx)

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Moving 'feature-x'" in result.output
        assert "✓ Moved 'feature-x'" in result.output


def test_move_error_source_is_root_target_is_root() -> None:
    """Test error when trying to move root to root."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        repo_root = cwd
        workstacks_root = cwd / "workstacks"
        workstacks_dir = workstacks_root / repo_root.name
        workstacks_dir.mkdir(parents=True)
        (repo_root / ".git").mkdir()

        git_ops = FakeGitOps(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                ],
            },
            git_common_dirs={
                cwd: repo_root / ".git",
                repo_root: repo_root / ".git",
            },
            default_branches={repo_root: "main"},
        )

        global_config_ops = FakeGlobalConfigOps(
            workstacks_root=workstacks_root,
            use_graphite=False,
        )

        test_ctx = create_test_context(git_ops=git_ops, global_config_ops=global_config_ops)

        # Try to move root to root (should fail)
        result = runner.invoke(cli, ["move", "root"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Source and target worktrees are the same" in result.output
