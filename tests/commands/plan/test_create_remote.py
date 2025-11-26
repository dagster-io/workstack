"""Tests for plan create-remote command."""

from click.testing import CliRunner
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.metadata import find_metadata_block

from erk.cli.cli import cli
from erk.core.github.fake import FakeGitHub
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env


def test_create_remote_creates_placeholder_issue(tmp_path) -> None:
    """Test that create-remote creates a placeholder issue before triggering workflow."""
    # Arrange
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Add feature X with behavior Y", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        github = FakeGitHub()
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "create-remote", str(prompt_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Creating placeholder issue" in result.output
        assert "Issue #1" in result.output or "Created" in result.output

        # Verify placeholder issue was created
        assert len(issues.created_issues) == 1
        title, body, labels = issues.created_issues[0]
        assert "erk-plan" in labels

        # Verify Schema V2 format: metadata in body
        assert "plan-header" in body

        # Verify placeholder comment was added
        assert len(issues.added_comments) == 1
        comment_number, comment_body = issues.added_comments[0]
        assert comment_number == 1
        assert "Pending" in comment_body or "pending" in comment_body.lower()


def test_create_remote_triggers_workflow(tmp_path) -> None:
    """Test that create-remote triggers the plan-create workflow."""
    # Arrange
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Add feature X", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        github = FakeGitHub()
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "create-remote", str(prompt_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "workflow triggered" in result.output.lower()

        # Verify workflow was triggered
        assert len(github.triggered_workflows) == 1
        workflow, inputs = github.triggered_workflows[0]
        assert workflow == "plan-create.yml"
        assert "prompt" in inputs
        assert "issue_number" in inputs
        assert inputs["issue_number"] == "1"


def test_create_remote_with_empty_prompt(tmp_path) -> None:
    """Test error when prompt file is empty."""
    # Arrange
    prompt_file = tmp_path / "empty.txt"
    prompt_file.write_text("", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        github = FakeGitHub()
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "create-remote", str(prompt_file)], obj=ctx)

        # Assert
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "empty" in result.output.lower()

        # No issue should be created
        assert len(issues.created_issues) == 0


def test_create_remote_with_explicit_title(tmp_path) -> None:
    """Test using explicit --title option."""
    # Arrange
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Some long prompt that doesn't make a good title", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        github = FakeGitHub()
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(
            cli,
            ["plan", "create-remote", "--title", "Custom Title", str(prompt_file)],
            obj=ctx,
        )

        # Assert
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify title was used
        title, body, labels = issues.created_issues[0]
        assert title == "Custom Title"


def test_create_remote_derives_title_from_prompt(tmp_path) -> None:
    """Test that title is derived from the first line of the prompt."""
    # Arrange
    prompt_file = tmp_path / "prompt.txt"
    prompt_content = "Add dark mode toggle to settings page\n\nDetails here..."
    prompt_file.write_text(prompt_content, encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        github = FakeGitHub()
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "create-remote", str(prompt_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify title was derived (prefix "Add" is stripped)
        title, body, labels = issues.created_issues[0]
        assert "dark mode" in title.lower()


def test_create_remote_with_nonexistent_file() -> None:
    """Test error when prompt file doesn't exist."""
    # Arrange
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        github = FakeGitHub()
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "create-remote", "/nonexistent/prompt.txt"], obj=ctx)

        # Assert
        # Click's Path(exists=True) validation causes exit code 2 (usage error)
        assert result.exit_code == 2
        assert "Error" in result.output or "does not exist" in result.output.lower()


def test_create_remote_shows_next_steps(tmp_path) -> None:
    """Test that output shows helpful next steps."""
    # Arrange
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Add feature", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        github = FakeGitHub()
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "create-remote", str(prompt_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0
        assert "Next steps" in result.output
        assert "Track issue" in result.output or "issue" in result.output.lower()
        assert "workflow" in result.output.lower()


def test_create_remote_uses_schema_v2(tmp_path) -> None:
    """Test that created issue uses Schema V2 format."""
    # Arrange
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Test feature", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues()
        github = FakeGitHub()
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "create-remote", str(prompt_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify Schema V2 structure
        title, body, labels = issues.created_issues[0]

        # Issue body should contain plan-header metadata block
        header_block = find_metadata_block(body, "plan-header")
        assert header_block is not None
        assert header_block.data["schema_version"] == "2"
        assert "worktree_name" in header_block.data
        assert "created_at" in header_block.data
        assert "created_by" in header_block.data


def test_create_remote_ensures_label_exists(tmp_path) -> None:
    """Test that erk-plan label is created if it doesn't exist."""
    # Arrange
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("Test feature", encoding="utf-8")

    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        issues = FakeGitHubIssues(labels=set())  # No labels exist initially
        github = FakeGitHub()
        ctx = build_workspace_test_context(env, issues=issues, github=github)

        # Act
        result = runner.invoke(cli, ["plan", "create-remote", str(prompt_file)], obj=ctx)

        # Assert
        assert result.exit_code == 0

        # Verify label was created
        assert len(issues.created_labels) == 1
        label, description, color = issues.created_labels[0]
        assert label == "erk-plan"
        assert "Implementation plan tracked by erk" in description
