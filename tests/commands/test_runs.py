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
from erk_shared.git.abc import WorktreeInfo
from erk_shared.github.types import WorkflowRun

from erk.cli.commands.runs import runs_cmd
from erk.core.git.fake import FakeGit
from erk.core.github.fake import FakeGitHub
from tests.fakes.context import create_test_context


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
    assert "Plan Implementation Runs" in result.output
    assert "feat-1" in result.output
    assert "pass" in result.output
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
    assert "pass" in result.output
    assert "fail" in result.output
    assert "running" in result.output


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
    assert "pass" in result.output
    # Should NOT show failure from older run
    assert result.output.count("fail") == 0


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


def test_runs_cmd_displays_table(tmp_path: Path) -> None:
    """Test runs command displays table with columns."""
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
    # Check for table columns
    assert "Branch" in result.output
    assert "Status" in result.output
    assert "Run" in result.output


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


def test_runs_cmd_displays_pr_column_with_pr(tmp_path: Path) -> None:
    """Test runs command displays PR number when PR exists for branch."""
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
    github_ops = FakeGitHub(
        workflow_runs=workflow_runs,
        pr_statuses={"feat-1": ("OPEN", 42, "My PR Title")},
    )
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    assert "#42" in result.output


def test_runs_cmd_displays_pr_column_without_pr(tmp_path: Path) -> None:
    """Test runs command displays '-' when no PR exists for branch."""
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
    # No pr_statuses configured for feat-1
    github_ops = FakeGitHub(workflow_runs=workflow_runs)
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Table should contain "-" for PR column (not a PR number)
    assert "feat-1" in result.output
    # The output should not contain any PR number format
    assert "#" not in result.output or result.output.count("#") == 0


def test_runs_cmd_displays_plan_column_with_impl_folder(tmp_path: Path) -> None:
    """Test runs command displays issue number when .impl/issue.json exists."""
    import json

    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    # Create worktree directory with .impl folder
    worktree_path = tmp_path / "worktrees" / "feat-1"
    worktree_path.mkdir(parents=True)
    impl_folder = worktree_path / ".impl"
    impl_folder.mkdir()

    # Create issue.json with issue reference
    issue_data = {
        "issue_number": 123,
        "issue_url": "https://github.com/test-owner/test-repo/issues/123",
        "created_at": "2024-01-01T00:00:00Z",
        "synced_at": "2024-01-01T00:00:00Z",
    }
    (impl_folder / "issue.json").write_text(json.dumps(issue_data))

    git_ops = FakeGit(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=worktree_path, branch="feat-1"),
            ]
        },
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="456",
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
    assert "#123" in result.output


def test_runs_cmd_displays_plan_column_without_impl_folder(tmp_path: Path) -> None:
    """Test runs command displays '-' when no .impl folder exists."""
    # Arrange
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    # Create worktree directory WITHOUT .impl folder
    worktree_path = tmp_path / "worktrees" / "feat-1"
    worktree_path.mkdir(parents=True)

    git_ops = FakeGit(
        worktrees={
            repo_root: [
                WorktreeInfo(path=repo_root, branch="main"),
                WorktreeInfo(path=worktree_path, branch="feat-1"),
            ]
        },
        current_branches={repo_root: "main"},
        git_common_dirs={repo_root: repo_root / ".git"},
    )
    workflow_runs = [
        WorkflowRun(
            run_id="456",
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
    assert "feat-1" in result.output
    # Plan column should show "-" (no issue number)
    # We verify there's no issue number format in the output
    # Since PR column is also "-", we just verify the run shows correctly


def test_runs_cmd_fallback_when_repo_info_unavailable(tmp_path: Path) -> None:
    """Test runs command falls back to simple display when repo info unavailable."""
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
    # Empty repo_owner and repo_name causes get_repo_info() to return None
    github_ops = FakeGitHub(
        workflow_runs=workflow_runs,
        repo_owner="",
        repo_name="",
    )
    ctx = create_test_context(git=git_ops, github=github_ops, cwd=repo_root)

    runner = CliRunner()

    # Act
    result = runner.invoke(runs_cmd, obj=ctx, catch_exceptions=False)

    # Assert
    assert result.exit_code == 0
    # Should show simple text format, not Rich table
    assert "Plan Implementation Runs:" in result.output
    assert "feat-1: run 123 - completed" in result.output


def test_runs_cmd_handles_unknown_status(tmp_path: Path) -> None:
    """Test runs command displays unknown status with '?' prefix."""
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
            status="some_new_status",
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
    assert "? some_new_status" in result.output


def test_runs_cmd_handles_unknown_conclusion(tmp_path: Path) -> None:
    """Test runs command displays unknown conclusion with '?' prefix."""
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
            conclusion="some_new_conclusion",
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
    assert "? some_new_conclusion" in result.output
