"""Unit tests for create-enriched-plan-issue-from-context command."""

import json

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues

from dot_agent_kit.context import DotAgentContext
from erk.data.kits.erk.kit_cli_commands.erk.create_enriched_plan_issue_from_context import (
    create_enriched_plan_issue_from_context,
)


def test_create_enriched_plan_issue_success() -> None:
    """Test successful issue creation from enriched plan with --plan-content."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# My Feature\n\n- Step 1\n- Step 2"

    result = runner.invoke(
        create_enriched_plan_issue_from_context,
        ["--plan-content", plan],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert "github.com/owner/repo/issues/1" in output["issue_url"]

    # Verify behavior through fake's mutation tracking
    assert len(fake_gh.created_issues) == 1
    title, body, labels = fake_gh.created_issues[0]
    assert title == "My Feature"
    assert "erk-plan" in labels
    assert "Step 1" in body


def test_create_enriched_plan_issue_multiline() -> None:
    """Test --plan-content option with multi-line content."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = """# Feature Plan

## Context

Background information

## Steps

1. First step
2. Second step

## Testing

Test instructions
"""

    result = runner.invoke(
        create_enriched_plan_issue_from_context,
        ["--plan-content", plan],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    # Verify newlines preserved correctly
    assert len(fake_gh.created_issues) == 1
    _title, body, _labels = fake_gh.created_issues[0]
    assert "## Context" in body
    assert "## Steps" in body
    assert "## Testing" in body
    assert "First step" in body


def test_create_enriched_plan_issue_empty_plan() -> None:
    """Test error when --plan-content is empty."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_enriched_plan_issue_from_context,
        ["--plan-content", ""],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 1
    assert "Error: Empty plan content" in result.output


def test_create_enriched_plan_issue_missing_option() -> None:
    """Test error when --plan-content not provided."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_enriched_plan_issue_from_context,
        [],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code != 0
    # Click should mention the missing required option
    assert "--plan-content" in result.output or "plan-content" in result.output


def test_create_enriched_plan_issue_ensures_label() -> None:
    """Test that command ensures erk-plan label exists."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# Test Plan\n\n- Step"

    result = runner.invoke(
        create_enriched_plan_issue_from_context,
        ["--plan-content", plan],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    # Verify label was created
    assert len(fake_gh.created_labels) == 1
    label, description, color = fake_gh.created_labels[0]
    assert label == "erk-plan"
    assert description == "Implementation plan for manual execution"
    assert color == "0E8A16"


def test_create_enriched_plan_issue_unicode() -> None:
    """Test issue creation with unicode content."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# café Feature 你好\n\n- Unicode test"

    result = runner.invoke(
        create_enriched_plan_issue_from_context,
        ["--plan-content", plan],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    # Verify issue was created (title will have unicode characters)
    assert len(fake_gh.created_issues) == 1


def test_create_enriched_plan_issue_yaml_frontmatter() -> None:
    """Test --plan-content with YAML frontmatter preserved."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = """---
erk_plan: true
---

# Feature Plan

- Step 1
"""

    result = runner.invoke(
        create_enriched_plan_issue_from_context,
        ["--plan-content", plan],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code == 0
    # Verify YAML frontmatter extracted properly
    assert len(fake_gh.created_issues) == 1
    title, body, _labels = fake_gh.created_issues[0]
    assert title == "Feature Plan"
    # Body should contain frontmatter
    assert "erk_plan: true" in body
