"""Tests for FakeGitHubIssues test infrastructure.

These tests verify that FakeGitHubIssues correctly simulates GitHub issue operations,
providing reliable test doubles for tests that use issue functionality.
"""

import pytest

from erk.core.github.issues import FakeGitHubIssues, IssueInfo
from tests.test_utils import sentinel_path


def test_fake_github_issues_initialization() -> None:
    """Test that FakeGitHubIssues initializes with empty state."""
    issues = FakeGitHubIssues()

    result = issues.list_issues(sentinel_path())
    assert result == []


def test_fake_github_issues_create_issue_returns_number() -> None:
    """Test create_issue returns predictable issue number."""
    issues = FakeGitHubIssues(next_issue_number=42)

    issue_num = issues.create_issue(
        sentinel_path(),
        title="Test Issue",
        body="Test body",
        labels=["plan", "erk"],
    )

    assert issue_num == 42


def test_fake_github_issues_create_issue_increments_number() -> None:
    """Test create_issue increments issue numbers sequentially."""
    issues = FakeGitHubIssues(next_issue_number=1)

    num1 = issues.create_issue(sentinel_path(), "Issue 1", "Body 1", ["label1"])
    num2 = issues.create_issue(sentinel_path(), "Issue 2", "Body 2", ["label2"])
    num3 = issues.create_issue(sentinel_path(), "Issue 3", "Body 3", ["label3"])

    assert num1 == 1
    assert num2 == 2
    assert num3 == 3


def test_fake_github_issues_create_issue_tracks_mutation() -> None:
    """Test create_issue tracks created issues in mutation list."""
    issues = FakeGitHubIssues()

    issues.create_issue(sentinel_path(), "Title 1", "Body 1", ["label1", "label2"])
    issues.create_issue(sentinel_path(), "Title 2", "Body 2", ["label3"])

    assert issues.created_issues == [
        ("Title 1", "Body 1", ["label1", "label2"]),
        ("Title 2", "Body 2", ["label3"]),
    ]


def test_fake_github_issues_created_issues_empty_initially() -> None:
    """Test created_issues property is empty list initially."""
    issues = FakeGitHubIssues()

    assert issues.created_issues == []


def test_fake_github_issues_created_issues_read_only() -> None:
    """Test created_issues property returns list that can be read."""
    issues = FakeGitHubIssues()
    issues.create_issue(sentinel_path(), "Title", "Body", ["label"])

    # Should be able to read the list
    created = issues.created_issues
    assert len(created) == 1
    assert created[0] == ("Title", "Body", ["label"])


def test_fake_github_issues_get_issue_existing() -> None:
    """Test get_issue returns stored issue for existing number."""
    pre_configured = {
        42: IssueInfo(
            number=42,
            title="Existing Issue",
            body="Existing body",
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
        )
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    result = issues.get_issue(sentinel_path(), 42)

    assert result.number == 42
    assert result.title == "Existing Issue"
    assert result.body == "Existing body"
    assert result.state == "OPEN"
    assert result.url == "https://github.com/owner/repo/issues/42"


def test_fake_github_issues_get_issue_missing() -> None:
    """Test get_issue raises RuntimeError for missing issue."""
    issues = FakeGitHubIssues()

    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        issues.get_issue(sentinel_path(), 999)


def test_fake_github_issues_get_issue_created() -> None:
    """Test get_issue returns issue that was created via create_issue."""
    issues = FakeGitHubIssues(next_issue_number=10)

    issue_num = issues.create_issue(
        sentinel_path(),
        title="Created Issue",
        body="Created body",
        labels=["test"],
    )

    result = issues.get_issue(sentinel_path(), issue_num)

    assert result.number == 10
    assert result.title == "Created Issue"
    assert result.body == "Created body"
    assert result.state == "OPEN"
    assert result.url == "https://github.com/owner/repo/issues/10"


def test_fake_github_issues_add_comment_existing_issue() -> None:
    """Test add_comment tracks mutation for existing issue."""
    pre_configured = {
        42: IssueInfo(
            number=42,
            title="Test",
            body="Body",
            state="OPEN",
            url="https://github.com/owner/repo/issues/42",
        )
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.add_comment(sentinel_path(), 42, "This is a comment")

    assert issues.added_comments == [(42, "This is a comment")]


def test_fake_github_issues_add_comment_missing_issue() -> None:
    """Test add_comment raises RuntimeError for missing issue."""
    issues = FakeGitHubIssues()

    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        issues.add_comment(sentinel_path(), 999, "Comment body")


def test_fake_github_issues_add_comment_multiple() -> None:
    """Test add_comment tracks multiple comments in order."""
    pre_configured = {
        10: IssueInfo(10, "Issue 10", "Body", "OPEN", "http://url/10"),
        20: IssueInfo(20, "Issue 20", "Body", "OPEN", "http://url/20"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.add_comment(sentinel_path(), 10, "First comment")
    issues.add_comment(sentinel_path(), 20, "Second comment")
    issues.add_comment(sentinel_path(), 10, "Third comment on issue 10")

    assert issues.added_comments == [
        (10, "First comment"),
        (20, "Second comment"),
        (10, "Third comment on issue 10"),
    ]


def test_fake_github_issues_added_comments_empty_initially() -> None:
    """Test added_comments property is empty list initially."""
    issues = FakeGitHubIssues()

    assert issues.added_comments == []


def test_fake_github_issues_added_comments_read_only() -> None:
    """Test added_comments property returns list that can be read."""
    pre_configured = {
        42: IssueInfo(42, "Test", "Body", "OPEN", "http://url"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)
    issues.add_comment(sentinel_path(), 42, "Comment")

    # Should be able to read the list
    comments = issues.added_comments
    assert len(comments) == 1
    assert comments[0] == (42, "Comment")


def test_fake_github_issues_list_issues_empty() -> None:
    """Test list_issues returns empty list when no issues exist."""
    issues = FakeGitHubIssues()

    result = issues.list_issues(sentinel_path())

    assert result == []


def test_fake_github_issues_list_issues_all() -> None:
    """Test list_issues returns all issues when no filters applied."""
    pre_configured = {
        1: IssueInfo(1, "Issue 1", "Body 1", "OPEN", "http://url/1"),
        2: IssueInfo(2, "Issue 2", "Body 2", "CLOSED", "http://url/2"),
        3: IssueInfo(3, "Issue 3", "Body 3", "OPEN", "http://url/3"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    result = issues.list_issues(sentinel_path())

    assert len(result) == 3
    assert result[0].number == 1
    assert result[1].number == 2
    assert result[2].number == 3


def test_fake_github_issues_list_issues_filter_open() -> None:
    """Test list_issues filters by state=open."""
    pre_configured = {
        1: IssueInfo(1, "Issue 1", "Body 1", "OPEN", "http://url/1"),
        2: IssueInfo(2, "Issue 2", "Body 2", "CLOSED", "http://url/2"),
        3: IssueInfo(3, "Issue 3", "Body 3", "OPEN", "http://url/3"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    result = issues.list_issues(sentinel_path(), state="open")

    assert len(result) == 2
    assert result[0].number == 1
    assert result[0].state == "OPEN"
    assert result[1].number == 3
    assert result[1].state == "OPEN"


def test_fake_github_issues_list_issues_filter_closed() -> None:
    """Test list_issues filters by state=closed."""
    pre_configured = {
        1: IssueInfo(1, "Issue 1", "Body 1", "OPEN", "http://url/1"),
        2: IssueInfo(2, "Issue 2", "Body 2", "CLOSED", "http://url/2"),
        3: IssueInfo(3, "Issue 3", "Body 3", "CLOSED", "http://url/3"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    result = issues.list_issues(sentinel_path(), state="closed")

    assert len(result) == 2
    assert result[0].number == 2
    assert result[0].state == "CLOSED"
    assert result[1].number == 3
    assert result[1].state == "CLOSED"


def test_fake_github_issues_list_issues_state_all() -> None:
    """Test list_issues with state=all returns all issues."""
    pre_configured = {
        1: IssueInfo(1, "Issue 1", "Body 1", "OPEN", "http://url/1"),
        2: IssueInfo(2, "Issue 2", "Body 2", "CLOSED", "http://url/2"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    result = issues.list_issues(sentinel_path(), state="all")

    assert len(result) == 2


def test_fake_github_issues_list_issues_includes_created() -> None:
    """Test list_issues includes issues created via create_issue."""
    issues = FakeGitHubIssues(next_issue_number=1)

    issues.create_issue(sentinel_path(), "Created Issue", "Body", ["label"])

    result = issues.list_issues(sentinel_path())

    assert len(result) == 1
    assert result[0].number == 1
    assert result[0].title == "Created Issue"
    assert result[0].state == "OPEN"


def test_fake_github_issues_full_workflow() -> None:
    """Test complete workflow: create, get, comment, list."""
    # Start with one pre-configured issue
    pre_configured = {100: IssueInfo(100, "Existing", "Body", "OPEN", "http://url/100")}
    issues = FakeGitHubIssues(issues=pre_configured, next_issue_number=200)

    # Create new issue
    new_num = issues.create_issue(
        sentinel_path(),
        title="New Issue",
        body="New body",
        labels=["plan", "erk"],
    )
    assert new_num == 200

    # Get created issue
    new_issue = issues.get_issue(sentinel_path(), 200)
    assert new_issue.title == "New Issue"
    assert new_issue.state == "OPEN"

    # Add comments
    issues.add_comment(sentinel_path(), 100, "Comment on existing")
    issues.add_comment(sentinel_path(), 200, "Comment on new")

    # List all issues
    all_issues = issues.list_issues(sentinel_path())
    assert len(all_issues) == 2

    # Verify mutation tracking
    assert issues.created_issues == [("New Issue", "New body", ["plan", "erk"])]
    assert issues.added_comments == [
        (100, "Comment on existing"),
        (200, "Comment on new"),
    ]


def test_fake_github_issues_empty_labels() -> None:
    """Test create_issue with empty labels list."""
    issues = FakeGitHubIssues()

    issue_num = issues.create_issue(sentinel_path(), "Title", "Body", [])

    assert issue_num == 1
    assert issues.created_issues == [("Title", "Body", [])]


def test_fake_github_issues_label_filtering_not_implemented() -> None:
    """Test that label filtering is not implemented (returns all issues).

    This is acceptable for fake - we control the state in tests.
    """
    pre_configured = {
        1: IssueInfo(1, "Issue 1", "Body 1", "OPEN", "http://url/1"),
        2: IssueInfo(2, "Issue 2", "Body 2", "OPEN", "http://url/2"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    # Labels parameter is accepted but ignored in fake
    result = issues.list_issues(sentinel_path(), labels=["nonexistent"])

    # Fake returns all issues (filtering not implemented)
    assert len(result) == 2


def test_fake_github_issues_state_case_sensitivity() -> None:
    """Test state filtering handles uppercase/lowercase properly."""
    pre_configured = {
        1: IssueInfo(1, "Open Issue", "Body", "OPEN", "http://url/1"),
        2: IssueInfo(2, "Closed Issue", "Body", "CLOSED", "http://url/2"),
    }
    issues = FakeGitHubIssues(issues=pre_configured)

    # Lowercase "open" should match uppercase "OPEN" state
    result = issues.list_issues(sentinel_path(), state="open")

    assert len(result) == 1
    assert result[0].state == "OPEN"


def test_fake_github_issues_mutation_tracking_independent() -> None:
    """Test that created_issues and added_comments track independently."""
    issues = FakeGitHubIssues(next_issue_number=1)

    # Create issues
    num1 = issues.create_issue(sentinel_path(), "Issue 1", "Body 1", ["label1"])
    num2 = issues.create_issue(sentinel_path(), "Issue 2", "Body 2", ["label2"])

    # Add comments
    issues.add_comment(sentinel_path(), num1, "Comment 1")
    issues.add_comment(sentinel_path(), num2, "Comment 2")

    # Verify both tracking lists are independent
    assert len(issues.created_issues) == 2
    assert len(issues.added_comments) == 2

    # Verify correct values
    assert issues.created_issues[0][0] == "Issue 1"
    assert issues.created_issues[1][0] == "Issue 2"
    assert issues.added_comments[0] == (1, "Comment 1")
    assert issues.added_comments[1] == (2, "Comment 2")


def test_fake_github_issues_pre_configured_and_created_coexist() -> None:
    """Test that pre-configured and dynamically created issues coexist."""
    pre_configured = {100: IssueInfo(100, "Pre-configured", "Body", "OPEN", "http://url/100")}
    issues = FakeGitHubIssues(issues=pre_configured, next_issue_number=1)

    # Create new issue
    new_num = issues.create_issue(sentinel_path(), "New", "Body", ["label"])

    # Both should be retrievable
    pre_issue = issues.get_issue(sentinel_path(), 100)
    assert pre_issue.title == "Pre-configured"

    new_issue = issues.get_issue(sentinel_path(), new_num)
    assert new_issue.title == "New"

    # List should include both
    all_issues = issues.list_issues(sentinel_path())
    assert len(all_issues) == 2


def test_fake_github_issues_url_generation() -> None:
    """Test that created issues get properly formatted URLs."""
    issues = FakeGitHubIssues(next_issue_number=42)

    issue_num = issues.create_issue(sentinel_path(), "Title", "Body", [])

    created_issue = issues.get_issue(sentinel_path(), issue_num)

    assert created_issue.url == "https://github.com/owner/repo/issues/42"


def test_fake_github_issues_created_state_always_open() -> None:
    """Test that created issues always have OPEN state."""
    issues = FakeGitHubIssues()

    issue_num = issues.create_issue(sentinel_path(), "Title", "Body", [])

    created_issue = issues.get_issue(sentinel_path(), issue_num)

    assert created_issue.state == "OPEN"


def test_fake_github_issues_multiple_comments_same_issue() -> None:
    """Test adding multiple comments to the same issue."""
    pre_configured = {42: IssueInfo(42, "Test", "Body", "OPEN", "http://url/42")}
    issues = FakeGitHubIssues(issues=pre_configured)

    issues.add_comment(sentinel_path(), 42, "Comment 1")
    issues.add_comment(sentinel_path(), 42, "Comment 2")
    issues.add_comment(sentinel_path(), 42, "Comment 3")

    # All comments should be tracked
    assert issues.added_comments == [
        (42, "Comment 1"),
        (42, "Comment 2"),
        (42, "Comment 3"),
    ]
