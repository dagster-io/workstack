"""Unit tests for create_issue kit CLI command.

Tests GitHub issue creation with body from stdin and multiple label support.
Uses FakeGitHubIssues for fast, reliable testing without subprocess mocking.
"""

import json

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_issue import (
    create_issue,
)

# ============================================================================
# Success Cases
# ============================================================================


def test_create_issue_success() -> None:
    """Test successful issue creation with single label."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_issue,
        ["Test Issue", "--label", "erk-plan"],
        input="Test body content",
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert output["issue_url"] == "https://github.com/test-owner/test-repo/issues/1"

    # Verify behavior through fake's mutation tracking
    assert len(fake_gh.created_issues) == 1
    title, body, labels = fake_gh.created_issues[0]
    assert title == "Test Issue"
    assert body == "Test body content"
    assert labels == ["erk-plan"]


def test_create_issue_no_labels() -> None:
    """Test issue creation without labels."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_issue,
        ["Test Issue"],
        input="Body content",
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1

    # Verify behavior: issue created without labels
    assert len(fake_gh.created_issues) == 1
    _, _, labels = fake_gh.created_issues[0]
    assert labels == []


def test_create_issue_multiple_labels() -> None:
    """Test issue creation with multiple labels."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_issue,
        ["Test Issue", "--label", "erk-plan", "--label", "priority-high"],
        input="Body content",
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify behavior: issue created with both labels
    assert len(fake_gh.created_issues) == 1
    _, _, labels = fake_gh.created_issues[0]
    assert labels == ["erk-plan", "priority-high"]


# ============================================================================
# Content Handling Tests
# ============================================================================


def test_create_issue_unicode_content() -> None:
    """Test issue creation with Unicode characters in body."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()
    unicode_body = "Testing Unicode: 你好 🎉 café"

    result = runner.invoke(
        create_issue,
        ["Test Issue", "--label", "erk-plan"],
        input=unicode_body,
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify Unicode content preserved
    assert len(fake_gh.created_issues) == 1
    _, body, _ = fake_gh.created_issues[0]
    assert body == unicode_body


def test_create_issue_yaml_frontmatter() -> None:
    """Test issue creation preserves any YAML front matter in body."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()
    body_with_yaml = """---
priority: high
custom_field: value
---

# Implementation Plan

This is the plan content."""

    result = runner.invoke(
        create_issue,
        ["Test Issue", "--label", "erk-plan"],
        input=body_with_yaml,
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify YAML front matter preserved (any frontmatter, not specific to erk_plan)
    assert len(fake_gh.created_issues) == 1
    _, body, _ = fake_gh.created_issues[0]
    assert body == body_with_yaml


def test_create_issue_special_characters() -> None:
    """Test issue creation with special characters in body and title."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()
    special_title = 'Title with "quotes" and `backticks`'
    special_body = """Body with special chars:
- "double quotes"
- 'single quotes'
- `backticks`
- $variables"""

    result = runner.invoke(
        create_issue,
        [special_title, "--label", "erk-plan"],
        input=special_body,
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify special characters preserved
    assert len(fake_gh.created_issues) == 1
    title, body, _ = fake_gh.created_issues[0]
    assert title == special_title
    assert body == special_body


def test_create_issue_large_body() -> None:
    """Test issue creation with large body content (10,000+ chars)."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()
    large_body = "x" * 10000

    result = runner.invoke(
        create_issue,
        ["Test Issue", "--label", "erk-plan"],
        input=large_body,
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True

    # Verify large body preserved
    assert len(fake_gh.created_issues) == 1
    _, body, _ = fake_gh.created_issues[0]
    assert body == large_body
    assert len(body) == 10000


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_create_issue_gh_failure() -> None:
    """Test error handling when gh CLI fails.

    Note: FakeGitHubIssues can be configured to raise RuntimeError to simulate
    gh CLI failures (not installed, not authenticated, network error, etc.).
    """
    from pathlib import Path

    # Create a fake that simulates failure
    from erk_shared.github.issues import CreateIssueResult

    class FailingFakeGitHubIssues(FakeGitHubIssues):
        def create_issue(
            self, repo_root: Path, title: str, body: str, labels: list[str]
        ) -> CreateIssueResult:
            raise RuntimeError("gh: command not found")

    fake_gh = FailingFakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_issue,
        ["Test Issue", "--label", "erk-plan"],
        input="Body content",
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    assert "Error: Failed to create issue" in result.output


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure() -> None:
    """Test JSON output structure on success."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_issue,
        ["Test Issue", "--label", "erk-plan"],
        input="Body",
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output
    assert "issue_url" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["issue_url"], str)

    # Verify values
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert output["issue_url"] == "https://github.com/test-owner/test-repo/issues/1"


def test_json_output_different_issue_numbers() -> None:
    """Test that JSON output correctly reflects different issue numbers."""
    fake_gh = FakeGitHubIssues(next_issue_number=12345)
    runner = CliRunner()

    result = runner.invoke(
        create_issue,
        ["Test Issue"],
        input="Body",
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify URL parsing mapped correctly
    assert output["issue_number"] == 12345
    assert output["issue_url"] == "https://github.com/test-owner/test-repo/issues/12345"
