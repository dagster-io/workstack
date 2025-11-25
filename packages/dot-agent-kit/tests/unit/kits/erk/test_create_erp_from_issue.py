"""Tests for create-erp-from-issue kit CLI command.

Layer 4 (Business Logic Tests): Tests command logic over fakes.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_erp_from_issue import (
    create_erp_from_issue,
)
from erk.core.plan_store.fake import FakePlanStore
from erk.core.plan_store.types import Plan, PlanState


def test_create_erp_from_issue_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful .erp/ folder creation from issue."""
    # Arrange: Set up fake plan store with test data
    plan_content = "# Test Plan\n\nThis is a test plan."
    plan = Plan(
        plan_identifier="1028",
        title="Test Issue Title",
        body=plan_content,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/1028",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    fake_plan_store = FakePlanStore(plans={"1028": plan})

    # Mock create_context to return context with fake plan store
    def mock_create_context(dry_run: bool, script: bool) -> object:
        # Return a minimal context object with just the plan_store
        class MockContext:
            def __init__(self) -> None:
                self.plan_store = fake_plan_store

        return MockContext()

    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_erp_from_issue.create_context",
        mock_create_context,
    )

    # Act: Run command
    runner = CliRunner()
    result = runner.invoke(
        create_erp_from_issue,
        ["1028", "Test Issue Title", "--repo-root", str(tmp_path)],
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


def test_create_erp_from_issue_plan_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test error handling when plan cannot be fetched."""
    # Arrange: Set up fake plan store with no plans
    fake_plan_store = FakePlanStore()

    # Mock create_context to return context with empty plan store
    def mock_create_context(dry_run: bool, script: bool) -> object:
        class MockContext:
            def __init__(self) -> None:
                self.plan_store = fake_plan_store

        return MockContext()

    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_erp_from_issue.create_context",
        mock_create_context,
    )

    # Act: Run command with non-existent issue
    runner = CliRunner()
    result = runner.invoke(
        create_erp_from_issue,
        ["999", "Non-existent Issue", "--repo-root", str(tmp_path)],
    )

    # Assert: Command failed with exit code 1
    assert result.exit_code == 1

    # Assert: Error output is valid JSON with error details
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "plan_not_found"
    assert "Could not fetch plan" in output["message"]

    # Assert: .erp/ folder was NOT created
    erp_path = tmp_path / ".erp"
    assert not erp_path.exists()


def test_create_erp_from_issue_uses_cwd_when_no_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test command defaults to current working directory when --repo-root not specified."""
    # Arrange: Set up fake plan store
    plan_content = "# Default CWD Test\n\nTesting default behavior."
    plan = Plan(
        plan_identifier="100",
        title="Default CWD Issue",
        body=plan_content,
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/issues/100",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    fake_plan_store = FakePlanStore(plans={"100": plan})

    # Mock create_context
    def mock_create_context(dry_run: bool, script: bool) -> object:
        class MockContext:
            def __init__(self) -> None:
                self.plan_store = fake_plan_store

        return MockContext()

    monkeypatch.setattr(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_erp_from_issue.create_context",
        mock_create_context,
    )

    # Mock Path.cwd() to return tmp_path
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    # Act: Run command WITHOUT --repo-root
    runner = CliRunner()
    result = runner.invoke(
        create_erp_from_issue,
        ["100", "Default CWD Issue"],
    )

    # Assert: Command succeeded
    assert result.exit_code == 0

    # Assert: .erp/ folder was created in cwd (tmp_path)
    erp_path = tmp_path / ".erp"
    assert erp_path.exists()
    assert (erp_path / "plan.md").exists()
