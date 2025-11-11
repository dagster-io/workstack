"""Tests for FakeGitHubOps test infrastructure.

These tests verify that FakeGitHubOps correctly simulates GitHub operations,
providing reliable test doubles for CLI tests.
"""

from pathlib import Path

import pytest

from tests.fakes.github_ops import FakeGitHubOps
from workstack.core.github_ops import PRInfo, PullRequestInfo


def test_fake_github_ops_initialization() -> None:
    """Test that FakeGitHubOps initializes with empty state."""
    ops = FakeGitHubOps()

    result = ops.get_prs_for_repo(Path("/repo"), include_checks=False)
    assert result == {}


def test_fake_github_ops_get_prs_for_repo() -> None:
    """Test that get_prs_for_repo returns pre-configured PRs."""
    prs = {
        "feature-1": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/repo/pull/123",
            is_draft=False,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        ),
        "feature-2": PullRequestInfo(
            number=456,
            state="MERGED",
            url="https://github.com/repo/pull/456",
            is_draft=False,
            checks_passing=None,
            owner="testowner",
            repo="testrepo",
        ),
    }
    ops = FakeGitHubOps(prs=prs)

    result = ops.get_prs_for_repo(Path("/repo"), include_checks=False)

    assert len(result) == 2
    assert result["feature-1"].number == 123
    assert result["feature-1"].state == "OPEN"
    assert result["feature-2"].number == 456
    assert result["feature-2"].state == "MERGED"


def test_fake_github_ops_get_prs_for_repo_with_checks() -> None:
    """Test that include_checks parameter is accepted (but ignored)."""
    prs = {
        "feature": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/repo/pull/123",
            is_draft=False,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        ),
    }
    ops = FakeGitHubOps(prs=prs)

    # Both calls should return same data regardless of include_checks
    result_without = ops.get_prs_for_repo(Path("/repo"), include_checks=False)
    result_with = ops.get_prs_for_repo(Path("/repo"), include_checks=True)

    assert result_without == result_with
    assert len(result_without) == 1


def test_fake_github_ops_get_pr_status_existing_branch() -> None:
    """Test get_pr_status returns configured PR info for existing branch."""
    prs = {
        "feature": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/repo/pull/123",
            is_draft=False,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        ),
    }
    ops = FakeGitHubOps(prs=prs)

    result = ops.get_pr_status(Path("/repo"), "feature", debug=False)

    assert result.state == "OPEN"
    assert result.pr_number == 123
    assert result.title == "https://github.com/repo/pull/123"  # URL used as title


def test_fake_github_ops_get_pr_status_missing_branch() -> None:
    """Test get_pr_status returns NONE for missing branch."""
    ops = FakeGitHubOps()

    result = ops.get_pr_status(Path("/repo"), "nonexistent", debug=False)

    assert result.state == "NONE"
    assert result.pr_number is None
    assert result.title is None


def test_fake_github_ops_legacy_pr_statuses_format() -> None:
    """Test backward compatibility with legacy pr_statuses parameter."""
    pr_statuses = {
        "feature": ("OPEN", 123, "Add feature"),
        "bugfix": ("MERGED", 456, "Fix bug"),
    }
    ops = FakeGitHubOps(pr_statuses=pr_statuses)

    result_feature = ops.get_pr_status(Path("/repo"), "feature", debug=False)
    assert result_feature.state == "OPEN"
    assert result_feature.pr_number == 123
    assert result_feature.title == "Add feature"

    result_bugfix = ops.get_pr_status(Path("/repo"), "bugfix", debug=False)
    assert result_bugfix.state == "MERGED"
    assert result_bugfix.pr_number == 456
    assert result_bugfix.title == "Fix bug"


def test_fake_github_ops_state_conversion() -> None:
    """Test that None state in legacy format converts to NONE."""
    pr_statuses = {
        "no-pr": (None, None, None),
    }
    ops = FakeGitHubOps(pr_statuses=pr_statuses)

    result = ops.get_pr_status(Path("/repo"), "no-pr", debug=False)

    assert result.state == "NONE"
    assert result.pr_number is None
    assert result.title is None


def test_fake_github_ops_pull_request_info_fields() -> None:
    """Test that PullRequestInfo fields map correctly to PRInfo."""
    prs = {
        "feature": PullRequestInfo(
            number=789,
            state="CLOSED",
            url="https://github.com/repo/pull/789",
            is_draft=False,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        ),
    }
    ops = FakeGitHubOps(prs=prs)

    result = ops.get_pr_status(Path("/repo"), "feature", debug=False)

    # Verify field mapping: PullRequestInfo -> PRInfo
    assert result.state == "CLOSED"
    assert result.pr_number == 789
    assert result.title == "https://github.com/repo/pull/789"


def test_fake_github_ops_empty_prs_dict() -> None:
    """Test behavior with explicitly empty prs dict."""
    ops = FakeGitHubOps(prs={})

    result = ops.get_prs_for_repo(Path("/repo"), include_checks=False)
    assert result == {}

    pr_status = ops.get_pr_status(Path("/repo"), "any-branch", debug=False)
    assert pr_status == PRInfo("NONE", None, None)


def test_fake_github_ops_both_formats_raises() -> None:
    """Test that specifying both prs and pr_statuses raises ValueError."""
    prs = {
        "feature": PullRequestInfo(
            number=1,
            state="OPEN",
            url="http://url",
            is_draft=False,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        )
    }
    pr_statuses = {"feature": ("OPEN", 1, "Title")}

    with pytest.raises(ValueError, match="Cannot specify both prs and pr_statuses"):
        FakeGitHubOps(prs=prs, pr_statuses=pr_statuses)


def test_fake_github_ops_get_pr_base_branch_existing() -> None:
    """Test get_pr_base_branch returns configured base for existing PR."""
    pr_bases = {
        123: "main",
        456: "develop",
    }
    ops = FakeGitHubOps(pr_bases=pr_bases)

    result = ops.get_pr_base_branch(Path("/repo"), 123)

    assert result == "main"


def test_fake_github_ops_get_pr_base_branch_missing() -> None:
    """Test get_pr_base_branch returns None for missing PR."""
    ops = FakeGitHubOps()

    result = ops.get_pr_base_branch(Path("/repo"), 999)

    assert result is None


def test_fake_github_ops_get_pr_base_branch_empty_dict() -> None:
    """Test get_pr_base_branch with explicitly empty pr_bases dict."""
    ops = FakeGitHubOps(pr_bases={})

    result = ops.get_pr_base_branch(Path("/repo"), 123)

    assert result is None


def test_fake_github_ops_update_pr_base_branch_single() -> None:
    """Test update_pr_base_branch tracks single update."""
    ops = FakeGitHubOps()

    ops.update_pr_base_branch(Path("/repo"), 123, "main")

    assert ops.updated_pr_bases == [(123, "main")]


def test_fake_github_ops_update_pr_base_branch_multiple() -> None:
    """Test update_pr_base_branch tracks multiple updates in order."""
    ops = FakeGitHubOps()

    ops.update_pr_base_branch(Path("/repo"), 123, "main")
    ops.update_pr_base_branch(Path("/repo"), 456, "develop")
    ops.update_pr_base_branch(Path("/repo"), 789, "feature-1")

    assert ops.updated_pr_bases == [
        (123, "main"),
        (456, "develop"),
        (789, "feature-1"),
    ]


def test_fake_github_ops_update_pr_base_branch_same_pr_twice() -> None:
    """Test update_pr_base_branch tracks same PR updated multiple times."""
    ops = FakeGitHubOps()

    ops.update_pr_base_branch(Path("/repo"), 123, "main")
    ops.update_pr_base_branch(Path("/repo"), 123, "develop")

    # Both updates should be tracked
    assert ops.updated_pr_bases == [
        (123, "main"),
        (123, "develop"),
    ]


def test_fake_github_ops_updated_pr_bases_empty_initially() -> None:
    """Test updated_pr_bases property is empty list initially."""
    ops = FakeGitHubOps()

    assert ops.updated_pr_bases == []


def test_fake_github_ops_updated_pr_bases_read_only() -> None:
    """Test updated_pr_bases property returns list that can be read."""
    ops = FakeGitHubOps()
    ops.update_pr_base_branch(Path("/repo"), 123, "main")

    # Should be able to read the list
    updates = ops.updated_pr_bases
    assert len(updates) == 1
    assert updates[0] == (123, "main")


def test_fake_github_ops_update_does_not_affect_get() -> None:
    """Test update_pr_base_branch does not modify configured pr_bases."""
    pr_bases = {123: "original-base"}
    ops = FakeGitHubOps(pr_bases=pr_bases)

    # Update should only track mutation, not modify configured state
    ops.update_pr_base_branch(Path("/repo"), 123, "new-base")

    # get_pr_base_branch should still return original configured value
    assert ops.get_pr_base_branch(Path("/repo"), 123) == "original-base"
    # But update should be tracked
    assert ops.updated_pr_bases == [(123, "new-base")]


def test_fake_github_ops_full_workflow() -> None:
    """Test complete workflow: configure state, query, and track mutations."""
    # Configure initial state
    prs = {
        "feature-1": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/repo/pull/123",
            is_draft=False,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        ),
        "feature-2": PullRequestInfo(
            number=456,
            state="OPEN",
            url="https://github.com/repo/pull/456",
            is_draft=False,
            checks_passing=True,
            owner="testowner",
            repo="testrepo",
        ),
    }
    pr_bases = {
        123: "main",
        456: "feature-1",
    }
    ops = FakeGitHubOps(prs=prs, pr_bases=pr_bases)

    # Query operations
    all_prs = ops.get_prs_for_repo(Path("/repo"), include_checks=False)
    assert len(all_prs) == 2

    pr_status = ops.get_pr_status(Path("/repo"), "feature-1", debug=False)
    assert pr_status.pr_number == 123

    base = ops.get_pr_base_branch(Path("/repo"), 123)
    assert base == "main"

    # Mutation tracking
    ops.update_pr_base_branch(Path("/repo"), 456, "main")
    ops.update_pr_base_branch(Path("/repo"), 123, "develop")

    # Verify mutations tracked
    assert ops.updated_pr_bases == [(456, "main"), (123, "develop")]

    # Verify configured state unchanged
    assert ops.get_pr_base_branch(Path("/repo"), 123) == "main"
    assert ops.get_pr_base_branch(Path("/repo"), 456) == "feature-1"
