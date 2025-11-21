"""Tests for RealGitHubIssues with mocked subprocess execution.

These tests verify that RealGitHubIssues correctly calls gh CLI commands and handles
responses. We use a mock executor function instead of actual subprocess calls.
"""

import json
from pathlib import Path

import pytest

from erk.core.github.issues import RealGitHubIssues


def test_create_issue_success() -> None:
    """Test create_issue calls gh CLI with correct arguments."""
    created_commands = []

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        created_commands.append(cmd)
        if "issue" in cmd and "create" in cmd:
            return "42"
        return ""

    issues = RealGitHubIssues(execute_fn=mock_execute)
    issue_num = issues.create_issue(
        Path("/repo"),
        title="Test Issue",
        body="Test body content",
        labels=["plan", "erk"],
    )

    # Verify issue number returned
    assert issue_num == 42

    # Verify gh command structure
    assert len(created_commands) == 1
    cmd = created_commands[0]
    assert cmd[0] == "gh"
    assert cmd[1] == "issue"
    assert cmd[2] == "create"
    assert "--title" in cmd
    assert "Test Issue" in cmd
    assert "--body" in cmd
    assert "Test body content" in cmd
    assert "--label" in cmd
    assert "plan" in cmd
    assert "erk" in cmd
    assert "--json" in cmd
    assert "number" in cmd


def test_create_issue_multiple_labels() -> None:
    """Test create_issue includes all labels in command."""
    created_commands = []

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        created_commands.append(cmd)
        return "1"

    issues = RealGitHubIssues(execute_fn=mock_execute)
    issues.create_issue(
        Path("/repo"),
        title="Title",
        body="Body",
        labels=["label1", "label2", "label3"],
    )

    cmd = created_commands[0]
    # Each label should appear after --label
    assert cmd.count("--label") == 3
    assert "label1" in cmd
    assert "label2" in cmd
    assert "label3" in cmd


def test_create_issue_no_labels() -> None:
    """Test create_issue works with empty labels list."""
    created_commands = []

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        created_commands.append(cmd)
        return "1"

    issues = RealGitHubIssues(execute_fn=mock_execute)
    issues.create_issue(Path("/repo"), title="Title", body="Body", labels=[])

    cmd = created_commands[0]
    # No --label flags should be present
    assert "--label" not in cmd


def test_create_issue_command_failure() -> None:
    """Test create_issue raises RuntimeError on gh CLI failure."""

    def mock_execute_failure(cmd: list[str], cwd: Path) -> str:
        raise RuntimeError("gh command failed: not authenticated")

    issues = RealGitHubIssues(execute_fn=mock_execute_failure)

    with pytest.raises(RuntimeError, match="not authenticated"):
        issues.create_issue(Path("/repo"), "Title", "Body", ["label"])


def test_get_issue_success() -> None:
    """Test get_issue calls gh CLI and parses response."""
    issue_data = {
        "number": 42,
        "title": "Test Issue Title",
        "body": "Test issue body content",
        "state": "OPEN",
        "url": "https://github.com/owner/repo/issues/42",
    }

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        if "issue" in cmd and "view" in cmd and "42" in cmd:
            return json.dumps(issue_data)
        return "{}"

    issues = RealGitHubIssues(execute_fn=mock_execute)
    result = issues.get_issue(Path("/repo"), 42)

    assert result.number == 42
    assert result.title == "Test Issue Title"
    assert result.body == "Test issue body content"
    assert result.state == "OPEN"
    assert result.url == "https://github.com/owner/repo/issues/42"


def test_get_issue_command_structure() -> None:
    """Test get_issue constructs correct gh CLI command."""
    created_commands = []

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        created_commands.append(cmd)
        return json.dumps(
            {
                "number": 123,
                "title": "Title",
                "body": "Body",
                "state": "OPEN",
                "url": "http://url",
            }
        )

    issues = RealGitHubIssues(execute_fn=mock_execute)
    issues.get_issue(Path("/repo"), 123)

    cmd = created_commands[0]
    assert cmd[0] == "gh"
    assert cmd[1] == "issue"
    assert cmd[2] == "view"
    assert cmd[3] == "123"
    assert "--json" in cmd
    # Verify all required JSON fields are requested
    json_fields_idx = cmd.index("--json") + 1
    json_fields = cmd[json_fields_idx]
    assert "number" in json_fields
    assert "title" in json_fields
    assert "body" in json_fields
    assert "state" in json_fields
    assert "url" in json_fields


def test_get_issue_command_failure() -> None:
    """Test get_issue raises RuntimeError on gh CLI failure."""

    def mock_execute_failure(cmd: list[str], cwd: Path) -> str:
        raise RuntimeError("Issue not found")

    issues = RealGitHubIssues(execute_fn=mock_execute_failure)

    with pytest.raises(RuntimeError, match="Issue not found"):
        issues.get_issue(Path("/repo"), 999)


def test_add_comment_success() -> None:
    """Test add_comment calls gh CLI with correct arguments."""
    created_commands = []

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        created_commands.append(cmd)
        return ""

    issues = RealGitHubIssues(execute_fn=mock_execute)
    issues.add_comment(Path("/repo"), 42, "This is my comment body")

    # Verify command structure
    cmd = created_commands[0]
    assert cmd[0] == "gh"
    assert cmd[1] == "issue"
    assert cmd[2] == "comment"
    assert cmd[3] == "42"
    assert "--body" in cmd
    assert "This is my comment body" in cmd


def test_add_comment_multiline_body() -> None:
    """Test add_comment handles multiline comment bodies."""
    created_commands = []

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        created_commands.append(cmd)
        return ""

    issues = RealGitHubIssues(execute_fn=mock_execute)
    multiline_body = """First line of comment

Second line after blank line

Third line"""
    issues.add_comment(Path("/repo"), 10, multiline_body)

    cmd = created_commands[0]
    assert multiline_body in cmd


def test_add_comment_command_failure() -> None:
    """Test add_comment raises RuntimeError on gh CLI failure."""

    def mock_execute_failure(cmd: list[str], cwd: Path) -> str:
        raise RuntimeError("Issue not found")

    issues = RealGitHubIssues(execute_fn=mock_execute_failure)

    with pytest.raises(RuntimeError, match="Issue not found"):
        issues.add_comment(Path("/repo"), 999, "Comment body")


def test_list_issues_all() -> None:
    """Test list_issues without filters."""
    issues_data = [
        {
            "number": 1,
            "title": "Issue 1",
            "body": "Body 1",
            "state": "OPEN",
            "url": "http://url/1",
        },
        {
            "number": 2,
            "title": "Issue 2",
            "body": "Body 2",
            "state": "CLOSED",
            "url": "http://url/2",
        },
    ]

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        if "issue" in cmd and "list" in cmd:
            return json.dumps(issues_data)
        return "[]"

    issues = RealGitHubIssues(execute_fn=mock_execute)
    result = issues.list_issues(Path("/repo"))

    assert len(result) == 2
    assert result[0].number == 1
    assert result[0].title == "Issue 1"
    assert result[1].number == 2
    assert result[1].state == "CLOSED"


def test_list_issues_with_state_filter() -> None:
    """Test list_issues with state filter."""
    created_commands = []

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        created_commands.append(cmd)
        return "[]"

    issues = RealGitHubIssues(execute_fn=mock_execute)
    issues.list_issues(Path("/repo"), state="open")

    cmd = created_commands[0]
    assert "--state" in cmd
    assert "open" in cmd


def test_list_issues_with_labels_filter() -> None:
    """Test list_issues with labels filter."""
    created_commands = []

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        created_commands.append(cmd)
        return "[]"

    issues = RealGitHubIssues(execute_fn=mock_execute)
    issues.list_issues(Path("/repo"), labels=["plan", "erk"])

    cmd = created_commands[0]
    assert cmd.count("--label") == 2
    assert "plan" in cmd
    assert "erk" in cmd


def test_list_issues_with_both_filters() -> None:
    """Test list_issues with both labels and state filters."""
    created_commands = []

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        created_commands.append(cmd)
        return "[]"

    issues = RealGitHubIssues(execute_fn=mock_execute)
    issues.list_issues(Path("/repo"), labels=["bug"], state="closed")

    cmd = created_commands[0]
    assert "--label" in cmd
    assert "bug" in cmd
    assert "--state" in cmd
    assert "closed" in cmd


def test_list_issues_json_fields() -> None:
    """Test list_issues requests all required JSON fields."""
    created_commands = []

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        created_commands.append(cmd)
        return "[]"

    issues = RealGitHubIssues(execute_fn=mock_execute)
    issues.list_issues(Path("/repo"))

    cmd = created_commands[0]
    assert "--json" in cmd
    json_fields_idx = cmd.index("--json") + 1
    json_fields = cmd[json_fields_idx]
    assert "number" in json_fields
    assert "title" in json_fields
    assert "body" in json_fields
    assert "state" in json_fields
    assert "url" in json_fields


def test_list_issues_command_failure() -> None:
    """Test list_issues raises RuntimeError on gh CLI failure."""

    def mock_execute_failure(cmd: list[str], cwd: Path) -> str:
        raise RuntimeError("gh not authenticated")

    issues = RealGitHubIssues(execute_fn=mock_execute_failure)

    with pytest.raises(RuntimeError, match="not authenticated"):
        issues.list_issues(Path("/repo"))


def test_list_issues_empty_response() -> None:
    """Test list_issues handles empty results."""

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        return "[]"

    issues = RealGitHubIssues(execute_fn=mock_execute)
    result = issues.list_issues(Path("/repo"))

    assert result == []


def test_list_issues_parses_all_fields() -> None:
    """Test list_issues correctly parses all IssueInfo fields."""
    issues_data = [
        {
            "number": 123,
            "title": "Complex Issue Title with Special Chars: / & <>",
            "body": "Multi-line\nbody\nwith\nlinebreaks",
            "state": "OPEN",
            "url": "https://github.com/owner/repo/issues/123",
        }
    ]

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        return json.dumps(issues_data)

    issues = RealGitHubIssues(execute_fn=mock_execute)
    result = issues.list_issues(Path("/repo"))

    assert len(result) == 1
    issue = result[0]
    assert issue.number == 123
    assert issue.title == "Complex Issue Title with Special Chars: / & <>"
    assert issue.body == "Multi-line\nbody\nwith\nlinebreaks"
    assert issue.state == "OPEN"
    assert issue.url == "https://github.com/owner/repo/issues/123"
