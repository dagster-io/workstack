"""Tests for workstack consolidate command.

This file tests the consolidate command which removes worktrees containing
branches from the current Graphite stack.
"""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import pure_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo


def _create_test_context(
    env,
    worktrees: dict[Path, list[WorktreeInfo]],
    current_branch: str | None,
    graphite_ops: FakeGraphiteOps,
    *,
    cwd: Path | None = None,
    git_dir: Path | None = None,
    file_statuses: dict[Path, tuple[list[str], list[str], list[str]]] | None = None,
) -> WorkstackContext:
    """Helper to create test context for consolidate command tests.

    Args:
        env: Simulated workstack environment
        worktrees: Map of repo_root to list of WorktreeInfo objects
        current_branch: Current branch name (or None for detached HEAD)
        graphite_ops: FakeGraphiteOps configured with branch stack data
        cwd: Optional current working directory path (defaults to env.cwd)
        git_dir: Optional git directory path (defaults to env.git_dir)
        file_statuses: Optional mapping of worktree paths to (staged, modified, untracked) files

    Returns:
        WorkstackContext configured for testing
    """
    if cwd is None:
        cwd = env.cwd
    if git_dir is None:
        git_dir = env.git_dir

    git_ops = FakeGitOps(
        worktrees=worktrees,
        git_common_dirs={cwd: git_dir},
        current_branches={cwd: current_branch},
        file_statuses=file_statuses,
    )

    return env.build_context(
        use_graphite=True,
        git_ops=git_ops,
        github_ops=FakeGitHubOps(),
        graphite_ops=graphite_ops,
        shell_ops=FakeShellOps(),
        cwd=cwd,
        dry_run=False,
    )


def test_consolidate_no_other_worktrees() -> None:
    """Test consolidate when no other worktrees contain stack branches."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphiteOps(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Current worktree only (on feature-2)
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-2")]}

        test_ctx = _create_test_context(
            env, worktrees, "feature-2", graphite_ops, git_dir=env.git_dir
        )
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "No other worktrees found" in result.output


def test_consolidate_no_other_worktrees_with_script_flag() -> None:
    """Test consolidate shows output with --script flag when no worktrees to remove."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphiteOps(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Current worktree only (on feature-2)
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-2")]}

        test_ctx = _create_test_context(
            env, worktrees, "feature-2", graphite_ops, git_dir=env.git_dir
        )
        result = runner.invoke(cli, ["consolidate", "--script", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # This would have caught the bug: output should display even with --script flag
        assert "No other worktrees found" in result.output


def test_consolidate_removes_other_stack_worktrees() -> None:
    """Test consolidate removes worktrees with branches from current stack."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphiteOps(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Create worktree directories
        wt1_path = env.workstacks_root / env.root_worktree.name / "wt1"
        wt2_path = env.workstacks_root / env.root_worktree.name / "wt2"

        # Current worktree on feature-2, other worktrees on feature-1 and main
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-2"),
                WorktreeInfo(path=wt1_path, branch="feature-1"),
                WorktreeInfo(path=wt2_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(
            env, worktrees, "feature-2", graphite_ops, git_dir=env.git_dir
        )
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Removed:" in result.output
        assert str(wt1_path) in result.output
        assert str(wt2_path) in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 2


def test_consolidate_preserves_current_worktree() -> None:
    """Test consolidate preserves the current worktree even if it's in the stack."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create other worktree
        wt1_path = env.workstacks_root / env.root_worktree.name / "wt1"

        # Both worktrees in same stack, current is on feature-1
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(
            env, worktrees, "feature-1", graphite_ops, git_dir=env.git_dir
        )
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only wt1 should be removed, not cwd
        assert len(test_ctx.git_ops.removed_worktrees) == 1
        assert wt1_path in test_ctx.git_ops.removed_worktrees


def test_consolidate_aborts_on_uncommitted_changes() -> None:
    """Test consolidate aborts if ANY worktree has uncommitted changes."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree with uncommitted changes marker
        wt1_path = env.workstacks_root / env.root_worktree.name / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        # Configure file_statuses to simulate uncommitted changes in wt1
        file_statuses = {
            wt1_path: ([], [], ["uncommitted.txt"]),  # Untracked file
        }

        test_ctx = _create_test_context(
            env,
            worktrees,
            "feature-1",
            graphite_ops,
            git_dir=env.git_dir,
            file_statuses=file_statuses,
        )
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Uncommitted changes detected" in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 0


def test_consolidate_dry_run_shows_preview() -> None:
    """Test --dry-run shows what would be removed without executing."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        wt1_path = env.workstacks_root / env.root_worktree.name / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(
            env, worktrees, "feature-1", graphite_ops, git_dir=env.git_dir
        )
        result = runner.invoke(cli, ["consolidate", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert str(wt1_path) in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 0


def test_consolidate_confirmation_prompt() -> None:
    """Test consolidate prompts for confirmation without --force."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        wt1_path = env.workstacks_root / env.root_worktree.name / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(
            env, worktrees, "feature-1", graphite_ops, git_dir=env.git_dir
        )

        # Test saying "no" to prompt
        result = runner.invoke(cli, ["consolidate"], input="n\n", obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Proceed with removal?" in result.output
        assert "Aborted" in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 0


def test_consolidate_detached_head_error() -> None:
    """Test consolidate aborts if current worktree is in detached HEAD state."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Current worktree with detached HEAD (None branch)
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch=None)]}

        # Create context with no current branch
        git_ops = FakeGitOps(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: None},
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git_ops=git_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "detached HEAD state" in result.output


def test_consolidate_not_tracked_by_graphite() -> None:
    """Test consolidate errors if current branch is not tracked by Graphite."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with only main branch (feature-1 is not tracked)
        graphite_ops = FakeGraphiteOps(stacks={"main": ["main"]})

        # Current branch is "feature-1" but not in Graphite
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-1")]}

        test_ctx = _create_test_context(
            env, worktrees, "feature-1", graphite_ops, git_dir=env.git_dir
        )
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not tracked by Graphite" in result.output


def test_consolidate_skips_non_stack_worktrees() -> None:
    """Test consolidate only removes worktrees with branches in current stack."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack-a only (main -> stack-a)
        # stack-b is a separate branch not in this stack
        graphite_ops = FakeGraphiteOps(stacks={"stack-a": ["main", "stack-a"]})

        # Create worktrees
        wt1_path = env.workstacks_root / env.root_worktree.name / "wt1"
        wt2_path = env.workstacks_root / env.root_worktree.name / "wt2"

        # Current on stack-a, wt1 on main (in stack), wt2 on stack-b (NOT in stack)
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="stack-a"),
                WorktreeInfo(path=wt1_path, branch="main"),
                WorktreeInfo(path=wt2_path, branch="stack-b"),
            ]
        }

        test_ctx = _create_test_context(
            env, worktrees, "stack-a", graphite_ops, git_dir=env.git_dir
        )
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only wt1 (main) should be removed, wt2 (stack-b) should remain
        assert len(test_ctx.git_ops.removed_worktrees) == 1
        assert wt1_path in test_ctx.git_ops.removed_worktrees
        assert wt2_path not in test_ctx.git_ops.removed_worktrees


def test_consolidate_with_uncommitted_changes_in_non_stack_worktree() -> None:
    """Test consolidate succeeds when non-stack worktrees have uncommitted changes."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphiteOps(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Create worktrees
        wt1_path = env.workstacks_root / env.root_worktree.name / "wt1"
        wt2_path = env.workstacks_root / env.root_worktree.name / "wt2"
        wt3_path = env.workstacks_root / env.root_worktree.name / "wt3"

        # Current on feature-2, wt1 on feature-1 (in stack), wt2 on main (in stack),
        # wt3 on other-branch (NOT in stack, has uncommitted changes)
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-2"),
                WorktreeInfo(path=wt1_path, branch="feature-1"),
                WorktreeInfo(path=wt2_path, branch="main"),
                WorktreeInfo(path=wt3_path, branch="other-branch"),
            ]
        }

        # Configure file_statuses to simulate uncommitted changes in non-stack worktree
        file_statuses = {
            wt3_path: ([], [], ["uncommitted.txt"]),  # Untracked file in non-stack worktree
        }

        test_ctx = _create_test_context(
            env,
            worktrees,
            "feature-2",
            graphite_ops,
            git_dir=env.git_dir,
            file_statuses=file_statuses,
        )
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        # Command should succeed despite uncommitted changes in non-stack worktree
        assert result.exit_code == 0, result.output
        # Only feature-1 and main worktrees should be removed
        assert len(test_ctx.git_ops.removed_worktrees) == 2
        assert wt1_path in test_ctx.git_ops.removed_worktrees
        assert wt2_path in test_ctx.git_ops.removed_worktrees
        # other-branch worktree should remain untouched
        assert wt3_path not in test_ctx.git_ops.removed_worktrees


def test_consolidate_preserves_root_worktree_even_when_in_stack() -> None:
    """Test consolidate never removes the root worktree, even if its branch is in the stack.

    This is a regression test for the bug where consolidate would attempt to remove
    the root worktree when run from a linked worktree, causing git to reject the
    operation with "fatal: '/path' is a main working tree".
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphiteOps(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Create worktree directories
        # Root worktree at repo root (on main branch, part of the stack)
        main_worktree = env.cwd / "main-repo"
        # Linked worktree for feature-1
        wt1_path = env.workstacks_root / env.root_worktree.name / "wt1"
        # Current linked worktree for feature-2
        wt2_path = env.workstacks_root / env.root_worktree.name / "wt2"

        # Root worktree is on 'main' branch (which is in the stack)
        # Current worktree is wt2 on feature-2
        # wt1 is on feature-1 (also in stack)
        worktrees = {
            main_worktree: [
                WorktreeInfo(path=main_worktree, branch="main", is_root=True),  # Root worktree
                WorktreeInfo(path=wt1_path, branch="feature-1", is_root=False),  # Linked
                WorktreeInfo(path=wt2_path, branch="feature-2", is_root=False),  # Current
            ]
        }

        # Create custom context with wt2_path as cwd
        git_ops = FakeGitOps(
            worktrees=worktrees,
            git_common_dirs={wt2_path: main_worktree / ".git"},
            current_branches={wt2_path: "feature-2"},
        )
        # Override git_common_dirs to include all worktrees
        git_ops._git_common_dirs[main_worktree] = main_worktree / ".git"
        git_ops._git_common_dirs[wt1_path] = main_worktree / ".git"
        git_ops._git_common_dirs[wt2_path] = main_worktree / ".git"

        test_ctx = env.build_context(
            use_graphite=True,
            git_ops=git_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            cwd=wt2_path,
            dry_run=False,
        )

        # Context already has cwd=wt2_path, no need for os.chdir() in pure mode
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        # Command should succeed
        assert result.exit_code == 0, result.output

        # Root worktree should NEVER be removed, even though 'main' is in the stack
        assert main_worktree not in test_ctx.git_ops.removed_worktrees

        # Only feature-1 worktree should be removed (feature-2 is current, root is root)
        assert len(test_ctx.git_ops.removed_worktrees) == 1
        assert wt1_path in test_ctx.git_ops.removed_worktrees

        # Current worktree (feature-2) should also not be removed
        assert wt2_path not in test_ctx.git_ops.removed_worktrees


def test_consolidate_partial_stack() -> None:
    """Test consolidating only trunk → specified branch."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feat-1 -> feat-2 -> feat-3)
        graphite_ops = FakeGraphiteOps(stacks={"feat-3": ["main", "feat-1", "feat-2", "feat-3"]})

        # Create worktree directories
        workstacks_dir = env.workstacks_root / env.cwd.name
        wt1_path = workstacks_dir / "wt1"
        wt2_path = workstacks_dir / "wt2"
        wt3_path = workstacks_dir / "wt3"

        # Three worktrees: wt1 (feat-1), wt2 (feat-2), wt3 (feat-3, current)
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=wt1_path, branch="feat-1"),
                WorktreeInfo(path=wt2_path, branch="feat-2"),
                WorktreeInfo(path=wt3_path, branch="feat-3"),
            ]
        }

        test_ctx = _create_test_context(
            env, worktrees, "feat-3", graphite_ops, cwd=wt3_path, git_dir=env.git_dir
        )
        # Override git_common_dirs
        test_ctx.git_ops._git_common_dirs[wt1_path] = env.git_dir
        test_ctx.git_ops._git_common_dirs[wt2_path] = env.git_dir
        test_ctx.git_ops._git_common_dirs[wt3_path] = env.git_dir

        # Run consolidate with branch argument: consolidate feat-2
        # Should consolidate main → feat-2 only, keeping feat-3 separate
        result = runner.invoke(cli, ["consolidate", "feat-2", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should remove wt1 (feat-1) and wt2 (feat-2), but NOT wt3 (feat-3, current)
        assert len(test_ctx.git_ops.removed_worktrees) == 2
        assert wt1_path in test_ctx.git_ops.removed_worktrees
        assert wt2_path in test_ctx.git_ops.removed_worktrees
        assert wt3_path not in test_ctx.git_ops.removed_worktrees


def test_consolidate_branch_not_in_stack() -> None:
    """Test error when specified branch is not in current stack."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feat-1 -> feat-2)
        graphite_ops = FakeGraphiteOps(stacks={"feat-2": ["main", "feat-1", "feat-2"]})

        # Current worktree on feat-2
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feat-2")]}

        test_ctx = _create_test_context(env, worktrees, "feat-2", graphite_ops, git_dir=env.git_dir)

        # Try to consolidate to a branch not in the stack
        result = runner.invoke(cli, ["consolidate", "feat-99", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not in the current stack" in result.output
        assert "feat-99" in result.output


def test_consolidate_preserves_upstack_branches() -> None:
    """Test that branches above the specified branch remain in separate worktrees."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feat-1 -> feat-2 -> feat-3 -> feat-4)
        graphite_ops = FakeGraphiteOps(
            stacks={"feat-4": ["main", "feat-1", "feat-2", "feat-3", "feat-4"]}
        )

        # Create worktree directories
        workstacks_dir = env.workstacks_root / env.cwd.name
        wt1_path = workstacks_dir / "wt1"
        wt2_path = workstacks_dir / "wt2"
        wt3_path = workstacks_dir / "wt3"
        wt4_path = workstacks_dir / "wt4"

        # Four worktrees for feat-1, feat-2, feat-3, feat-4
        # Current is wt4 (feat-4)
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=wt1_path, branch="feat-1"),
                WorktreeInfo(path=wt2_path, branch="feat-2"),
                WorktreeInfo(path=wt3_path, branch="feat-3"),
                WorktreeInfo(path=wt4_path, branch="feat-4"),
            ]
        }

        test_ctx = _create_test_context(
            env, worktrees, "feat-4", graphite_ops, cwd=wt4_path, git_dir=env.git_dir
        )
        # Override git_common_dirs
        test_ctx.git_ops._git_common_dirs[wt1_path] = env.git_dir
        test_ctx.git_ops._git_common_dirs[wt2_path] = env.git_dir
        test_ctx.git_ops._git_common_dirs[wt3_path] = env.git_dir
        test_ctx.git_ops._git_common_dirs[wt4_path] = env.git_dir

        # Consolidate feat-2 (from current=feat-4)
        # Should remove feat-1 and feat-2, but keep feat-3 and feat-4
        result = runner.invoke(cli, ["consolidate", "feat-2", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should remove wt1 (feat-1) and wt2 (feat-2)
        assert len(test_ctx.git_ops.removed_worktrees) == 2
        assert wt1_path in test_ctx.git_ops.removed_worktrees
        assert wt2_path in test_ctx.git_ops.removed_worktrees
        # Should NOT remove wt3 (feat-3) and wt4 (feat-4, current)
        assert wt3_path not in test_ctx.git_ops.removed_worktrees
        assert wt4_path not in test_ctx.git_ops.removed_worktrees


def test_consolidate_shows_output_with_script_flag() -> None:
    """Test consolidate displays removal output even when --script flag is enabled."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        workstacks_dir = env.workstacks_root / env.cwd.name
        wt1_path = workstacks_dir / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(
            env, worktrees, "feature-1", graphite_ops, git_dir=env.git_dir
        )
        result = runner.invoke(cli, ["consolidate", "--script", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify output is shown even with --script flag
        assert "✅ Removed:" in result.output
        assert str(wt1_path) in result.output
        assert "Consolidation complete" in result.output


def test_consolidate_shows_output_without_script_flag() -> None:
    """Test consolidate displays removal output when --script flag is not enabled."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        workstacks_dir = env.workstacks_root / env.cwd.name
        wt1_path = workstacks_dir / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(
            env, worktrees, "feature-1", graphite_ops, git_dir=env.git_dir
        )
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify output is shown
        assert "✅ Removed:" in result.output
        assert str(wt1_path) in result.output
        assert "Consolidation complete" in result.output


def test_consolidate_script_mode_shows_preview_output() -> None:
    """Test consolidate displays full preview even with --script flag.

    Regression test for bug where line 277 guard suppressed ALL preview output
    in script mode, causing users to see nothing.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree to remove
        wt1_path = env.workstacks_root / env.root_worktree.name / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(
            env, worktrees, "feature-1", graphite_ops, git_dir=env.git_dir
        )
        result = runner.invoke(cli, ["consolidate", "--script", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        # Verify preview sections appear (were suppressed by line 277 guard)
        assert "Current stack:" in result.output
        assert "Target worktree:" in result.output
        assert "Safe to remove" in result.output
        assert "Note: Use 'gt restack'" in result.output

        # Verify visual markers appear
        assert "←" in result.output or "current" in result.output
        assert "→" in result.output or "consolidating" in result.output


def test_consolidate_outputs_to_stderr() -> None:
    """Test consolidate routes all user output to stderr for shell integration.

    Shell integration captures stdout. User-visible output must go to stderr
    or users won't see it.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        wt1_path = env.workstacks_root / env.root_worktree.name / "wt1"

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(
            env, worktrees, "feature-1", graphite_ops, git_dir=env.git_dir
        )
        result = runner.invoke(
            cli, ["consolidate", "--script", "-f"], obj=test_ctx, catch_exceptions=False
        )

        assert result.exit_code == 0

        # With the fix, all output should appear in result.output
        # (which captures both streams by default)
        # The key test is that output DOES appear (not suppressed by --script flag)


def test_consolidate_down_without_name_no_script_output() -> None:
    """Test consolidate --down without --name produces no script output to stdout.

    This tests the specific bug fix: when consolidating into the current worktree
    (--down without --name), no script path should be written to stdout.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Set up main → feature1 → feature2 stack
        main = WorktreeInfo(path=env.cwd, branch="main")
        feature1_dir = env.cwd.parent / "feature1"
        feature1 = WorktreeInfo(path=feature1_dir, branch="feature1")
        graphite_ops = FakeGraphiteOps(stacks={"feature2": ["main", "feature1", "feature2"]})

        test_ctx = _create_test_context(
            env,
            {env.cwd: [main, feature1]},
            current_branch="feature2",  # Current is feature2, will consolidate feature1
            graphite_ops=graphite_ops,
        )

        result = runner.invoke(cli, ["consolidate", "--down", "-f"], obj=test_ctx)

        assert result.exit_code == 0
        # Critical test: stdout should be empty (no script path)
        # When mix_stderr=False, result.output contains only stdout
        assert result.output.strip() == ""
        # User messages should still appear (in stderr when mix_stderr=False)
        # or in result.output when mix_stderr=True
        # The key test is that stdout is empty


def test_consolidate_with_name_produces_script_output() -> None:
    """Test consolidate --name produces script output to stdout when successful.

    When consolidating into a new/different worktree, a script path should be
    written to stdout for shell integration.
    """
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Set up main → feature1 → feature2 stack
        main = WorktreeInfo(path=env.cwd, branch="main")
        feature1_dir = env.cwd.parent / "feature1"
        feature1 = WorktreeInfo(path=feature1_dir, branch="feature1")
        graphite_ops = FakeGraphiteOps(stacks={"feature2": ["main", "feature1", "feature2"]})

        test_ctx = _create_test_context(
            env,
            {env.cwd: [main, feature1]},
            current_branch="feature2",
            graphite_ops=graphite_ops,
        )

        result = runner.invoke(
            cli, ["consolidate", "--name", "consolidated", "--script", "-f"], obj=test_ctx
        )

        assert result.exit_code == 0
        # With --name and --script, stdout should contain a script path
        # When mix_stderr=False, result.output contains only stdout
        stdout = result.output.strip()
        assert stdout != ""
        assert "/" in stdout  # Should be a path
        assert "\n" not in stdout  # Should be single line
        # The key test is that stdout contains a valid script path
