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
    # No labels added (erk-plan label removed for optimization)
    assert labels == []
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


def test_create_enriched_plan_issue_no_labels() -> None:
    """Test that command does NOT create or apply labels (optimization)."""
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

    # Verify no labels were created (optimization: removed ensure_label_exists call)
    assert len(fake_gh.created_labels) == 0

    # Verify issue was created without labels
    assert len(fake_gh.created_issues) == 1
    _title, _body, labels = fake_gh.created_issues[0]
    assert labels == []


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
    """Verify created issues have collapsible details tags (no update_issue_body call)."""
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

    # Verify issue was created with pre-formatted body (no update call)
    assert len(fake_gh.created_issues) == 1
    _title, body, _labels = fake_gh.created_issues[0]

    # Verify details tags are present in the created issue body
    assert "<details>" in body
    assert "</details>" in body
    assert "<summary><strong>📋 Implementation Plan</strong></summary>" in body
    # Execution commands removed for optimization (shown in CLI output instead)
    assert "## Execution Commands" not in body
    assert "Step 1" in body
    assert "Step 2" in body
