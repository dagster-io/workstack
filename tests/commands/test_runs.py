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


def test_runs_logs_explicit_run_id(tmp_path: Path) -> None:
    """Test viewing logs with explicit run ID."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    github_ops = FakeGitHub(run_logs={"12345": "Step 1: Setup\nStep 2: Tests\n"})
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["logs", "12345"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "Step 1: Setup" in result.output
    assert "Step 2: Tests" in result.output


def test_runs_logs_auto_detect(tmp_path: Path) -> None:
    """Test auto-detecting most recent run for current branch."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="feature-x")]},
        current_branches={repo_root: "feature-x"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="111",
            status="completed",
            conclusion="success",
            branch="main",
            head_sha="abc",
        ),
        WorkflowRun(
            run_id="222",
            status="completed",
            conclusion="success",
            branch="feature-x",
            head_sha="def",
        ),
    ]
    github_ops = FakeGitHub(
        workflow_runs=workflow_runs, run_logs={"222": "Logs for feature-x run\n"}
    )
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["logs"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "Showing logs for run 222" in result.output
    assert "Logs for feature-x run" in result.output


def test_runs_logs_run_not_found(tmp_path: Path) -> None:
    """Test error handling when run doesn't exist."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="main")]},
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    github_ops = FakeGitHub(run_logs={})  # No logs configured
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["logs", "99999"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "99999" in result.output


def test_runs_logs_no_runs_for_branch(tmp_path: Path) -> None:
    """Test auto-detect when no runs exist for current branch."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="feature-y")]},
        current_branches={repo_root: "feature-y"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="111",
            status="completed",
            conclusion="success",
            branch="main",
            head_sha="abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["logs"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 1
    assert "No workflow runs found for branch: feature-y" in result.output


def test_runs_current_with_run_found(tmp_path: Path) -> None:
    """Test runs current command with run found returns all WorkflowRun fields."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="feat-1")]},
        current_branches={repo_root: "feat-1"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="1234567890",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc123def456",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["current"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0

    # Parse JSON output
    import json
    output_json = json.loads(result.output)

    # Verify all WorkflowRun fields are present
    assert output_json["run_id"] == "1234567890"
    assert output_json["status"] == "completed"
    assert output_json["conclusion"] == "success"
    assert output_json["branch"] == "feat-1"
    assert output_json["head_sha"] == "abc123def456"


def test_runs_current_with_no_runs(tmp_path: Path) -> None:
    """Test runs current command with no runs returns no_run status object."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="feat-1")]},
        current_branches={repo_root: "feat-1"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    github_ops = FakeGitHub(workflow_runs=[])  # Empty runs
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["current"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0

    # Parse JSON output
    import json
    output_json = json.loads(result.output)

    assert output_json == {"status": "no_run"}


def test_runs_current_detached_head(tmp_path: Path) -> None:
    """Test runs current command with detached HEAD returns error object."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="HEAD")]},
        current_branches={repo_root: None},  # Simulates detached HEAD
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    github_ops = FakeGitHub(workflow_runs=[])
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["current"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 1

    # Parse JSON output
    import json
    output_json = json.loads(result.output)

    assert output_json["status"] == "error"
    assert output_json["error"] == "Could not determine current branch"


def test_runs_current_json_structure_validity(tmp_path: Path) -> None:
    """Test runs current command output is valid JSON with correct field types."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="feat-1")]},
        current_branches={repo_root: "feat-1"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="123",
            status="in_progress",
            conclusion=None,  # None conclusion while in progress
            branch="feat-1",
            head_sha="abc",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["current"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0

    # Verify JSON can be parsed
    import json
    output_json = json.loads(result.output)

    # Verify field types
    assert isinstance(output_json["run_id"], str)
    assert isinstance(output_json["status"], str)
    assert output_json["conclusion"] is None  # None is valid for in_progress
    assert isinstance(output_json["branch"], str)
    assert isinstance(output_json["head_sha"], str)


def test_runs_current_filters_by_current_branch(tmp_path: Path) -> None:
    """Test runs current command correctly filters by current branch."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    git_ops = FakeGit(
        worktrees={repo_root: [WorktreeInfo(path=repo_root, branch="feat-2")]},
        current_branches={repo_root: "feat-2"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="111",
            status="completed",
            conclusion="success",
            branch="feat-1",
            head_sha="abc",
        ),
        WorkflowRun(
            run_id="222",
            status="completed",
            conclusion="failure",
            branch="feat-2",
            head_sha="def",
        ),
        WorkflowRun(
            run_id="333",
            status="completed",
            conclusion="success",
            branch="feat-3",
            head_sha="ghi",
        ),
    ]
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, ["current"], obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0

    # Parse JSON output
    import json
    output_json = json.loads(result.output)

    # Should return only feat-2's run, not feat-1 or feat-3
    assert output_json["run_id"] == "222"
    assert output_json["branch"] == "feat-2"
    assert output_json["conclusion"] == "failure"
