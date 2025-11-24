"""Tests for create-erp-from-issue kit CLI command.

Layer 4 (Business Logic Tests): Tests command logic over fakes.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues, IssueInfo

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_erp_from_issue import (
    create_erp_from_issue,
)


def test_create_erp_from_issue_success(tmp_path: Path) -> None:
    """Test successful .erp/ folder creation from issue."""
    # Arrange: Set up fake GitHub Issues with test data
    plan_content = "# Test Plan\n\nThis is a test plan."
    issue = IssueInfo(
        number=1028,
        title="Test Issue Title",
        body=plan_content,
        state="OPEN",
        url="https://github.com/owner/repo/issues/1028",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    fake_github = FakeGitHubIssues(issues={1028: issue})

    # Create context with fake GitHub Issues
    ctx = DotAgentContext.for_test(
        github_issues=fake_github,
        repo_root=tmp_path,
        cwd=tmp_path,
    )

    # Act: Run command
    runner = CliRunner()
    result = runner.invoke(
        create_erp_from_issue,
        ["1028", "Test Issue Title"],
        obj=ctx,
    )

    # Assert: Command succeeded
    assert result.exit_code == 0

    # Assert: Output is valid JSON with expected fields
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1028
    assert output["issue_url"] == "https://github.com/owner/repo/issues/1028"
    assert "erp_path" in output

    # Assert: .erp/ folder was created with expected files
    erp_path = tmp_path / ".erp"
    assert erp_path.exists()
    assert (erp_path / "plan.md").exists()
    assert (erp_path / "issue.json").exists()

    # Assert: plan.md contains the plan content
    plan_content_read = (erp_path / "plan.md").read_text(encoding="utf-8")
    assert plan_content in plan_content_read


def test_create_erp_from_issue_issue_not_found(tmp_path: Path) -> None:
    """Test error handling when issue cannot be fetched."""
    # Arrange: Set up fake GitHub Issues with no issues
    fake_github = FakeGitHubIssues(issues={})

    # Create context
    ctx = DotAgentContext.for_test(
        github_issues=fake_github,
        repo_root=tmp_path,
        cwd=tmp_path,
    )

    # Act: Run command with non-existent issue
    runner = CliRunner()
    result = runner.invoke(
        create_erp_from_issue,
        ["999", "Non-existent Issue"],
        obj=ctx,
    )

    # Assert: Command failed with exit code 1
    assert result.exit_code == 1

    # Assert: Error output is valid JSON with error details
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "issue_not_found"
    assert "Could not fetch issue" in output["message"]

    # Assert: .erp/ folder was NOT created
    erp_path = tmp_path / ".erp"
    assert not erp_path.exists()


def test_create_erp_from_issue_missing_erk_plan_label(tmp_path: Path) -> None:
    """Test error handling when issue lacks erk-plan label."""
    # Arrange: Set up issue without erk-plan label
    plan_content = "# Test Plan\n\nThis is a test plan."
    issue = IssueInfo(
        number=100,
        title="Issue Without Label",
        body=plan_content,
        state="OPEN",
        url="https://github.com/owner/repo/issues/100",
        labels=["bug"],  # Different label, not erk-plan
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    fake_github = FakeGitHubIssues(issues={100: issue})

    # Create context
    ctx = DotAgentContext.for_test(
        github_issues=fake_github,
        repo_root=tmp_path,
        cwd=tmp_path,
    )

    # Act: Run command
    runner = CliRunner()
    result = runner.invoke(
        create_erp_from_issue,
        ["100", "Issue Without Label"],
        obj=ctx,
    )

    # Assert: Command failed with exit code 1
    assert result.exit_code == 1

    # Assert: Error output is valid JSON with error details
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "missing_erk_plan_label"
    assert "does not have 'erk-plan' label" in output["message"]

    # Assert: .erp/ folder was NOT created
    erp_path = tmp_path / ".erp"
    assert not erp_path.exists()
