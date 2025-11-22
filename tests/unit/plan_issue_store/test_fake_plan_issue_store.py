"""Unit tests for FakePlanIssueStore."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.core.plan_issue_store import (
    FakePlanIssueStore,
    PlanIssue,
    PlanIssueQuery,
    PlanIssueState,
)


def test_get_plan_issue_success() -> None:
    """Test fetching a plan issue that exists."""
    plan_issue = PlanIssue(
        plan_issue_identifier="42",
        title="Test Issue",
        body="Test body",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/42",
        labels=["erk-plan"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        metadata={"number": 42},
    )

    store = FakePlanIssueStore(plan_issues={"42": plan_issue})
    result = store.get_plan_issue(Path("/fake/repo"), "42")

    assert result == plan_issue


def test_get_plan_issue_not_found() -> None:
    """Test fetching a plan issue that doesn't exist raises RuntimeError."""
    store = FakePlanIssueStore(plan_issues={})

    with pytest.raises(RuntimeError, match="Plan issue '999' not found"):
        store.get_plan_issue(Path("/fake/repo"), "999")


def test_list_plan_issues_no_filters() -> None:
    """Test listing all plan issues with no filters."""
    issue1 = PlanIssue(
        plan_issue_identifier="1",
        title="Issue 1",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue2 = PlanIssue(
        plan_issue_identifier="2",
        title="Issue 2",
        body="",
        state=PlanIssueState.CLOSED,
        url="https://example.com/issues/2",
        labels=["bug"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanIssueStore(plan_issues={"1": issue1, "2": issue2})
    query = PlanIssueQuery()
    results = store.list_plan_issues(Path("/fake/repo"), query)

    assert len(results) == 2
    assert issue1 in results
    assert issue2 in results


def test_list_plan_issues_filter_by_state() -> None:
    """Test filtering plan issues by state."""
    open_issue = PlanIssue(
        plan_issue_identifier="1",
        title="Open Issue",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/1",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    closed_issue = PlanIssue(
        plan_issue_identifier="2",
        title="Closed Issue",
        body="",
        state=PlanIssueState.CLOSED,
        url="https://example.com/issues/2",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanIssueStore(plan_issues={"1": open_issue, "2": closed_issue})

    # Filter for open issues
    query_open = PlanIssueQuery(state=PlanIssueState.OPEN)
    results_open = store.list_plan_issues(Path("/fake/repo"), query_open)
    assert len(results_open) == 1
    assert results_open[0] == open_issue

    # Filter for closed issues
    query_closed = PlanIssueQuery(state=PlanIssueState.CLOSED)
    results_closed = store.list_plan_issues(Path("/fake/repo"), query_closed)
    assert len(results_closed) == 1
    assert results_closed[0] == closed_issue


def test_list_plan_issues_filter_by_labels_and_logic() -> None:
    """Test filtering plan issues by labels with AND logic."""
    issue_with_both = PlanIssue(
        plan_issue_identifier="1",
        title="Issue with both labels",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/1",
        labels=["erk-plan", "erk-queue"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue_with_one = PlanIssue(
        plan_issue_identifier="2",
        title="Issue with one label",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/2",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanIssueStore(plan_issues={"1": issue_with_both, "2": issue_with_one})

    # Query for both labels (AND logic)
    query = PlanIssueQuery(labels=["erk-plan", "erk-queue"])
    results = store.list_plan_issues(Path("/fake/repo"), query)

    # Only issue 1 has both labels
    assert len(results) == 1
    assert results[0] == issue_with_both


def test_list_plan_issues_filter_by_assignee() -> None:
    """Test filtering plan issues by assignee."""
    alice_issue = PlanIssue(
        plan_issue_identifier="1",
        title="Alice's Issue",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/1",
        labels=[],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    bob_issue = PlanIssue(
        plan_issue_identifier="2",
        title="Bob's Issue",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/2",
        labels=[],
        assignees=["bob"],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanIssueStore(plan_issues={"1": alice_issue, "2": bob_issue})
    query = PlanIssueQuery(assignee="alice")
    results = store.list_plan_issues(Path("/fake/repo"), query)

    assert len(results) == 1
    assert results[0] == alice_issue


def test_list_plan_issues_filter_by_limit() -> None:
    """Test limiting the number of returned plan issues."""
    issue1 = PlanIssue(
        plan_issue_identifier="1",
        title="Issue 1",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/1",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue2 = PlanIssue(
        plan_issue_identifier="2",
        title="Issue 2",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/2",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )
    issue3 = PlanIssue(
        plan_issue_identifier="3",
        title="Issue 3",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/3",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
        updated_at=datetime(2024, 1, 3, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanIssueStore(plan_issues={"1": issue1, "2": issue2, "3": issue3})
    query = PlanIssueQuery(limit=2)
    results = store.list_plan_issues(Path("/fake/repo"), query)

    assert len(results) == 2


def test_list_plan_issues_combined_filters() -> None:
    """Test combining multiple filters."""
    matching_issue = PlanIssue(
        plan_issue_identifier="1",
        title="Matching Issue",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/1",
        labels=["erk-plan", "bug"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    wrong_state = PlanIssue(
        plan_issue_identifier="2",
        title="Wrong State",
        body="",
        state=PlanIssueState.CLOSED,
        url="https://example.com/issues/2",
        labels=["erk-plan", "bug"],
        assignees=["alice"],
        created_at=datetime(2024, 1, 2, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, tzinfo=UTC),
        metadata={},
    )
    wrong_labels = PlanIssue(
        plan_issue_identifier="3",
        title="Wrong Labels",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/3",
        labels=["erk-plan"],  # Missing "bug"
        assignees=["alice"],
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
        updated_at=datetime(2024, 1, 3, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanIssueStore(
        plan_issues={"1": matching_issue, "2": wrong_state, "3": wrong_labels}
    )
    query = PlanIssueQuery(
        state=PlanIssueState.OPEN,
        labels=["erk-plan", "bug"],
        assignee="alice",
    )
    results = store.list_plan_issues(Path("/fake/repo"), query)

    # Only issue 1 matches all criteria
    assert len(results) == 1
    assert results[0] == matching_issue


def test_list_plan_issues_empty_results() -> None:
    """Test querying with filters that match no issues."""
    issue = PlanIssue(
        plan_issue_identifier="1",
        title="Issue",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/1",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanIssueStore(plan_issues={"1": issue})
    query = PlanIssueQuery(state=PlanIssueState.CLOSED)
    results = store.list_plan_issues(Path("/fake/repo"), query)

    assert len(results) == 0


def test_get_provider_name() -> None:
    """Test getting the provider name."""
    store = FakePlanIssueStore()
    assert store.get_provider_name() == "fake"


def test_string_identifier_flexibility() -> None:
    """Test that identifiers work as strings (not just integers)."""
    # Test with various string formats
    issue_github = PlanIssue(
        plan_issue_identifier="42",
        title="GitHub Issue",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/42",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue_jira = PlanIssue(
        plan_issue_identifier="PROJ-123",
        title="Jira Issue",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/PROJ-123",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )
    issue_linear = PlanIssue(
        plan_issue_identifier="550e8400-e29b-41d4-a716-446655440000",
        title="Linear Issue",
        body="",
        state=PlanIssueState.OPEN,
        url="https://example.com/issues/550e8400",
        labels=[],
        assignees=[],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        metadata={},
    )

    store = FakePlanIssueStore(
        plan_issues={
            "42": issue_github,
            "PROJ-123": issue_jira,
            "550e8400-e29b-41d4-a716-446655440000": issue_linear,
        }
    )

    # All identifier formats should work
    assert store.get_plan_issue(Path("/fake"), "42") == issue_github
    assert store.get_plan_issue(Path("/fake"), "PROJ-123") == issue_jira
    assert (
        store.get_plan_issue(Path("/fake"), "550e8400-e29b-41d4-a716-446655440000") == issue_linear
    )
