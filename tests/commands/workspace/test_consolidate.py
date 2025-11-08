"""Tests for workstack consolidate command.

This file tests the consolidate command which removes worktrees containing
branches from the current Graphite stack.
"""

from pathlib import Path

from click.testing import CliRunner

from tests.fakes.github_ops import FakeGitHubOps
from tests.fakes.gitops import FakeGitOps
from tests.fakes.global_config_ops import FakeGlobalConfigOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.shell_ops import FakeShellOps
from workstack.cli.cli import cli
from workstack.core.branch_metadata import BranchMetadata
from workstack.core.context import WorkstackContext
from workstack.core.gitops import WorktreeInfo


def _create_test_context(
    cwd: Path,
    worktrees: dict[Path, list[WorktreeInfo]],
    current_branch: str,
    workstacks_root: Path,
    graphite_ops: FakeGraphiteOps,
    *,
    file_statuses: dict[Path, tuple[list[str], list[str], list[str]]] | None = None,
) -> WorkstackContext:
    """Helper to create test context for consolidate command tests.

    Args:
        cwd: Current working directory (repo root)
        worktrees: Map of repo_root to list of WorktreeInfo objects
        current_branch: Current branch name
        workstacks_root: Root directory for workstacks
        graphite_ops: FakeGraphiteOps configured with branch stack data
        file_statuses: Optional mapping of worktree paths to (staged, modified, untracked) files

    Returns:
        WorkstackContext configured for testing
    """
    git_dir = cwd / ".git"
    git_ops = FakeGitOps(
        worktrees=worktrees,
        git_common_dirs={cwd: git_dir},
        current_branches={cwd: current_branch},
        file_statuses=file_statuses,
    )

    return WorkstackContext(
        git_ops=git_ops,
        global_config_ops=FakeGlobalConfigOps(workstacks_root=workstacks_root, use_graphite=True),
        github_ops=FakeGitHubOps(),
        graphite_ops=graphite_ops,
        shell_ops=FakeShellOps(),
        dry_run=False,
    )


def test_consolidate_no_other_worktrees() -> None:
    """Test consolidate when no other worktrees contain stack branches."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feature-1 -> feature-2)
        branches = {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["feature-1"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "feature-1": BranchMetadata(
                name="feature-1",
                parent="main",
                children=["feature-2"],
                is_trunk=False,
                commit_sha="abc123",
            ),
            "feature-2": BranchMetadata(
                name="feature-2",
                parent="feature-1",
                children=[],
                is_trunk=False,
                commit_sha="abc123",
            ),
        }
        graphite_ops = FakeGraphiteOps(
            stacks={"feature-2": ["main", "feature-1", "feature-2"]}, branches=branches
        )

        # Current worktree only (on feature-2)
        worktrees = {cwd: [WorktreeInfo(path=cwd, branch="feature-2")]}

        test_ctx = _create_test_context(cwd, worktrees, "feature-2", workstacks_root, graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "No other worktrees found" in result.output


def test_consolidate_removes_other_stack_worktrees() -> None:
    """Test consolidate removes worktrees with branches from current stack."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feature-1 -> feature-2 -> feature-3)
        # and branch metadata marking main as trunk
        branches = {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["feature-1"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "feature-1": BranchMetadata(
                name="feature-1",
                parent="main",
                children=["feature-2"],
                is_trunk=False,
                commit_sha="abc123",
            ),
            "feature-2": BranchMetadata(
                name="feature-2",
                parent="feature-1",
                children=["feature-3"],
                is_trunk=False,
                commit_sha="abc123",
            ),
            "feature-3": BranchMetadata(
                name="feature-3",
                parent="feature-2",
                children=[],
                is_trunk=False,
                commit_sha="abc123",
            ),
        }

        graphite_ops = FakeGraphiteOps(
            stacks={"feature-3": ["main", "feature-1", "feature-2", "feature-3"]},
            branches=branches,
        )

        # Create worktree directories
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt2_path = workstacks_root / repo_name / "wt2"
        wt1_path.mkdir(parents=True)
        wt2_path.mkdir(parents=True)

        # Current worktree on feature-3, other worktrees on feature-1 and feature-2
        worktrees = {
            cwd: [
                WorktreeInfo(path=cwd, branch="feature-3"),
                WorktreeInfo(path=wt1_path, branch="feature-1"),
                WorktreeInfo(path=wt2_path, branch="feature-2"),
            ]
        }

        test_ctx = _create_test_context(cwd, worktrees, "feature-3", workstacks_root, graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Removed:" in result.output
        assert str(wt1_path) in result.output
        assert str(wt2_path) in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 2


def test_consolidate_preserves_current_worktree() -> None:
    """Test consolidate preserves the current worktree even if it's in the stack."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feature-1 -> feature-2)
        # Use feature-1 and feature-2 so both are non-trunk
        branches = {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["feature-1"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "feature-1": BranchMetadata(
                name="feature-1",
                parent="main",
                children=["feature-2"],
                is_trunk=False,
                commit_sha="abc123",
            ),
            "feature-2": BranchMetadata(
                name="feature-2",
                parent="feature-1",
                children=[],
                is_trunk=False,
                commit_sha="abc123",
            ),
        }
        graphite_ops = FakeGraphiteOps(
            stacks={"feature-2": ["main", "feature-1", "feature-2"]}, branches=branches
        )

        # Create other worktree
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt1_path.mkdir(parents=True)

        # Both worktrees in same stack, current is on feature-2
        worktrees = {
            cwd: [
                WorktreeInfo(path=cwd, branch="feature-2"),
                WorktreeInfo(path=wt1_path, branch="feature-1"),
            ]
        }

        test_ctx = _create_test_context(cwd, worktrees, "feature-2", workstacks_root, graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only wt1 should be removed, not cwd
        assert len(test_ctx.git_ops.removed_worktrees) == 1
        assert wt1_path in test_ctx.git_ops.removed_worktrees


def test_consolidate_aborts_on_uncommitted_changes() -> None:
    """Test consolidate aborts if ANY worktree has uncommitted changes."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feature-1 -> feature-2)
        branches = {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["feature-1"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "feature-1": BranchMetadata(
                name="feature-1",
                parent="main",
                children=["feature-2"],
                is_trunk=False,
                commit_sha="abc123",
            ),
            "feature-2": BranchMetadata(
                name="feature-2",
                parent="feature-1",
                children=[],
                is_trunk=False,
                commit_sha="abc123",
            ),
        }
        graphite_ops = FakeGraphiteOps(
            stacks={"feature-2": ["main", "feature-1", "feature-2"]}, branches=branches
        )

        # Create worktree with uncommitted changes marker
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt1_path.mkdir(parents=True)
        # Create a file to simulate uncommitted changes
        (wt1_path / "uncommitted.txt").write_text("changes", encoding="utf-8")

        worktrees = {
            cwd: [
                WorktreeInfo(path=cwd, branch="feature-2"),
                WorktreeInfo(path=wt1_path, branch="feature-1"),
            ]
        }

        # Configure file_statuses to simulate uncommitted changes in wt1
        file_statuses = {
            wt1_path: ([], [], ["uncommitted.txt"]),  # Untracked file
        }

        test_ctx = _create_test_context(
            cwd, worktrees, "feature-2", workstacks_root, graphite_ops, file_statuses=file_statuses
        )
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Uncommitted changes detected" in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 0


def test_consolidate_dry_run_shows_preview() -> None:
    """Test --dry-run shows what would be removed without executing."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feature-1 -> feature-2)
        branches = {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["feature-1"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "feature-1": BranchMetadata(
                name="feature-1",
                parent="main",
                children=["feature-2"],
                is_trunk=False,
                commit_sha="abc123",
            ),
            "feature-2": BranchMetadata(
                name="feature-2",
                parent="feature-1",
                children=[],
                is_trunk=False,
                commit_sha="abc123",
            ),
        }
        graphite_ops = FakeGraphiteOps(
            stacks={"feature-2": ["main", "feature-1", "feature-2"]}, branches=branches
        )

        # Create worktree
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt1_path.mkdir(parents=True)

        worktrees = {
            cwd: [
                WorktreeInfo(path=cwd, branch="feature-2"),
                WorktreeInfo(path=wt1_path, branch="feature-1"),
            ]
        }

        test_ctx = _create_test_context(cwd, worktrees, "feature-2", workstacks_root, graphite_ops)
        result = runner.invoke(cli, ["consolidate", "--dry-run"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert str(wt1_path) in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 0
        assert wt1_path.exists()


def test_consolidate_confirmation_prompt() -> None:
    """Test consolidate prompts for confirmation without --force."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feature-1 -> feature-2)
        branches = {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["feature-1"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "feature-1": BranchMetadata(
                name="feature-1",
                parent="main",
                children=["feature-2"],
                is_trunk=False,
                commit_sha="abc123",
            ),
            "feature-2": BranchMetadata(
                name="feature-2",
                parent="feature-1",
                children=[],
                is_trunk=False,
                commit_sha="abc123",
            ),
        }
        graphite_ops = FakeGraphiteOps(
            stacks={"feature-2": ["main", "feature-1", "feature-2"]}, branches=branches
        )

        # Create worktree
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt1_path.mkdir(parents=True)

        worktrees = {
            cwd: [
                WorktreeInfo(path=cwd, branch="feature-2"),
                WorktreeInfo(path=wt1_path, branch="feature-1"),
            ]
        }

        test_ctx = _create_test_context(cwd, worktrees, "feature-2", workstacks_root, graphite_ops)

        # Test saying "no" to prompt
        result = runner.invoke(cli, ["consolidate"], input="n\n", obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Proceed with removal?" in result.output
        assert "Aborted" in result.output
        assert len(test_ctx.git_ops.removed_worktrees) == 0


def test_consolidate_detached_head_error() -> None:
    """Test consolidate aborts if current worktree is in detached HEAD state."""
    runner = CliRunner()
    cwd = Path("/fake/repo")
    workstacks_root = cwd / "workstacks"
    git_dir = cwd / ".git"

    # Current worktree with detached HEAD (None branch)
    worktrees = {cwd: [WorktreeInfo(path=cwd, branch=None)]}

    # Create context with no current branch
    git_ops = FakeGitOps(
        worktrees=worktrees,
        git_common_dirs={cwd: git_dir},
        current_branches={cwd: None},
    )

    test_ctx = WorkstackContext(
        git_ops=git_ops,
        global_config_ops=FakeGlobalConfigOps(workstacks_root=workstacks_root, use_graphite=True),
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
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with only main branch (feature-1 is not tracked)
        graphite_ops = FakeGraphiteOps(stacks={"main": ["main"]})

        # Current branch is "feature-1" but not in Graphite
        worktrees = {cwd: [WorktreeInfo(path=cwd, branch="feature-1")]}

        test_ctx = _create_test_context(cwd, worktrees, "feature-1", workstacks_root, graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 1
        assert "not tracked by Graphite" in result.output


def test_consolidate_skips_non_stack_worktrees() -> None:
    """Test consolidate only removes worktrees with branches in current stack."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack-a only (main -> stack-a-1 -> stack-a-2)
        # stack-b is a separate branch not in this stack
        branches = {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["stack-a-1"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "stack-a-1": BranchMetadata(
                name="stack-a-1",
                parent="main",
                children=["stack-a-2"],
                is_trunk=False,
                commit_sha="abc123",
            ),
            "stack-a-2": BranchMetadata(
                name="stack-a-2",
                parent="stack-a-1",
                children=[],
                is_trunk=False,
                commit_sha="abc123",
            ),
        }
        graphite_ops = FakeGraphiteOps(
            stacks={"stack-a-2": ["main", "stack-a-1", "stack-a-2"]}, branches=branches
        )

        # Create worktrees
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt2_path = workstacks_root / repo_name / "wt2"
        wt1_path.mkdir(parents=True)
        wt2_path.mkdir(parents=True)

        # Current on stack-a-2, wt1 on stack-a-1 (in stack), wt2 on stack-b (NOT in stack)
        worktrees = {
            cwd: [
                WorktreeInfo(path=cwd, branch="stack-a-2"),
                WorktreeInfo(path=wt1_path, branch="stack-a-1"),
                WorktreeInfo(path=wt2_path, branch="stack-b"),
            ]
        }

        test_ctx = _create_test_context(cwd, worktrees, "stack-a-2", workstacks_root, graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only wt1 (stack-a-1) should be removed, wt2 (stack-b) should remain
        assert len(test_ctx.git_ops.removed_worktrees) == 1
        assert wt1_path in test_ctx.git_ops.removed_worktrees
        assert wt2_path not in test_ctx.git_ops.removed_worktrees


def test_consolidate_protects_trunk_branches() -> None:
    """Test consolidate never suggests removing trunk branch worktrees."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feature-1 -> feature-2)
        # Main is trunk, feature branches are not
        branches = {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["feature-1"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "feature-1": BranchMetadata(
                name="feature-1",
                parent="main",
                children=["feature-2"],
                is_trunk=False,
                commit_sha="abc123",
            ),
            "feature-2": BranchMetadata(
                name="feature-2",
                parent="feature-1",
                children=[],
                is_trunk=False,
                commit_sha="abc123",
            ),
        }
        graphite_ops = FakeGraphiteOps(
            stacks={"feature-2": ["main", "feature-1", "feature-2"]}, branches=branches
        )

        # Create worktrees
        repo_name = cwd.name
        wt_main = workstacks_root / repo_name / "wt-main"
        wt_f1 = workstacks_root / repo_name / "wt-f1"
        wt_main.mkdir(parents=True)
        wt_f1.mkdir(parents=True)

        # Current worktree on feature-2, other worktrees on main (trunk) and feature-1
        worktrees = {
            cwd: [
                WorktreeInfo(path=cwd, branch="feature-2"),
                WorktreeInfo(path=wt_main, branch="main"),
                WorktreeInfo(path=wt_f1, branch="feature-1"),
            ]
        }

        test_ctx = _create_test_context(cwd, worktrees, "feature-2", workstacks_root, graphite_ops)
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Only feature-1 worktree should be removed, NOT main (trunk)
        assert len(test_ctx.git_ops.removed_worktrees) == 1
        assert wt_f1 in test_ctx.git_ops.removed_worktrees
        assert wt_main not in test_ctx.git_ops.removed_worktrees


def test_consolidate_with_uncommitted_changes_in_non_stack_worktree() -> None:
    """Test consolidate succeeds when non-stack worktrees have uncommitted changes."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        workstacks_root = cwd / "workstacks"

        # Configure graphite with stack (main -> feature-1 -> feature-2 -> feature-3)
        branches = {
            "main": BranchMetadata(
                name="main",
                parent=None,
                children=["feature-1"],
                is_trunk=True,
                commit_sha="abc123",
            ),
            "feature-1": BranchMetadata(
                name="feature-1",
                parent="main",
                children=["feature-2"],
                is_trunk=False,
                commit_sha="abc123",
            ),
            "feature-2": BranchMetadata(
                name="feature-2",
                parent="feature-1",
                children=["feature-3"],
                is_trunk=False,
                commit_sha="abc123",
            ),
            "feature-3": BranchMetadata(
                name="feature-3",
                parent="feature-2",
                children=[],
                is_trunk=False,
                commit_sha="abc123",
            ),
        }
        graphite_ops = FakeGraphiteOps(
            stacks={"feature-3": ["main", "feature-1", "feature-2", "feature-3"]}, branches=branches
        )

        # Create worktrees
        repo_name = cwd.name
        wt1_path = workstacks_root / repo_name / "wt1"
        wt2_path = workstacks_root / repo_name / "wt2"
        wt3_path = workstacks_root / repo_name / "wt3"
        wt1_path.mkdir(parents=True)
        wt2_path.mkdir(parents=True)
        wt3_path.mkdir(parents=True)

        # Create a file to simulate uncommitted changes in non-stack worktree
        (wt3_path / "uncommitted.txt").write_text("changes", encoding="utf-8")

        # Current on feature-3, wt1 on feature-1 (in stack), wt2 on feature-2 (in stack),
        # wt3 on other-branch (NOT in stack, has uncommitted changes)
        worktrees = {
            cwd: [
                WorktreeInfo(path=cwd, branch="feature-3"),
                WorktreeInfo(path=wt1_path, branch="feature-1"),
                WorktreeInfo(path=wt2_path, branch="feature-2"),
                WorktreeInfo(path=wt3_path, branch="other-branch"),
            ]
        }

        # Configure file_statuses to simulate uncommitted changes in non-stack worktree
        file_statuses = {
            wt3_path: ([], [], ["uncommitted.txt"]),  # Untracked file in non-stack worktree
        }

        test_ctx = _create_test_context(
            cwd, worktrees, "feature-3", workstacks_root, graphite_ops, file_statuses=file_statuses
        )
        result = runner.invoke(cli, ["consolidate", "-f"], obj=test_ctx)

        # Command should succeed despite uncommitted changes in non-stack worktree
        assert result.exit_code == 0, result.output
        # Only feature-1 and feature-2 worktrees should be removed (main is trunk, protected)
        assert len(test_ctx.git_ops.removed_worktrees) == 2
        assert wt1_path in test_ctx.git_ops.removed_worktrees
        assert wt2_path in test_ctx.git_ops.removed_worktrees
        # other-branch worktree should remain untouched
        assert wt3_path not in test_ctx.git_ops.removed_worktrees
