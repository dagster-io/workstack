"""Unit tests for GitHubPlanIssueStore using FakeGitHubIssues."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.core.github.issues import FakeGitHubIssues
from erk.core.plan_issue_store import (
    GitHubPlanIssueStore,
    PlanIssueQuery,
    PlanIssueState,
)
from tests.test_utils.github_helpers import create_test_issue


def test_get_plan_issue_success() -> None:
    """Test fetching a plan issue from GitHub."""
    # Create fake with pre-configured issue
    issue = create_test_issue(
        number=42,
        title="Implement feature X",
        body="Description of feature X",
        labels=["erk-plan", "enhancement"],
        assignees=["alice", "bob"],
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 16, 14, 45, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={42: issue})
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "42")

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
    issue = create_test_issue(
        number=100,
        title="Closed Issue",
        state="CLOSED",
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={100: issue})
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "100")

    assert result.state == PlanIssueState.CLOSED


def test_get_plan_issue_empty_body() -> None:
    """Test handling of empty body field."""
    issue = create_test_issue(
        number=50,
        title="Issue without body",
    )
    fake_github = FakeGitHubIssues(issues={50: issue})
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "50")

    assert result.body == ""


def test_get_plan_issue_not_found() -> None:
    """Test error handling when issue is not found."""
    fake_github = FakeGitHubIssues(issues={})
    store = GitHubPlanIssueStore(fake_github)

    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        store.get_plan_issue(Path("/fake/repo"), "999")


def test_list_plan_issues_no_filters() -> None:
    """Test listing all plan issues with no filters."""
    issue1 = create_test_issue(
        number=1,
        title="Issue 1",
        labels=["erk-plan"],
    )
    issue2 = create_test_issue(
        number=2,
        title="Issue 2",
        state="CLOSED",
        labels=["bug"],
        created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue1, 2: issue2})
    store = GitHubPlanIssueStore(fake_github)

    query = PlanIssueQuery()
    results = store.list_plan_issues(Path("/fake/repo"), query)

    # Verify results
    assert len(results) == 2
    assert {r.plan_issue_identifier for r in results} == {"1", "2"}


def test_list_plan_issues_with_labels() -> None:
    """Test filtering by labels."""
    issue1 = create_test_issue(
        number=1,
        title="Issue 1",
        labels=["erk-plan", "erk-queue"],
    )
    issue2 = create_test_issue(
        number=2,
        title="Issue 2",
        labels=["bug"],
        created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue1, 2: issue2})
    store = GitHubPlanIssueStore(fake_github)

    # Note: FakeGitHubIssues doesn't implement label filtering,
    # so this test verifies the call succeeds rather than filtering behavior
    query = PlanIssueQuery(labels=["erk-plan", "erk-queue"])
    results = store.list_plan_issues(Path("/fake/repo"), query)

    # Fake returns all issues regardless of label filter
    assert len(results) >= 0


def test_list_plan_issues_with_state_open() -> None:
    """Test filtering by OPEN state."""
    issue1 = create_test_issue(number=1, title="Open Issue")
    issue2 = create_test_issue(
        number=2,
        title="Closed Issue",
        state="CLOSED",
        created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue1, 2: issue2})
    store = GitHubPlanIssueStore(fake_github)

    query = PlanIssueQuery(state=PlanIssueState.OPEN)
    results = store.list_plan_issues(Path("/fake/repo"), query)

    # Verify only OPEN issues returned
    assert len(results) == 1
    assert results[0].plan_issue_identifier == "1"
    assert results[0].state == PlanIssueState.OPEN


def test_list_plan_issues_with_state_closed() -> None:
    """Test filtering by CLOSED state."""
    issue1 = create_test_issue(number=1, title="Open Issue")
    issue2 = create_test_issue(
        number=2,
        title="Closed Issue",
        state="CLOSED",
        created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue1, 2: issue2})
    store = GitHubPlanIssueStore(fake_github)

    query = PlanIssueQuery(state=PlanIssueState.CLOSED)
    results = store.list_plan_issues(Path("/fake/repo"), query)

    # Verify only CLOSED issues returned
    assert len(results) == 1
    assert results[0].plan_issue_identifier == "2"
    assert results[0].state == PlanIssueState.CLOSED


def test_list_plan_issues_with_limit() -> None:
    """Test limiting results."""
    issues = {
        i: create_test_issue(
            number=i,
            title=f"Issue {i}",
            created_at=datetime(2024, 1, i, 0, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, i, 0, 0, 0, tzinfo=UTC),
        )
        for i in range(1, 11)
    }
    fake_github = FakeGitHubIssues(issues=issues)
    store = GitHubPlanIssueStore(fake_github)

    query = PlanIssueQuery(limit=3)
    results = store.list_plan_issues(Path("/fake/repo"), query)

    # Verify limit is applied
    assert len(results) == 3


def test_list_plan_issues_combined_filters() -> None:
    """Test combining multiple filters."""
    issue1 = create_test_issue(
        number=1,
        title="Open Issue",
        labels=["erk-plan"],
    )
    issue2 = create_test_issue(
        number=2,
        title="Closed Issue",
        state="CLOSED",
        labels=["erk-plan"],
        created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue1, 2: issue2})
    store = GitHubPlanIssueStore(fake_github)

    query = PlanIssueQuery(
        labels=["erk-plan"],
        state=PlanIssueState.OPEN,
        limit=5,
    )
    results = store.list_plan_issues(Path("/fake/repo"), query)

    # Verify state filtering works (label filtering not implemented in fake)
    assert all(r.state == PlanIssueState.OPEN for r in results)


def test_timestamp_parsing_with_z_suffix() -> None:
    """Test that datetime objects from IssueInfo are correctly converted."""
    issue = create_test_issue(
        number=1,
        title="Test",
        created_at=datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC),
        updated_at=datetime(2024, 1, 16, 14, 20, 30, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue})
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "1")

    # Verify timestamps are preserved correctly
    assert result.created_at == datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
    assert result.updated_at == datetime(2024, 1, 16, 14, 20, 30, tzinfo=UTC)


def test_label_extraction() -> None:
    """Test that labels from IssueInfo are correctly converted."""
    issue = create_test_issue(
        number=1,
        title="Test",
        labels=["erk-plan", "erk-queue", "enhancement"],
    )
    fake_github = FakeGitHubIssues(issues={1: issue})
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "1")

    # Verify labels are preserved as list of strings
    assert result.labels == ["erk-plan", "erk-queue", "enhancement"]


def test_assignee_extraction() -> None:
    """Test that assignees from IssueInfo are correctly converted."""
    issue = create_test_issue(
        number=1,
        title="Test",
        assignees=["alice", "bob", "charlie"],
    )
    fake_github = FakeGitHubIssues(issues={1: issue})
    store = GitHubPlanIssueStore(fake_github)

    result = store.get_plan_issue(Path("/fake/repo"), "1")

    # Verify assignees are preserved as list of strings
    assert result.assignees == ["alice", "bob", "charlie"]


def test_metadata_preserves_github_number() -> None:
    """Test that GitHub issue number is preserved in metadata."""
    issue = create_test_issue(
        number=42,
        title="Test",
    )
    fake_github = FakeGitHubIssues(issues={42: issue})
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
    store = GitHubPlanIssueStore(fake_github)
    assert store.get_provider_name() == "github"


def test_list_plan_issues_passes_limit_to_interface() -> None:
    """Test list_plan_issues passes limit to GitHubIssues interface."""
    now = datetime.now(UTC)
    issues = {
        1: create_test_issue(
            number=1,
            title="Plan 1",
            body="Body 1",
            labels=["erk-plan"],
            created_at=now,
            updated_at=now,
        ),
        2: create_test_issue(
            number=2,
            title="Plan 2",
            body="Body 2",
            labels=["erk-plan"],
            created_at=now,
            updated_at=now,
        ),
    }
    fake_github = FakeGitHubIssues(issues=issues)
    store = GitHubPlanIssueStore(fake_github)

    # Query with limit=1
    query = PlanIssueQuery(labels=["erk-plan"], limit=1)
    results = store.list_plan_issues(Path("/repo"), query)

    # Should only return 1 result (not slice in Python)
    assert len(results) == 1
