"""CLI tests for erk runs command.

This file focuses on CLI-specific concerns for the runs command:
- Command execution and exit codes
- Output formatting and display (status indicators, colors)
- Grouping by branch (most recent per branch)
- Error handling and empty state messages

The integration layer (list_workflow_runs) is tested in:
- tests/unit/fakes/test_fake_github.py - Fake infrastructure tests
- tests/integration/test_real_github.py - Real implementation tests

This file trusts that unit layer and only tests CLI integration.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.runs import runs_cmd
from erk.core.github.types import WorkflowRun
from tests.fakes.context import create_test_context
from tests.fakes.git import FakeGit, WorktreeInfo
from tests.fakes.github import FakeGitHub


def test_runs_cmd_empty_state(tmp_path: Path) -> None:
    """Test runs command displays message when no runs found."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    github_ops = FakeGitHub(workflow_runs=[])  # Empty runs
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "No workflow runs found" in result.output


def test_runs_cmd_single_success_run(tmp_path: Path) -> None:
    """Test runs command displays single successful run."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="1234567890",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "Plan Implementation Runs:" in result.output
    assert "feat-1" in result.output
    assert "success" in result.output
    assert "1234567890" in result.output


def test_runs_cmd_multiple_runs_different_branches(tmp_path: Path) -> None:
    """Test runs command displays multiple runs from different branches."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
        ),
        WorkflowRun(
            run_id="456",
            status="completed",
            conclusion="failure",
            branch="feat-2",
            head_sha="def456",
        ),
        WorkflowRun(
            run_id="789",
            status="in_progress",
            conclusion=None,
            branch="feat-3",
            head_sha="ghi789",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "feat-1" in result.output
    assert "feat-2" in result.output
    assert "feat-3" in result.output
    assert "success" in result.output
    assert "failure" in result.output
    assert "in_progress" in result.output


def test_runs_cmd_groups_by_branch_keeps_latest(tmp_path: Path) -> None:
    """Test runs command groups by branch and keeps most recent."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    # Multiple runs for same branch - first one should be shown (most recent)
    workflow_runs = [
        WorkflowRun(
            run_id="newer-run",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="new123",
        ),
        WorkflowRun(
            run_id="older-run",
            status="completed",
            conclusion="failure",
            branch="feat-1",
            head_sha="old456",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Should show newer run, not older
    assert "newer-run" in result.output
    assert "older-run" not in result.output
    assert "success" in result.output
    # Should NOT show failure from older run
    assert result.output.count("failure") == 0


def test_runs_cmd_handles_cancelled_status(tmp_path: Path) -> None:
    """Test runs command displays cancelled status correctly."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="cancelled",
            branch="feat-1",
            head_sha="abc123",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "cancelled" in result.output


def test_runs_cmd_handles_queued_status(tmp_path: Path) -> None:
    """Test runs command displays queued status correctly."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="queued",
            conclusion=None,
            branch="feat-1",
            head_sha="abc123",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "queued" in result.output


def test_runs_cmd_shows_help_text(tmp_path: Path) -> None:
    """Test runs command shows help text at the end."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "View details: gh run view" in result.output
