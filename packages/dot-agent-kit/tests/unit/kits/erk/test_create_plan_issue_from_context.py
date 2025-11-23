"""Unit tests for create-plan-issue-from-context command."""

import json

from click.testing import CliRunner

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.create_plan_issue_from_context import (
    create_plan_issue_from_context,
)
from tests.fakes.fake_github_cli import FakeDotAgentGitHubCli


def test_create_plan_issue_success() -> None:
    """Test successful issue creation from plan."""
    fake_gh = FakeDotAgentGitHubCli()
    runner = CliRunner()

    plan = "# My Feature\n\n- Step 1\n- Step 2"

    result = runner.invoke(
        create_plan_issue_from_context,
        input=plan,
        obj=DotAgentContext.for_test(github_cli=fake_gh),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert "github.com/owner/repo/issues/1" in output["issue_url"]

    # Verify behavior through fake
    issue = fake_gh.get_issue(1)
    assert issue is not None
    assert issue.title == "My Feature"
    assert "erk-plan" in issue.labels
    assert "Step 1" in issue.body


def test_create_plan_issue_empty_plan() -> None:
    """Test error handling for empty plan."""
    fake_gh = FakeDotAgentGitHubCli()
    runner = CliRunner()

    result = runner.invoke(
        create_plan_issue_from_context,
        input="",
        obj=DotAgentContext.for_test(github_cli=fake_gh),
    )

    assert result.exit_code == 1
    assert "Error: Empty plan content" in result.output


def test_create_plan_issue_unicode() -> None:
    """Test issue creation with unicode content."""
    fake_gh = FakeDotAgentGitHubCli()
    runner = CliRunner()

    plan = "# café Feature 你好\n\n- Unicode test"

    result = runner.invoke(
        create_plan_issue_from_context,
        input=plan,
        obj=DotAgentContext.for_test(github_cli=fake_gh),
    )

    assert result.exit_code == 0
    issue = fake_gh.get_issue(1)
    # Title will have unicode characters stripped by generate_filename_from_title
    # but issue title extraction keeps original characters up to markdown cleanup
    assert issue is not None


def test_create_plan_issue_ensures_label() -> None:
    """Test that command ensures erk-plan label exists."""
    fake_gh = FakeDotAgentGitHubCli()
    runner = CliRunner()

    plan = "# Test Plan\n\n- Step"

    result = runner.invoke(
        create_plan_issue_from_context,
        input=plan,
        obj=DotAgentContext.for_test(github_cli=fake_gh),
    )

    assert result.exit_code == 0
    assert "erk-plan" in fake_gh.labels


def test_create_plan_issue_h2_title() -> None:
    """Test title extraction falls back to H2."""
    fake_gh = FakeDotAgentGitHubCli()
    runner = CliRunner()

    plan = "## Secondary Title\n\n- Step"

    result = runner.invoke(
        create_plan_issue_from_context,
        input=plan,
        obj=DotAgentContext.for_test(github_cli=fake_gh),
    )

    assert result.exit_code == 0
    issue = fake_gh.get_issue(1)
    assert issue is not None
    assert issue.title == "Secondary Title"


def test_create_plan_issue_preserves_body() -> None:
    """Test that full plan content is preserved in issue body."""
    fake_gh = FakeDotAgentGitHubCli()
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
        create_plan_issue_from_context,
        input=plan,
        obj=DotAgentContext.for_test(github_cli=fake_gh),
    )

    assert result.exit_code == 0
    issue = fake_gh.get_issue(1)
    assert issue is not None
    assert "## Context" in issue.body
    assert "## Steps" in issue.body
    assert "## Testing" in issue.body
    assert "First step" in issue.body
