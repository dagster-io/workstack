"""Unit tests for create-enriched-plan-from-context command.

Schema Version 2 format:
- Issue body contains only metadata (plan-header block)
- First comment contains plan content wrapped in markers
"""

import json
from pathlib import Path

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_enriched_plan_from_context import (
    create_enriched_plan_from_context,
)


def test_create_enriched_plan_issue_success() -> None:
    """Test successful issue creation from enriched plan with --plan-file.

    Schema v2: Issue body has metadata, first comment has plan content.
    """
    # FakeGitHubIssues default username is "testuser"
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

    assert result.exit_code == 0, f"Failed with output: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert "github.com/test-owner/test-repo/issues/1" in output["issue_url"]

    # Verify issue created with metadata body (schema v2)
    assert len(fake_gh.created_issues) == 1
    title, body, labels = fake_gh.created_issues[0]
    assert title == "My Feature"
    assert labels == ["erk-plan"]
    # Body contains plan-header metadata block
    assert "plan-header" in body
    assert "schema_version: '2'" in body
    assert "created_by: testuser" in body
    assert "worktree_name: my-feature" in body

    # Verify first comment has plan content (schema v2)
    assert len(fake_gh.added_comments) == 1
    issue_num, comment_body = fake_gh.added_comments[0]
    assert issue_num == 1
    assert "<!-- erk:plan-content -->" in comment_body
    assert "Step 1" in comment_body
    assert "Step 2" in comment_body


def test_create_enriched_plan_issue_multiline() -> None:
    """Test --plan-file option with multi-line content.

    Schema v2: Plan content preserved in first comment with markers.
    """
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

    assert result.exit_code == 0, f"Failed with output: {result.output}"

    # Verify issue created
    assert len(fake_gh.created_issues) == 1

    # Verify plan content in first comment (newlines preserved)
    assert len(fake_gh.added_comments) == 1
    _issue_num, comment_body = fake_gh.added_comments[0]
    assert "## Context" in comment_body
    assert "## Steps" in comment_body
    assert "## Testing" in comment_body
    assert "First step" in comment_body


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


def test_create_enriched_plan_issue_has_label() -> None:
    """Test that command creates and applies erk-plan label (required for erk submit)."""
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

    # Verify label was created (ensure_label_exists called)
    assert len(fake_gh.created_labels) == 1
    label_name, label_desc, label_color = fake_gh.created_labels[0]
    assert label_name == "erk-plan"
    assert label_desc == "Implementation plan for manual execution"
    assert label_color == "0E8A16"

    # Verify issue was created with erk-plan label
    assert len(fake_gh.created_issues) == 1
    _title, _body, labels = fake_gh.created_issues[0]
    assert labels == ["erk-plan"]


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
    """Test --plan-file with YAML frontmatter preserved.

    Schema v2: Plan content goes in first comment, body has metadata only.
    """
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

    # Verify issue created with correct title
    assert len(fake_gh.created_issues) == 1
    title, _body, _labels = fake_gh.created_issues[0]
    assert title == "Feature Plan"

    # Verify plan content in first comment (schema v2)
    assert len(fake_gh.added_comments) == 1
    _issue_num, comment_body = fake_gh.added_comments[0]
    assert "- Step 1" in comment_body


def test_create_enriched_plan_schema_v2_format() -> None:
    """Verify created issues follow schema v2 format.

    Schema v2: Issue body has metadata block only, plan content in first comment.
    """
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

    # Verify issue was created with metadata body (schema v2)
    assert len(fake_gh.created_issues) == 1
    _title, body, _labels = fake_gh.created_issues[0]

    # Body contains plan-header metadata block (schema v2)
    assert "plan-header" in body
    assert "schema_version: '2'" in body
    # Body does NOT contain the plan content (that's in the comment now)
    assert "Step 1" not in body
    assert "Step 2" not in body

    # Verify plan content in first comment with markers (schema v2)
    assert len(fake_gh.added_comments) == 1
    _issue_num, comment_body = fake_gh.added_comments[0]
    assert "<!-- erk:plan-content -->" in comment_body
    assert "Step 1" in comment_body
    assert "Step 2" in comment_body
    assert "<!-- /erk:plan-content -->" in comment_body
