"""Unit tests for post_pr_comment kit CLI command.

Tests posting PR link comments to GitHub issues after PR publication.
Uses FakeGitHubIssues for fast, reliable testing without subprocess mocking.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.impl_folder import save_issue_reference

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_pr_comment import (
    create_pr_published_block,
    get_branch_name,
    post_pr_comment,
)


def make_issue_info(number: int) -> IssueInfo:
    """Create test IssueInfo with given number."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test Issue #{number}",
        body="Test issue body",
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
    )


# ============================================================================
# Helper Functions
# ============================================================================


def create_issue_json(impl_dir: Path, issue_number: int) -> None:
    """Create a valid .impl/issue.json file."""
    impl_dir.mkdir(parents=True, exist_ok=True)
    save_issue_reference(
        impl_dir=impl_dir,
        issue_number=issue_number,
        issue_url=f"https://github.com/test-owner/test-repo/issues/{issue_number}",
    )


# ============================================================================
# Pure Unit Tests (Layer 3) - No Dependencies
# ============================================================================


def test_create_pr_published_block_structure() -> None:
    """Test that create_pr_published_block creates correct metadata block."""
    block = create_pr_published_block(
        pr_number=123,
        pr_url="https://github.com/org/repo/pull/123",
        branch_name="feature-branch",
        timestamp="2025-11-25T12:00:00+00:00",
    )

    assert block.key == "erk-pr-published"
    assert block.data["status"] == "pr_published"
    assert block.data["pr_number"] == 123
    assert block.data["pr_url"] == "https://github.com/org/repo/pull/123"
    assert block.data["branch_name"] == "feature-branch"
    assert block.data["timestamp"] == "2025-11-25T12:00:00+00:00"


def test_get_branch_name_success() -> None:
    """Test get_branch_name returns branch when git succeeds."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "my-feature-branch\n"
        mock_run.return_value.returncode = 0

        result = get_branch_name()

        assert result == "my-feature-branch"
        mock_run.assert_called_once()


def test_get_branch_name_empty_output() -> None:
    """Test get_branch_name returns None when git returns empty string."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "\n"
        mock_run.return_value.returncode = 0

        result = get_branch_name()

        assert result is None


def test_get_branch_name_failure() -> None:
    """Test get_branch_name returns None when git command fails."""
    import subprocess

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        result = get_branch_name()

        assert result is None


# ============================================================================
# Business Logic Tests (Layer 4) - Over Fakes
# ============================================================================


def test_post_pr_comment_success(tmp_path: Path) -> None:
    """Test successful PR comment posting."""
    # Arrange - pre-populate fake with issue
    fake_gh = FakeGitHubIssues(issues={456: make_issue_info(456)})
    runner = CliRunner()

    # Act
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create .impl folder in isolated filesystem
        create_issue_json(Path.cwd() / ".impl", issue_number=456)

        with patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_pr_comment.get_branch_name"
        ) as mock_branch:
            mock_branch.return_value = "feature/test-branch"

            result = runner.invoke(
                post_pr_comment,
                ["--pr-url", "https://github.com/org/repo/pull/123", "--pr-number", "123"],
                obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
            )

    # Assert
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 456
    assert output["pr_number"] == 123

    # Verify comment was posted using added_comments property
    assert len(fake_gh.added_comments) == 1
    issue_number, comment_body = fake_gh.added_comments[0]
    assert issue_number == 456
    assert "PR Published" in comment_body
    assert "#123" in comment_body
    assert "https://github.com/org/repo/pull/123" in comment_body


def test_post_pr_comment_no_issue_reference(tmp_path: Path) -> None:
    """Test error when no .impl/issue.json exists."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Don't create .impl/issue.json

        result = runner.invoke(
            post_pr_comment,
            ["--pr-url", "https://github.com/org/repo/pull/123", "--pr-number", "123"],
            obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
        )

    assert result.exit_code == 0  # Always exits 0 for || true pattern
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "no_issue_reference"
    assert ".impl/issue.json" in output["message"]


def test_post_pr_comment_invalid_issue_json(tmp_path: Path) -> None:
    """Test error when .impl/issue.json contains invalid JSON."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create invalid issue.json
        impl_dir = Path.cwd() / ".impl"
        impl_dir.mkdir(parents=True)
        (impl_dir / "issue.json").write_text("not valid json", encoding="utf-8")

        result = runner.invoke(
            post_pr_comment,
            ["--pr-url", "https://github.com/org/repo/pull/123", "--pr-number", "123"],
            obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "invalid_issue_reference"


def test_post_pr_comment_branch_detection_failed(tmp_path: Path) -> None:
    """Test error when git branch detection fails."""
    fake_gh = FakeGitHubIssues(issues={456: make_issue_info(456)})
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_issue_json(Path.cwd() / ".impl", issue_number=456)

        with patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_pr_comment.get_branch_name"
        ) as mock_branch:
            mock_branch.return_value = None  # Branch detection failed

            result = runner.invoke(
                post_pr_comment,
                ["--pr-url", "https://github.com/org/repo/pull/123", "--pr-number", "123"],
                obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
            )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "branch_detection_failed"


def test_post_pr_comment_github_api_failure(tmp_path: Path) -> None:
    """Test error when GitHub API fails during comment posting."""

    class FailingFakeGitHubIssues(FakeGitHubIssues):
        def add_comment(self, repo_root: Path, number: int, body: str) -> None:
            raise RuntimeError("Network error")

    fake_gh = FailingFakeGitHubIssues(issues={456: make_issue_info(456)})
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_issue_json(Path.cwd() / ".impl", issue_number=456)

        with patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_pr_comment.get_branch_name"
        ) as mock_branch:
            mock_branch.return_value = "feature/test-branch"

            result = runner.invoke(
                post_pr_comment,
                ["--pr-url", "https://github.com/org/repo/pull/123", "--pr-number", "123"],
                obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
            )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "github_api_failed"
    assert "Network error" in output["message"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success(tmp_path: Path) -> None:
    """Test JSON output structure on success."""
    fake_gh = FakeGitHubIssues(issues={789: make_issue_info(789)})
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_issue_json(Path.cwd() / ".impl", issue_number=789)

        with patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_pr_comment.get_branch_name"
        ) as mock_branch:
            mock_branch.return_value = "feature/test-branch"

            result = runner.invoke(
                post_pr_comment,
                ["--pr-url", "https://github.com/org/repo/pull/456", "--pr-number", "456"],
                obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
            )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output
    assert "pr_number" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["pr_number"], int)

    # Verify values
    assert output["success"] is True
    assert output["issue_number"] == 789
    assert output["pr_number"] == 456


def test_json_output_structure_error(tmp_path: Path) -> None:
    """Test JSON output structure on error."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # No .impl/issue.json - will cause error

        result = runner.invoke(
            post_pr_comment,
            ["--pr-url", "https://github.com/org/repo/pull/123", "--pr-number", "123"],
            obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error_type" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error_type"], str)
    assert isinstance(output["message"], str)

    # Verify values
    assert output["success"] is False


# ============================================================================
# Comment Content Tests
# ============================================================================


def test_comment_contains_pr_metadata(tmp_path: Path) -> None:
    """Test that posted comment contains expected PR metadata."""
    fake_gh = FakeGitHubIssues(issues={100: make_issue_info(100)})
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        create_issue_json(Path.cwd() / ".impl", issue_number=100)

        with patch(
            "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.post_pr_comment.get_branch_name"
        ) as mock_branch:
            mock_branch.return_value = "feature/awesome-feature"

            result = runner.invoke(
                post_pr_comment,
                [
                    "--pr-url",
                    "https://github.com/myorg/myrepo/pull/999",
                    "--pr-number",
                    "999",
                ],
                obj=DotAgentContext.for_test(github_issues=fake_gh, repo_root=tmp_path),
            )

    assert result.exit_code == 0

    # Verify comment content using added_comments property
    assert len(fake_gh.added_comments) == 1
    issue_number, comment_body = fake_gh.added_comments[0]
    assert issue_number == 100

    # Should contain PR link
    assert "https://github.com/myorg/myrepo/pull/999" in comment_body
    assert "#999" in comment_body

    # Should contain metadata block
    assert "erk-pr-published" in comment_body
    assert "pr_published" in comment_body
    assert "feature/awesome-feature" in comment_body

    # Should contain title
    assert "PR Published" in comment_body
