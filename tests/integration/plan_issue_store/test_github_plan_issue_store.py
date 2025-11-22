"""Integration tests for GitHubPlanIssueStore with mocked gh CLI."""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from erk.core.github.issues import FakeGitHubIssues
from erk.core.plan_issue_store import (
    GitHubPlanIssueStore,
    PlanIssueQuery,
    PlanIssueState,
)


def test_get_plan_issue_success() -> None:
    """Test fetching a plan issue from GitHub."""
    # Mock gh CLI response
    mock_response = {
        "number": 42,
        "title": "Implement feature X",
        "body": "Description of feature X",
        "state": "OPEN",
        "url": "https://github.com/owner/repo/issues/42",
        "labels": [{"name": "erk-plan"}, {"name": "enhancement"}],
        "assignees": [{"login": "alice"}, {"login": "bob"}],
        "createdAt": "2024-01-15T10:30:00Z",
        "updatedAt": "2024-01-16T14:45:00Z",
    }

    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "42")

    # Verify gh CLI was called correctly
    mock_execute.assert_called_once()
    call_args = mock_execute.call_args[0]
    assert call_args[0][0] == "gh"
    assert call_args[0][1] == "issue"
    assert call_args[0][2] == "view"
    assert call_args[0][3] == "42"
    assert "--json" in call_args[0]

    # Verify conversion to PlanIssue
    assert result.plan_issue_identifier == "42"
    assert result.title == "Implement feature X"
    assert result.body == "Description of feature X"
    assert result.state == PlanIssueState.OPEN
    assert result.url == "https://github.com/owner/repo/issues/42"
    assert result.labels == ["erk-plan", "enhancement"]
    assert result.assignees == ["alice", "bob"]
    assert result.created_at == datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
    assert result.updated_at == datetime(2024, 1, 16, 14, 45, 0, tzinfo=UTC)
    assert result.metadata == {"number": 42}


def test_get_plan_issue_closed_state() -> None:
    """Test that CLOSED state is normalized correctly."""
    mock_response = {
        "number": 100,
        "title": "Closed Issue",
        "body": "",
        "state": "CLOSED",
        "url": "https://github.com/owner/repo/issues/100",
        "labels": [],
        "assignees": [],
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-02T00:00:00Z",
    }

    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "100")

    assert result.state == PlanIssueState.CLOSED


def test_get_plan_issue_empty_body() -> None:
    """Test handling of missing or empty body field."""
    mock_response = {
        "number": 50,
        "title": "Issue without body",
        "state": "OPEN",
        "url": "https://github.com/owner/repo/issues/50",
        "labels": [],
        "assignees": [],
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
    }

    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "50")

    assert result.body == ""


def test_get_plan_issue_not_found() -> None:
    """Test error handling when issue is not found."""
    mock_execute = Mock(side_effect=RuntimeError("Issue not found"))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    with pytest.raises(RuntimeError, match="Issue not found"):
        store.get_plan_issue(Path("/fake/repo"), "999")


def test_list_plan_issues_no_filters() -> None:
    """Test listing all plan issues with no filters."""
    mock_response = [
        {
            "number": 1,
            "title": "Issue 1",
            "body": "",
            "state": "OPEN",
            "url": "https://github.com/owner/repo/issues/1",
            "labels": [{"name": "erk-plan"}],
            "assignees": [],
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
        },
        {
            "number": 2,
            "title": "Issue 2",
            "body": "",
            "state": "CLOSED",
            "url": "https://github.com/owner/repo/issues/2",
            "labels": [{"name": "bug"}],
            "assignees": [],
            "createdAt": "2024-01-02T00:00:00Z",
            "updatedAt": "2024-01-02T00:00:00Z",
        },
    ]

    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    query = PlanIssueQuery()
    results = store.list_plan_issues(Path("/fake/repo"), query)

    # Verify gh CLI was called correctly
    mock_execute.assert_called_once()
    call_args = mock_execute.call_args[0]
    assert call_args[0][0] == "gh"
    assert call_args[0][1] == "issue"
    assert call_args[0][2] == "list"

    # Verify results
    assert len(results) == 2
    assert results[0].plan_issue_identifier == "1"
    assert results[1].plan_issue_identifier == "2"


def test_list_plan_issues_with_labels() -> None:
    """Test filtering by labels (AND logic)."""
    mock_response = []
    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    query = PlanIssueQuery(labels=["erk-plan", "erk-queue"])
    store.list_plan_issues(Path("/fake/repo"), query)

    # Verify gh CLI was called with label filters
    call_args = mock_execute.call_args[0][0]
    assert "--label" in call_args
    # Both labels should be in the command
    label_indices = [i for i, arg in enumerate(call_args) if arg == "--label"]
    assert len(label_indices) == 2


def test_list_plan_issues_with_state_open() -> None:
    """Test filtering by OPEN state."""
    mock_response = []
    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    query = PlanIssueQuery(state=PlanIssueState.OPEN)
    store.list_plan_issues(Path("/fake/repo"), query)

    # Verify gh CLI was called with state filter
    call_args = mock_execute.call_args[0][0]
    assert "--state" in call_args
    state_index = call_args.index("--state")
    assert call_args[state_index + 1] == "open"


def test_list_plan_issues_with_state_closed() -> None:
    """Test filtering by CLOSED state."""
    mock_response = []
    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    query = PlanIssueQuery(state=PlanIssueState.CLOSED)
    store.list_plan_issues(Path("/fake/repo"), query)

    # Verify gh CLI was called with state filter
    call_args = mock_execute.call_args[0][0]
    assert "--state" in call_args
    state_index = call_args.index("--state")
    assert call_args[state_index + 1] == "closed"


def test_list_plan_issues_with_limit() -> None:
    """Test limiting results."""
    mock_response = []
    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    query = PlanIssueQuery(limit=10)
    store.list_plan_issues(Path("/fake/repo"), query)

    # Verify gh CLI was called with limit
    call_args = mock_execute.call_args[0][0]
    assert "--limit" in call_args
    limit_index = call_args.index("--limit")
    assert call_args[limit_index + 1] == "10"


def test_list_plan_issues_combined_filters() -> None:
    """Test combining multiple filters."""
    mock_response = []
    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    query = PlanIssueQuery(
        labels=["erk-plan"],
        state=PlanIssueState.OPEN,
        limit=5,
    )
    store.list_plan_issues(Path("/fake/repo"), query)

    # Verify all filters are in the command
    call_args = mock_execute.call_args[0][0]
    assert "--label" in call_args
    assert "--state" in call_args
    assert "--limit" in call_args


def test_timestamp_parsing_with_z_suffix() -> None:
    """Test that ISO8601 timestamps with 'Z' suffix are parsed correctly."""
    mock_response = {
        "number": 1,
        "title": "Test",
        "body": "",
        "state": "OPEN",
        "url": "https://github.com/owner/repo/issues/1",
        "labels": [],
        "assignees": [],
        "createdAt": "2024-01-15T10:30:45Z",
        "updatedAt": "2024-01-16T14:20:30Z",
    }

    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "1")

    # Verify timestamps are parsed correctly
    assert result.created_at == datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
    assert result.updated_at == datetime(2024, 1, 16, 14, 20, 30, tzinfo=UTC)


def test_label_extraction() -> None:
    """Test that labels are extracted from GitHub's label objects."""
    mock_response = {
        "number": 1,
        "title": "Test",
        "body": "",
        "state": "OPEN",
        "url": "https://github.com/owner/repo/issues/1",
        "labels": [
            {"name": "erk-plan"},
            {"name": "erk-queue"},
            {"name": "enhancement"},
        ],
        "assignees": [],
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
    }

    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "1")

    # Verify labels are extracted as list of strings
    assert result.labels == ["erk-plan", "erk-queue", "enhancement"]


def test_assignee_extraction() -> None:
    """Test that assignees are extracted from GitHub's assignee objects."""
    mock_response = {
        "number": 1,
        "title": "Test",
        "body": "",
        "state": "OPEN",
        "url": "https://github.com/owner/repo/issues/1",
        "labels": [],
        "assignees": [{"login": "alice"}, {"login": "bob"}, {"login": "charlie"}],
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
    }

    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "1")

    # Verify assignees are extracted as list of strings
    assert result.assignees == ["alice", "bob", "charlie"]


def test_metadata_preserves_github_number() -> None:
    """Test that GitHub issue number is preserved in metadata."""
    mock_response = {
        "number": 42,
        "title": "Test",
        "body": "",
        "state": "OPEN",
        "url": "https://github.com/owner/repo/issues/42",
        "labels": [],
        "assignees": [],
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
    }

    mock_execute = Mock(return_value=json.dumps(mock_response))
    fake_github = FakeGitHubIssues()
    fake_github._execute = mock_execute  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "42")

    # Verify metadata contains GitHub number
    assert result.metadata == {"number": 42}
    # Verify identifier is string
    assert result.plan_issue_identifier == "42"
    assert isinstance(result.plan_issue_identifier, str)


def test_get_provider_name() -> None:
    """Test getting the provider name."""
    fake_github = FakeGitHubIssues()
    fake_github._execute = Mock()  # type: ignore[attr-defined]
    store = GitHubPlanIssueStore(fake_github)
    assert store.get_provider_name() == "github"
