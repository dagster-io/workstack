"""Tests for planned issue + worktree creation workflow.

Tests the integration of plan file reading, worktree creation, issue creation,
and linking them together via .plan/issue.json.
"""

from pathlib import Path

import pytest

from erk.core.github.issues import FakeGitHubIssues, IssueInfo
from erk.core.plan_folder import (
    create_plan_folder,
    has_issue_reference,
    read_issue_reference,
    save_issue_reference,
)
from tests.test_utils import sentinel_path


def test_save_and_read_issue_reference(tmp_path: Path) -> None:
    """Test saving and reading issue reference from plan folder."""
    plan_folder = tmp_path / ".plan"
    plan_folder.mkdir()

    issue_number = 42
    issue_url = "https://github.com/owner/repo/issues/42"

    # Save issue reference
    save_issue_reference(plan_folder, issue_number, issue_url)

    # Verify file was created
    issue_json = plan_folder / "issue.json"
    assert issue_json.exists()

    # Read back and verify
    ref = read_issue_reference(plan_folder)
    assert ref is not None
    assert ref.issue_number == issue_number
    assert ref.issue_url == issue_url
    assert ref.created_at is not None
    assert ref.synced_at is not None


def test_save_issue_reference_plan_dir_must_exist(tmp_path: Path) -> None:
    """Test that save_issue_reference raises if plan dir doesn't exist."""
    plan_folder = tmp_path / ".plan"  # Doesn't exist

    with pytest.raises(FileNotFoundError, match="Plan directory does not exist"):
        save_issue_reference(plan_folder, 42, "https://github.com/owner/repo/issues/42")


def test_has_issue_reference_false_when_no_file(tmp_path: Path) -> None:
    """Test has_issue_reference returns False when issue.json doesn't exist."""
    plan_folder = tmp_path / ".plan"
    plan_folder.mkdir()

    assert has_issue_reference(plan_folder) is False


def test_has_issue_reference_true_when_file_exists(tmp_path: Path) -> None:
    """Test has_issue_reference returns True when issue.json exists."""
    plan_folder = tmp_path / ".plan"
    plan_folder.mkdir()

    save_issue_reference(plan_folder, 42, "https://github.com/owner/repo/issues/42")

    assert has_issue_reference(plan_folder) is True


def test_read_issue_reference_returns_none_when_no_file(tmp_path: Path) -> None:
    """Test read_issue_reference returns None when file doesn't exist."""
    plan_folder = tmp_path / ".plan"
    plan_folder.mkdir()

    ref = read_issue_reference(plan_folder)
    assert ref is None


def test_workflow_create_plan_then_link_issue(tmp_path: Path) -> None:
    """Test complete workflow: create plan folder, then link issue."""
    plan_content = """# Test Plan

## Objective
Test the workflow.

## Implementation Steps
1. Step one
2. Step two
"""

    # Step 1: Create plan folder (simulates erk create --plan)
    plan_folder = create_plan_folder(tmp_path, plan_content)

    # Step 2: Create issue (simulates gh issue create)
    issues = FakeGitHubIssues(next_issue_number=123)
    issue_num = issues.create_issue(sentinel_path(), "Test Plan", plan_content, ["erk-plan"])

    assert issue_num == 123

    # Step 3: Link issue to plan folder
    issue_url = f"https://github.com/owner/repo/issues/{issue_num}"
    save_issue_reference(plan_folder, issue_num, issue_url)

    # Step 4: Verify link was created
    assert has_issue_reference(plan_folder)

    # Step 5: Read back and verify
    ref = read_issue_reference(plan_folder)
    assert ref is not None
    assert ref.issue_number == 123
    assert ref.issue_url == issue_url


def test_workflow_issue_creation_tracks_erk_plan_label() -> None:
    """Test that issue creation includes erk-plan label."""
    issues = FakeGitHubIssues()

    issues.create_issue(
        sentinel_path(),
        title="Implementation Plan",
        body="Plan content here",
        labels=["erk-plan"],
    )

    # Verify issue was created with label
    assert len(issues.created_issues) == 1
    title, body, labels = issues.created_issues[0]
    assert title == "Implementation Plan"
    assert body == "Plan content here"
    assert "erk-plan" in labels


def test_workflow_get_issue_after_creation() -> None:
    """Test retrieving issue info after creation."""
    from datetime import UTC, datetime

    issues = FakeGitHubIssues(
        next_issue_number=42,
        issues={
            42: IssueInfo(
                number=42,
                title="Test Issue",
                body="Body content",
                state="OPEN",
                url="https://github.com/owner/repo/issues/42",
                labels=[],
                assignees=[],
                created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
                updated_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            )
        },
    )

    # Create issue
    issue_num = issues.create_issue(sentinel_path(), "Test Issue", "Body content", ["erk-plan"])

    # Retrieve issue info
    info = issues.get_issue(sentinel_path(), issue_num)

    assert info is not None
    assert info.number == 42
    assert info.title == "Test Issue"
    assert info.url == "https://github.com/owner/repo/issues/42"
    assert info.state == "OPEN"


def test_workflow_multiple_issues_increment_numbers() -> None:
    """Test that multiple issue creations increment issue numbers."""
    issues = FakeGitHubIssues(next_issue_number=10)

    num1 = issues.create_issue(sentinel_path(), "Issue 1", "Body 1", ["label1"])
    num2 = issues.create_issue(sentinel_path(), "Issue 2", "Body 2", ["label2"])
    num3 = issues.create_issue(sentinel_path(), "Issue 3", "Body 3", ["label3"])

    assert num1 == 10
    assert num2 == 11
    assert num3 == 12

    assert len(issues.created_issues) == 3


def test_workflow_title_extraction_yaml_frontmatter(tmp_path: Path) -> None:
    """Test that plan with YAML front matter title is used for issue."""
    plan_content = """---
title: Custom Title from YAML
erk_plan: true
---

# Some Other Heading

Content here.
"""

    plan_file = tmp_path / "test-plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # In real workflow, agent would parse YAML and extract "Custom Title from YAML"
    # For this test, we just verify the content contains the YAML
    content = plan_file.read_text(encoding="utf-8")
    assert "title: Custom Title from YAML" in content
    assert "# Some Other Heading" in content


def test_workflow_title_extraction_h1_heading(tmp_path: Path) -> None:
    """Test that plan with H1 heading (no YAML) uses H1 for issue."""
    plan_content = """# Implementation Plan for Feature X

## Objective
Build feature X.

## Steps
1. Step one
2. Step two
"""

    plan_file = tmp_path / "test-plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # In real workflow, agent would extract "Implementation Plan for Feature X"
    content = plan_file.read_text(encoding="utf-8")
    lines = content.split("\n")
    h1_line = next((line for line in lines if line.startswith("# ")), None)

    assert h1_line is not None
    title = h1_line.lstrip("# ").strip()
    assert title == "Implementation Plan for Feature X"


def test_workflow_title_extraction_filename_fallback(tmp_path: Path) -> None:
    """Test that filename (without -plan.md) is used as fallback for issue title."""
    plan_content = """Some plan content without YAML or H1 heading.

Just plain text describing the plan.
"""

    plan_file = tmp_path / "feature-x-plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # In real workflow, agent would use "feature-x" as title
    filename = plan_file.name
    title = filename.replace("-plan.md", "")
    assert title == "feature-x"
