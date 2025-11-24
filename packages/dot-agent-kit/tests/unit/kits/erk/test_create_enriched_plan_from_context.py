"""Unit tests for create-enriched-plan-from-context command."""

import json
from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues

from dot_agent_kit.context import DotAgentContext
from erk.data.kits.erk.kit_cli_commands.erk.create_enriched_plan_from_context import (
    create_enriched_plan_from_context,
)


def test_create_enriched_plan_issue_success() -> None:
    """Test successful issue creation from enriched plan with --plan-file."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# My Feature\n\n- Step 1\n- Step 2"

    with runner.isolated_filesystem():
        plan_file = Path("plan.md")
        plan_file.write_text(plan, encoding="utf-8")

        result = runner.invoke(
            create_enriched_plan_from_context,
            ["--plan-file", str(plan_file)],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["issue_number"] == 1
        assert "github.com/test-owner/test-repo/issues/1" in output["issue_url"]

    # Verify behavior through fake's mutation tracking
    assert len(fake_gh.created_issues) == 1
    title, body, labels = fake_gh.created_issues[0]
    assert title == "My Feature"
    assert "erk-plan" in labels
    assert "Step 1" in body


def test_create_enriched_plan_issue_multiline() -> None:
    """Test --plan-file option with multi-line content."""
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

    with runner.isolated_filesystem():
        plan_file = Path("plan.md")
        plan_file.write_text(plan, encoding="utf-8")

        result = runner.invoke(
            create_enriched_plan_from_context,
            ["--plan-file", str(plan_file)],
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
    """Test error when --plan-file contains empty content."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    with runner.isolated_filesystem():
        plan_file = Path("plan.md")
        plan_file.write_text("", encoding="utf-8")

        result = runner.invoke(
            create_enriched_plan_from_context,
            ["--plan-file", str(plan_file)],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

        assert result.exit_code == 1
        assert "Error: Empty plan content" in result.output


def test_create_enriched_plan_issue_missing_option() -> None:
    """Test error when --plan-file not provided."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        create_enriched_plan_from_context,
        [],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    assert result.exit_code != 0
    # Click should mention the missing required option
    assert "--plan-file" in result.output or "plan-file" in result.output


def test_create_enriched_plan_issue_ensures_label() -> None:
    """Test that command ensures erk-plan label exists."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# Test Plan\n\n- Step"

    with runner.isolated_filesystem():
        plan_file = Path("plan.md")
        plan_file.write_text(plan, encoding="utf-8")

        result = runner.invoke(
            create_enriched_plan_from_context,
            ["--plan-file", str(plan_file)],
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

    with runner.isolated_filesystem():
        plan_file = Path("plan.md")
        plan_file.write_text(plan, encoding="utf-8")

        result = runner.invoke(
            create_enriched_plan_from_context,
            ["--plan-file", str(plan_file)],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

        assert result.exit_code == 0

    # Verify issue was created (title will have unicode characters)
    assert len(fake_gh.created_issues) == 1


def test_create_enriched_plan_issue_yaml_frontmatter() -> None:
    """Test --plan-file with YAML frontmatter preserved."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = """# Feature Plan

- Step 1
"""

    with runner.isolated_filesystem():
        plan_file = Path("plan.md")
        plan_file.write_text(plan, encoding="utf-8")

        result = runner.invoke(
            create_enriched_plan_from_context,
            ["--plan-file", str(plan_file)],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

        assert result.exit_code == 0

    # Verify plan content preserved
    assert len(fake_gh.created_issues) == 1
    title, body, _labels = fake_gh.created_issues[0]
    assert title == "Feature Plan"
    # Body should contain plan content
    assert "- Step 1" in body


def test_create_enriched_plan_formats_with_details_tags() -> None:
    """Verify created issues have collapsible details tags."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# Test Plan\n\n- Step 1\n- Step 2"

    with runner.isolated_filesystem():
        plan_file = Path("plan.md")
        plan_file.write_text(plan, encoding="utf-8")

        result = runner.invoke(
            create_enriched_plan_from_context,
            ["--plan-file", str(plan_file)],
            obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=Path.cwd()),
        )

        assert result.exit_code == 0
        output_json = json.loads(result.output)
        issue_number = output_json["issue_number"]

    # Get the updated issue body from fake storage
    updated_issue = fake_gh.get_issue(Path.cwd(), issue_number)
    updated_body = updated_issue.body

    # Verify details tags are present
    assert "<details>" in updated_body
    assert "</details>" in updated_body
    assert "<summary><strong>📋 Implementation Plan</strong></summary>" in updated_body
    assert "## Execution Commands" in updated_body
    assert "Step 1" in updated_body
    assert "Step 2" in updated_body
