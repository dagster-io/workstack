"""Tests for workstack split command.

This file tests the split command which creates individual worktrees for each
branch in a Graphite stack.
"""

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from tests.test_utils.env_helpers import pure_workstack_env
from workstack.cli.cli import cli
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo


def _create_test_context_for_split(
    env,
    stack_branches: list[str],
    current_branch: str | None,
    existing_worktrees: list[WorktreeInfo] | None = None,
    trunk_branch: str = "main",
    has_uncommitted: bool = False,
) -> WorkstackContext:
    """Helper to create test context for split command tests.

    Args:
        env: Test environment from pure_workstack_env or simulated_workstack_env
        stack_branches: Branches in the stack (trunk to leaf order)
        current_branch: Currently checked out branch
        existing_worktrees: List of existing WorktreeInfo objects
        trunk_branch: Name of trunk branch (main or master)
        has_uncommitted: Whether to simulate uncommitted changes
    """
    # Configure graphite with stack
    if current_branch and current_branch in stack_branches:
        graphite_ops = FakeGraphiteOps(stacks={current_branch: stack_branches})
    else:
        # For detached HEAD or untracked branches, use trunk as key
        graphite_ops = FakeGraphiteOps(stacks={trunk_branch: stack_branches})

    # Default worktrees if not provided
    if existing_worktrees is None:
        existing_worktrees = [
            WorktreeInfo(path=env.cwd, branch=current_branch, is_root=True),
        ]

    # Configure git ops
    file_statuses = None
    if has_uncommitted:
        # Simulate uncommitted changes with modified files
        file_statuses = {env.cwd: ([], ["modified_file.py"], [])}  # (staged, modified, untracked)

    git_ops = FakeGitOps(
        worktrees={env.cwd: existing_worktrees},
        current_branches={env.cwd: current_branch},
        file_statuses=file_statuses,
        trunk_branches={env.cwd: trunk_branch},  # Configure trunk branch properly
    )

    return env.build_context(
        git_ops=git_ops,
        graphite_ops=graphite_ops,
        github_ops=FakeGitHubOps(),
        shell_ops=FakeShellOps(),
        use_graphite=True,
    )


# Basic functionality tests


def test_split_full_stack() -> None:
    """Default behavior splits entire stack into individual worktrees."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2", "feat-3"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "feat-2")

        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Will create:" in result.output
        # feat-1 and feat-3 should be created (not main or current feat-2)
        assert "feat-1" in result.output
        assert "feat-3" in result.output
        # Check that worktrees were created via git_ops
        assert len(test_ctx.git_ops.added_worktrees) == 2


def test_split_excludes_trunk() -> None:
    """Trunk branch stays in root worktree and is not split."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "feat-1")

        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Main should be marked as staying in root
        assert "trunk (stays in root)" in result.output
        # Main should not be in the "will create" list
        assert len(test_ctx.git_ops.added_worktrees) == 0  # Only feat-1, which is current


def test_split_excludes_current_branch() -> None:
    """Current branch cannot be duplicated in another worktree."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "feat-1")

        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # feat-1 should be marked as current/already checked out
        assert "current (already checked out)" in result.output
        # Only feat-2 should be created
        assert "feat-2" in result.output
        assert len(test_ctx.git_ops.added_worktrees) == 1


def test_split_preserves_existing_worktrees() -> None:
    """Idempotent operation - existing worktrees are preserved."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        existing_worktrees = [
            WorktreeInfo(path=env.cwd, branch="main", is_root=True),
            WorktreeInfo(path=env.workstacks_root / "feat-1", branch="feat-1", is_root=False),
        ]
        test_ctx = _create_test_context_for_split(env, stack_branches, "main", existing_worktrees)

        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # feat-1 should be marked as already having a worktree
        assert "already has worktree" in result.output
        # Only feat-2 should be created
        assert len(test_ctx.git_ops.added_worktrees) == 1


# Flag combination tests


def test_split_with_up_flag() -> None:
    """--up flag only splits upstack branches."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2", "feat-3"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "feat-2")

        result = runner.invoke(cli, ["split", "--up", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only feat-3 should be created (upstack from feat-2)
        assert "feat-3" in result.output
        assert "feat-1" not in result.output  # Downstack, not included
        assert len(test_ctx.git_ops.added_worktrees) == 1


def test_split_with_down_flag() -> None:
    """--down flag only splits downstack branches."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2", "feat-3"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "feat-2")

        result = runner.invoke(cli, ["split", "--down", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only feat-1 should be created (downstack from feat-2, main excluded)
        assert "feat-1" in result.output
        assert "feat-3" not in result.output  # Upstack, not included
        assert len(test_ctx.git_ops.added_worktrees) == 1


def test_split_up_and_down_conflict() -> None:
    """Error when both --up and --down flags are used."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "feat-1")

        result = runner.invoke(cli, ["split", "--up", "--down"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Cannot use --up and --down together" in result.output


def test_split_with_force_flag() -> None:
    """--force flag skips confirmation prompt."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "main")

        # Without -f, would need interactive confirmation
        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Split complete:" in result.output


def test_split_with_dry_run() -> None:
    """--dry-run shows preview without creating worktrees."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "main")

        result = runner.invoke(cli, ["split", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN] Would create:" in result.output
        assert "[DRY RUN] No changes made" in result.output
        # No actual worktrees created
        assert len(test_ctx.git_ops.added_worktrees) == 0


# Edge case tests


def test_split_detached_head_state() -> None:
    """Handle detached HEAD state gracefully."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        test_ctx = _create_test_context_for_split(env, stack_branches, None)  # Detached HEAD

        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should split feat-1 and feat-2 (main excluded as trunk)
        assert "feat-1" in result.output
        assert "feat-2" in result.output
        assert len(test_ctx.git_ops.added_worktrees) == 2


def test_split_untracked_branch() -> None:
    """Error when branch is not tracked by Graphite."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Empty graphite_ops - no tracked branches
        graphite_ops = FakeGraphiteOps(stacks={})
        git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="untracked")]},
            current_branches={env.cwd: "untracked"},
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["split"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not tracked by Graphite" in result.output


def test_split_no_graphite_init() -> None:
    """Error when repository doesn't have Graphite initialized."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Graphite returns None for uninitialized repo
        graphite_ops = FakeGraphiteOps(stacks=None)  # Returns None for all branches
        git_ops = FakeGitOps(
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main")]},
            current_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(
            git_ops=git_ops,
            graphite_ops=graphite_ops,
            use_graphite=True,
        )

        result = runner.invoke(cli, ["split"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not tracked by Graphite" in result.output
        assert "gt repo init" in result.output  # Suggests initialization


def test_split_uncommitted_changes() -> None:
    """Safety check prevents split with uncommitted changes."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "main", has_uncommitted=True)

        result = runner.invoke(cli, ["split"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Uncommitted changes detected" in result.output
        assert "Commit or stash" in result.output


def test_split_uncommitted_changes_with_force() -> None:
    """--force flag still allows split with uncommitted changes."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "main", has_uncommitted=True)

        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should proceed with split
        assert "Split complete:" in result.output


def test_split_all_branches_have_worktrees() -> None:
    """Nothing to do when all branches already have worktrees."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1"]
        existing_worktrees = [
            WorktreeInfo(path=env.cwd, branch="main", is_root=True),
            WorktreeInfo(path=env.workstacks_root / "feat-1", branch="feat-1", is_root=False),
        ]
        test_ctx = _create_test_context_for_split(env, stack_branches, "main", existing_worktrees)

        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "All branches already have worktrees" in result.output
        assert len(test_ctx.git_ops.added_worktrees) == 0


# Output verification tests


def test_split_output_formatting() -> None:
    """Verify correct colors and symbols in output."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2", "feat-3"]
        existing_worktrees = [
            WorktreeInfo(path=env.cwd, branch="feat-2", is_root=False),  # Current is feat-2
            WorktreeInfo(path=env.workstacks_root / "main", branch="main", is_root=True),
            WorktreeInfo(path=env.workstacks_root / "feat-1", branch="feat-1", is_root=False),
        ]
        test_ctx = _create_test_context_for_split(
            env,
            stack_branches,
            "feat-2",
            existing_worktrees,  # Current is feat-2, not main
        )

        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Check for expected markers
        assert "← trunk (stays in root)" in result.output  # main
        assert "← current (already checked out)" in result.output  # feat-2
        assert "✓ already has worktree" in result.output  # feat-1
        assert "→ will create worktree" in result.output  # feat-3


def test_split_dry_run_output() -> None:
    """Dry run shows clear preview of what would be created."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "main")

        result = runner.invoke(cli, ["split", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN] Would create:" in result.output
        # Should show paths where worktrees would be created
        assert "feat-1 at" in result.output
        assert "feat-2 at" in result.output
        assert "[DRY RUN] No changes made" in result.output


def test_split_success_messages() -> None:
    """Successful split shows completion confirmation."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main", "feat-1", "feat-2"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "main")

        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "✅ Created worktree for" in result.output
        assert "✅ Split complete:" in result.output
        assert "created 2 worktree(s)" in result.output


def test_split_with_master_as_trunk() -> None:
    """Handle 'master' as trunk branch instead of 'main'."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["master", "feat-1"]
        test_ctx = _create_test_context_for_split(
            env, stack_branches, "feat-1", trunk_branch="master"
        )

        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Master should be marked as trunk
        assert "trunk (stays in root)" in result.output
        # feat-1 is current, so nothing to create
        assert len(test_ctx.git_ops.added_worktrees) == 0


def test_split_empty_stack() -> None:
    """Handle edge case of single-branch stack (just trunk)."""
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        stack_branches = ["main"]
        test_ctx = _create_test_context_for_split(env, stack_branches, "main")

        result = runner.invoke(cli, ["split", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "All branches already have worktrees or are excluded" in result.output
        assert len(test_ctx.git_ops.added_worktrees) == 0
