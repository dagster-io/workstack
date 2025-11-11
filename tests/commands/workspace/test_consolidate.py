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
from tests.test_utils.env_helpers import simulated_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo
from workstack.core.global_config import GlobalConfig


def _create_test_context(
    env,
    worktrees: dict[Path, list[WorktreeInfo]],
    current_branch: str,
    graphite_ops: FakeGraphiteOps,
    *,
    file_statuses: dict[Path, tuple[list[str], list[str], list[str]]] | None = None,
) -> WorkstackContext:
    """Helper to create test context for consolidate command tests.

    Args:
        env: SimulatedWorkstackEnv from simulated_workstack_env
        worktrees: Map of repo_root to list of WorktreeInfo objects
        current_branch: Current branch name
        graphite_ops: FakeGraphiteOps configured with branch stack data
        file_statuses: Optional mapping of worktree paths to (staged, modified, untracked) files

    Returns:
        WorkstackContext configured for testing
    """
    git_ops = FakeGitOps(
        worktrees=worktrees,
        git_common_dirs={env.cwd: env.git_dir},
        current_branches={env.cwd: current_branch},
        file_statuses=file_statuses,
    )

    return WorkstackContext(
        git_ops=git_ops,
        global_config_ops=GlobalConfig(
            workstacks_root=env.workstacks_root,
            use_graphite=True,
            shell_setup_complete=False,
            show_pr_info=True,
            show_pr_checks=False,
        ),
        github_ops=FakeGitHubOps(),
        graphite_ops=graphite_ops,
        shell_ops=FakeShellOps(),
        cwd=env.cwd,
        dry_run=False,
        trunk_branch=None,
    )


def test_consolidate_no_other_worktrees() -> None:
    """Test consolidate when no other worktrees contain stack branches."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphiteOps(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Current worktree only (on feature-2)
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-2")]}

        test_ctx = _create_test_context(env, worktrees, "feature-2", graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "No other worktrees found" in result.output


def test_consolidate_removes_other_stack_worktrees() -> None:
    """Test consolidate removes worktrees with branches from current stack."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphiteOps(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Create worktree directories
        wt1_path = env.workstacks_dir / "wt1"
        wt2_path = env.workstacks_dir / "wt2"
        wt1_path.mkdir(parents=True)
        wt2_path.mkdir(parents=True)

        # Current worktree on feature-2, other worktrees on feature-1 and main
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-2"),
                WorktreeInfo(path=wt1_path, branch="feature-1"),
                WorktreeInfo(path=wt2_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(env, worktrees, "feature-2", graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Removed:" in result.output
        assert str(wt1_path) in result.output
        assert str(wt2_path) in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 2


def test_consolidate_preserves_current_worktree() -> None:
    """Test consolidate preserves the current worktree even if it's in the stack."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create other worktree
        wt1_path = env.workstacks_dir / "wt1"
        wt1_path.mkdir(parents=True)

        # Both worktrees in same stack, current is on feature-1
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(env, worktrees, "feature-1", graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only wt1 should be removed, not cwd
        assert len(test_ctx.git_ops.removed_worktrees) == 1
        assert wt1_path in test_ctx.git_ops.removed_worktrees


def test_consolidate_aborts_on_uncommitted_changes() -> None:
    """Test consolidate aborts if ANY worktree has uncommitted changes."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree with uncommitted changes marker
        wt1_path = env.workstacks_dir / "wt1"
        wt1_path.mkdir(parents=True)
        # Create a file to simulate uncommitted changes
        (wt1_path / "uncommitted.txt").write_text("changes", encoding="utf-8")

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
            env, worktrees, "feature-1", graphite_ops, file_statuses=file_statuses
        )
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Uncommitted changes detected" in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 0


def test_consolidate_dry_run_shows_preview() -> None:
    """Test --dry-run shows what would be removed without executing."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        wt1_path = env.workstacks_dir / "wt1"
        wt1_path.mkdir(parents=True)

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(env, worktrees, "feature-1", graphite_ops)
        result = runner.invoke(cli, ["consolidate", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert str(wt1_path) in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 0
        assert wt1_path.exists()


def test_consolidate_confirmation_prompt() -> None:
    """Test consolidate prompts for confirmation without --force."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        wt1_path = env.workstacks_dir / "wt1"
        wt1_path.mkdir(parents=True)

        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(env, worktrees, "feature-1", graphite_ops)

        # Test saying "no" to prompt
        result = runner.invoke(cli, ["consolidate"], input="n\n", obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Proceed with removal?" in result.output
        assert "Aborted" in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 0


def test_consolidate_detached_head_error() -> None:
    """Test consolidate aborts if current worktree is in detached HEAD state."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Current worktree with detached HEAD (None branch)
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch=None)]}

        # Create context with no current branch
        git_ops = FakeGitOps(
            worktrees=worktrees,
            git_common_dirs={env.cwd: env.git_dir},
            current_branches={env.cwd: None},
        )

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=GlobalConfig(
                workstacks_root=env.workstacks_root,
                use_graphite=True,
                shell_setup_complete=False,
                show_pr_info=True,
                show_pr_checks=False,
            ),
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            cwd=env.cwd,
            dry_run=False,
            trunk_branch=None,
        )

        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "detached HEAD state" in result.output


def test_consolidate_not_tracked_by_graphite() -> None:
    """Test consolidate errors if current branch is not tracked by Graphite."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure graphite with only main branch (feature-1 is not tracked)
        graphite_ops = FakeGraphiteOps(stacks={"main": ["main"]})

        # Current branch is "feature-1" but not in Graphite
        worktrees = {env.cwd: [WorktreeInfo(path=env.cwd, branch="feature-1")]}

        test_ctx = _create_test_context(env, worktrees, "feature-1", graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not tracked by Graphite" in result.output


def test_consolidate_skips_non_stack_worktrees() -> None:
    """Test consolidate only removes worktrees with branches in current stack."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure graphite with stack-a only (main -> stack-a)
        # stack-b is a separate branch not in this stack
        graphite_ops = FakeGraphiteOps(stacks={"stack-a": ["main", "stack-a"]})

        # Create worktrees
        wt1_path = env.workstacks_dir / "wt1"
        wt2_path = env.workstacks_dir / "wt2"
        wt1_path.mkdir(parents=True)
        wt2_path.mkdir(parents=True)

        # Current on stack-a, wt1 on main (in stack), wt2 on stack-b (NOT in stack)
        worktrees = {
            env.cwd: [
                WorktreeInfo(path=env.cwd, branch="stack-a"),
                WorktreeInfo(path=wt1_path, branch="main"),
                WorktreeInfo(path=wt2_path, branch="stack-b"),
            ]
        }

        test_ctx = _create_test_context(env, worktrees, "stack-a", graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only wt1 (main) should be removed, wt2 (stack-b) should remain
        assert len(test_ctx.git_ops.removed_worktrees) == 1
        assert wt1_path in test_ctx.git_ops.removed_worktrees
        assert wt2_path not in test_ctx.git_ops.removed_worktrees


def test_consolidate_with_uncommitted_changes_in_non_stack_worktree() -> None:
    """Test consolidate succeeds when non-stack worktrees have uncommitted changes."""
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphiteOps(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Create worktrees
        wt1_path = env.workstacks_dir / "wt1"
        wt2_path = env.workstacks_dir / "wt2"
        wt3_path = env.workstacks_dir / "wt3"
        wt1_path.mkdir(parents=True)
        wt2_path.mkdir(parents=True)
        wt3_path.mkdir(parents=True)

        # Create a file to simulate uncommitted changes in non-stack worktree
        (wt3_path / "uncommitted.txt").write_text("changes", encoding="utf-8")

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
            env, worktrees, "feature-2", graphite_ops, file_statuses=file_statuses
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
    with simulated_workstack_env(runner) as env:
        # Configure graphite with stack (main -> feature-1 -> feature-2)
        graphite_ops = FakeGraphiteOps(stacks={"feature-2": ["main", "feature-1", "feature-2"]})

        # Create worktree directories
        # Root worktree at repo root (on main branch, part of the stack)
        main_worktree = env.cwd / "main-repo"
        main_worktree.mkdir(parents=True)
        # Linked worktree for feature-1
        wt1_path = env.workstacks_dir / "wt1"
        wt1_path.mkdir(parents=True)
        # Current linked worktree for feature-2
        wt2_path = env.workstacks_dir / "wt2"
        wt2_path.mkdir(parents=True)

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

        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=GlobalConfig(
                workstacks_root=env.workstacks_root,
                use_graphite=True,
                shell_setup_complete=False,
                show_pr_info=True,
                show_pr_checks=False,
            ),
            github_ops=FakeGitHubOps(),
            graphite_ops=graphite_ops,
            shell_ops=FakeShellOps(),
            cwd=Path("/test/default/cwd"),
            dry_run=False,
        )

        # Change to wt2_path to simulate running from that worktree
        import os

        original_cwd = os.getcwd()
        os.chdir(wt2_path)
        try:
            result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)
        finally:
            os.chdir(original_cwd)

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
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feat-1 -> feat-2 -> feat-3)
        graphite_ops = FakeGraphiteOps(stacks={"feat-3": ["main", "feat-1", "feat-2", "feat-3"]})

        # Create worktree directories
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt2_path = workstacks_root / repo_name / "wt2"
        wt3_path = workstacks_root / repo_name / "wt3"
        wt1_path.mkdir(parents=True)
        wt2_path.mkdir(parents=True)
        wt3_path.mkdir(parents=True)

        # Three worktrees: wt1 (feat-1), wt2 (feat-2), wt3 (feat-3, current)
        worktrees = {
            cwd: [
                WorktreeInfo(path=wt1_path, branch="feat-1"),
                WorktreeInfo(path=wt2_path, branch="feat-2"),
                WorktreeInfo(path=wt3_path, branch="feat-3"),
            ]
        }

        test_ctx = _create_test_context(
            wt3_path, worktrees, "feat-3", workstacks_root, graphite_ops
        )
        # Override git_common_dirs
        test_ctx.git_ops._git_common_dirs[wt1_path] = cwd / ".git"
        test_ctx.git_ops._git_common_dirs[wt2_path] = cwd / ".git"
        test_ctx.git_ops._git_common_dirs[wt3_path] = cwd / ".git"

        # Run consolidate with branch argument: consolidate feat-2
        # Should consolidate main → feat-2 only, keeping feat-3 separate
        result = runner.invoke(cli, ["consolidate", "feat-2", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should remove wt1 (feat-1) and wt2 (feat-2), but NOT wt3 (feat-3, current)
        assert len(test_ctx.git_ops.removed_worktrees) == 2
        assert wt1_path in test_ctx.git_ops.removed_worktrees
        assert wt2_path in test_ctx.git_ops.removed_worktrees
        assert wt3_path not in test_ctx.git_ops.removed_worktrees


def test_consolidate_with_new_name() -> None:
    """Test consolidating into a new worktree with --name option."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feat-1 -> feat-2)
        graphite_ops = FakeGraphiteOps(stacks={"feat-2": ["main", "feat-1", "feat-2"]})

        # Create worktree directories
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt2_path = workstacks_root / repo_name / "wt2"
        wt1_path.mkdir(parents=True)
        wt2_path.mkdir(parents=True)

        # Two worktrees: wt1 (feat-1), wt2 (feat-2, current)
        worktrees = {
            cwd: [
                WorktreeInfo(path=wt1_path, branch="feat-1"),
                WorktreeInfo(path=wt2_path, branch="feat-2"),
            ]
        }

        test_ctx = _create_test_context(
            wt2_path, worktrees, "feat-2", workstacks_root, graphite_ops
        )
        # Override git_common_dirs
        test_ctx.git_ops._git_common_dirs[wt1_path] = cwd / ".git"
        test_ctx.git_ops._git_common_dirs[wt2_path] = cwd / ".git"

        # Run consolidate with --name option
        result = runner.invoke(cli, ["consolidate", "--name", "my-stack", "-f"], obj=test_ctx)

        # With FakeGitOps, this now succeeds and creates the new worktree
        assert result.exit_code == 0, result.output
        assert "Created new worktree: my-stack" in result.output
        assert "Consolidation complete" in result.output

        # Verify worktree was added
        assert len(test_ctx.git_ops.added_worktrees) == 1
        added_path, added_branch = test_ctx.git_ops.added_worktrees[0]
        assert added_path.name == "my-stack"
        assert added_branch == "feat-2"


def test_consolidate_name_already_exists() -> None:
    """Test that --name errors if worktree already exists."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feat-1)
        graphite_ops = FakeGraphiteOps(stacks={"feat-1": ["main", "feat-1"]})

        # Create worktree directories including one named "my-stack"
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        existing_stack = cwd.parent / "my-stack"
        wt1_path.mkdir(parents=True, exist_ok=True)
        existing_stack.mkdir(parents=True, exist_ok=True)

        # Worktrees: wt1 (feat-1, current) and existing "my-stack"
        worktrees = {
            cwd: [
                WorktreeInfo(path=wt1_path, branch="feat-1"),
                WorktreeInfo(path=existing_stack, branch="other"),
            ]
        }

        test_ctx = _create_test_context(
            wt1_path, worktrees, "feat-1", workstacks_root, graphite_ops
        )
        test_ctx.git_ops._git_common_dirs[wt1_path] = cwd / ".git"
        test_ctx.git_ops._git_common_dirs[existing_stack] = cwd / ".git"

        # Run consolidate with --name for existing worktree
        result = runner.invoke(cli, ["consolidate", "--name", "my-stack", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists" in result.output


def test_consolidate_partial_with_name() -> None:
    """Test combining both features: partial stack + new worktree."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feat-1 -> feat-2 -> feat-3)
        graphite_ops = FakeGraphiteOps(stacks={"feat-3": ["main", "feat-1", "feat-2", "feat-3"]})

        # Create worktree directories
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt2_path = workstacks_root / repo_name / "wt2"
        wt3_path = workstacks_root / repo_name / "wt3"
        wt1_path.mkdir(parents=True)
        wt2_path.mkdir(parents=True)
        wt3_path.mkdir(parents=True)

        # Three worktrees: wt1 (feat-1), wt2 (feat-2), wt3 (feat-3, current)
        worktrees = {
            cwd: [
                WorktreeInfo(path=wt1_path, branch="feat-1"),
                WorktreeInfo(path=wt2_path, branch="feat-2"),
                WorktreeInfo(path=wt3_path, branch="feat-3"),
            ]
        }

        test_ctx = _create_test_context(
            wt3_path, worktrees, "feat-3", workstacks_root, graphite_ops
        )
        # Override git_common_dirs
        test_ctx.git_ops._git_common_dirs[wt1_path] = cwd / ".git"
        test_ctx.git_ops._git_common_dirs[wt2_path] = cwd / ".git"
        test_ctx.git_ops._git_common_dirs[wt3_path] = cwd / ".git"

        # Run consolidate with both branch and --name
        result = runner.invoke(
            cli, ["consolidate", "feat-2", "--name", "my-partial", "-f"], obj=test_ctx
        )

        # With FakeGitOps, this succeeds and creates partial consolidation
        assert result.exit_code == 0, result.output
        assert "Created new worktree: my-partial" in result.output
        assert "Consolidation complete" in result.output

        # Verify worktree was added
        assert len(test_ctx.git_ops.added_worktrees) == 1
        added_path, added_branch = test_ctx.git_ops.added_worktrees[0]
        assert added_path.name == "my-partial"
        assert added_branch == "feat-3"


def test_consolidate_branch_not_in_stack() -> None:
    """Test error when specified branch is not in current stack."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feat-1 -> feat-2)
        graphite_ops = FakeGraphiteOps(stacks={"feat-2": ["main", "feat-1", "feat-2"]})

        # Current worktree on feat-2
        worktrees = {cwd: [WorktreeInfo(path=cwd, branch="feat-2")]}

        test_ctx = _create_test_context(cwd, worktrees, "feat-2", workstacks_root, graphite_ops)

        # Try to consolidate to a branch not in the stack
        result = runner.invoke(cli, ["consolidate", "feat-99", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not in the current stack" in result.output
        assert "feat-99" in result.output


def test_consolidate_preserves_upstack_branches() -> None:
    """Test that branches above the specified branch remain in separate worktrees."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feat-1 -> feat-2 -> feat-3 -> feat-4)
        graphite_ops = FakeGraphiteOps(
            stacks={"feat-4": ["main", "feat-1", "feat-2", "feat-3", "feat-4"]}
        )

        # Create worktree directories
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt2_path = workstacks_root / repo_name / "wt2"
        wt3_path = workstacks_root / repo_name / "wt3"
        wt4_path = workstacks_root / repo_name / "wt4"
        wt1_path.mkdir(parents=True)
        wt2_path.mkdir(parents=True)
        wt3_path.mkdir(parents=True)
        wt4_path.mkdir(parents=True)

        # Four worktrees for feat-1, feat-2, feat-3, feat-4
        # Current is wt4 (feat-4)
        worktrees = {
            cwd: [
                WorktreeInfo(path=wt1_path, branch="feat-1"),
                WorktreeInfo(path=wt2_path, branch="feat-2"),
                WorktreeInfo(path=wt3_path, branch="feat-3"),
                WorktreeInfo(path=wt4_path, branch="feat-4"),
            ]
        }

        test_ctx = _create_test_context(
            wt4_path, worktrees, "feat-4", workstacks_root, graphite_ops
        )
        # Override git_common_dirs
        test_ctx.git_ops._git_common_dirs[wt1_path] = cwd / ".git"
        test_ctx.git_ops._git_common_dirs[wt2_path] = cwd / ".git"
        test_ctx.git_ops._git_common_dirs[wt3_path] = cwd / ".git"
        test_ctx.git_ops._git_common_dirs[wt4_path] = cwd / ".git"

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
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt1_path.mkdir(parents=True)

        worktrees = {
            cwd: [
                WorktreeInfo(path=cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(cwd, worktrees, "feature-1", workstacks_root, graphite_ops)
        result = runner.invoke(cli, ["consolidate", "--script", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify output is shown even with --script flag
        assert "✅ Removed:" in result.output
        assert str(wt1_path) in result.output
        assert "Consolidation complete" in result.output


def test_consolidate_shows_output_without_script_flag() -> None:
    """Test consolidate displays removal output when --script flag is not enabled."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feature-1)
        graphite_ops = FakeGraphiteOps(stacks={"feature-1": ["main", "feature-1"]})

        # Create worktree
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt1_path.mkdir(parents=True)

        worktrees = {
            cwd: [
                WorktreeInfo(path=cwd, branch="feature-1"),
                WorktreeInfo(path=wt1_path, branch="main"),
            ]
        }

        test_ctx = _create_test_context(cwd, worktrees, "feature-1", workstacks_root, graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify output is shown
        assert "✅ Removed:" in result.output
        assert str(wt1_path) in result.output
        assert "Consolidation complete" in result.output
