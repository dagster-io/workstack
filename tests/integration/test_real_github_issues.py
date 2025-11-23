"""Tests for RealGitHubIssues with mocked subprocess execution.

These tests verify that RealGitHubIssues correctly calls gh CLI commands and handles
responses. We use pytest monkeypatch to mock subprocess calls.
"""

import json
import subprocess
from pathlib import Path

import pytest
from erk_shared.github.issues import RealGitHubIssues
from pytest import MonkeyPatch

from tests.integration.test_helpers import mock_subprocess_run


def test_create_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue calls gh CLI with correct arguments."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="42",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
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


def test_create_issue_multiple_labels(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue includes all labels in command."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="1",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
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


def test_create_issue_no_labels(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue works with empty labels list."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="1",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.create_issue(Path("/repo"), title="Title", body="Body", labels=[])

        cmd = created_commands[0]
        # No --label flags should be present
        assert "--label" not in cmd


def test_create_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("gh command failed: not authenticated")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="not authenticated"):
            issues.create_issue(Path("/repo"), "Title", "Body", ["label"])


def test_get_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue calls gh CLI and parses response."""
    issue_data = {
        "number": 42,
        "title": "Test Issue Title",
        "body": "Test issue body content",
        "state": "OPEN",
        "url": "https://github.com/owner/repo/issues/42",
        "labels": [{"name": "bug"}, {"name": "enhancement"}],
        "assignees": [{"login": "alice"}, {"login": "bob"}],
        "createdAt": "2024-01-15T10:30:00Z",
        "updatedAt": "2024-01-16T14:45:00Z",
    }

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issue_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.get_issue(Path("/repo"), 42)

        assert result.number == 42
        assert result.title == "Test Issue Title"
        assert result.body == "Test issue body content"
        assert result.state == "OPEN"
        assert result.url == "https://github.com/owner/repo/issues/42"


def test_get_issue_command_structure(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue constructs correct gh CLI command."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(
                {
                    "number": 123,
                    "title": "Title",
                    "body": "Body",
                    "state": "OPEN",
                    "url": "http://url",
                    "labels": [],
                    "assignees": [],
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                }
            ),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
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


def test_get_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.get_issue(Path("/repo"), 999)


def test_add_comment_success(monkeypatch: MonkeyPatch) -> None:
    """Test add_comment calls gh CLI with correct arguments."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.add_comment(Path("/repo"), 42, "This is my comment body")

        # Verify command structure
        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "issue"
        assert cmd[2] == "comment"
        assert cmd[3] == "42"
        assert "--body" in cmd
        assert "This is my comment body" in cmd


def test_add_comment_multiline_body(monkeypatch: MonkeyPatch) -> None:
    """Test add_comment handles multiline comment bodies."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        multiline_body = """First line of comment

Second line after blank line

Third line"""
        issues.add_comment(Path("/repo"), 10, multiline_body)

        cmd = created_commands[0]
        assert multiline_body in cmd


def test_add_comment_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test add_comment raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.add_comment(Path("/repo"), 999, "Comment body")


def test_list_issues_all(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues without filters."""
    issues_data = [
        {
            "number": 1,
            "title": "Issue 1",
            "body": "Body 1",
            "state": "OPEN",
            "url": "http://url/1",
            "labels": [],
            "assignees": [],
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
        },
        {
            "number": 2,
            "title": "Issue 2",
            "body": "Body 2",
            "state": "CLOSED",
            "url": "http://url/2",
            "labels": [],
            "assignees": [],
            "createdAt": "2024-01-02T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
        },
    ]

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issues_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.list_issues(Path("/repo"))

        assert len(result) == 2
        assert result[0].number == 1
        assert result[0].title == "Issue 1"
        assert result[1].number == 2
        assert result[1].state == "CLOSED"


def test_list_issues_with_state_filter(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues with state filter."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.list_issues(Path("/repo"), state="open")

        cmd = created_commands[0]
        assert "--state" in cmd
        assert "open" in cmd


def test_list_issues_with_labels_filter(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues with labels filter."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.list_issues(Path("/repo"), labels=["plan", "erk"])

        cmd = created_commands[0]
        assert cmd.count("--label") == 2
        assert "plan" in cmd
        assert "erk" in cmd


def test_list_issues_with_both_filters(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues with both labels and state filters."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.list_issues(Path("/repo"), labels=["bug"], state="closed")

        cmd = created_commands[0]
        assert "--label" in cmd
        assert "bug" in cmd
        assert "--state" in cmd
        assert "closed" in cmd


def test_list_issues_json_fields(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues requests all required JSON fields."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
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


def test_list_issues_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("gh not authenticated")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()

        with pytest.raises(RuntimeError, match="not authenticated"):
            issues.list_issues(Path("/repo"))


def test_list_issues_empty_response(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues handles empty results."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.list_issues(Path("/repo"))

        assert result == []


def test_list_issues_parses_all_fields(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues correctly parses all IssueInfo fields."""
    issues_data = [
        {
            "number": 123,
            "title": "Complex Issue Title with Special Chars: / & <>",
            "body": "Multi-line\nbody\nwith\nlinebreaks",
            "state": "OPEN",
            "url": "https://github.com/owner/repo/issues/123",
            "labels": [{"name": "bug"}, {"name": "documentation"}],
            "assignees": [{"login": "alice"}],
            "createdAt": "2024-01-15T10:30:00Z",
            "updatedAt": "2024-01-20T16:45:00Z",
        }
    ]

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issues_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        result = issues.list_issues(Path("/repo"))

        assert len(result) == 1
        issue = result[0]
        assert issue.number == 123
        assert issue.title == "Complex Issue Title with Special Chars: / & <>"
        assert issue.body == "Multi-line\nbody\nwith\nlinebreaks"
        assert issue.state == "OPEN"
        assert issue.url == "https://github.com/owner/repo/issues/123"


def test_list_issues_with_limit(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues respects limit parameter."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues()
        issues.list_issues(Path("/repo"), limit=10)

        cmd = created_commands[0]
        assert "--limit" in cmd
        assert "10" in cmd
