"""Unit tests for GitHub parsing functions with JSON fixtures."""

from erk.core.github.parsing import (
    _determine_checks_status,
    parse_github_pr_list,
    parse_github_pr_status,
)
from tests.conftest import load_fixture


def test_parse_github_pr_list_with_checks():
    """Test parsing PR list with CI check status."""
    json_data = load_fixture("github/pr_list_with_checks.json")
    result = parse_github_pr_list(json_data, include_checks=True)

    assert len(result) == 3

    # Check feature branch with passing checks
    assert "feature-branch" in result
    feature = result["feature-branch"]
    assert feature.number == 123
    assert feature.state == "OPEN"
    assert feature.url == "https://github.com/dagster-io/erk/pull/123"
    assert feature.is_draft is False
    assert feature.checks_passing is True
    assert feature.owner == "dagster-io"
    assert feature.repo == "erk"

    # Check bugfix branch with failing checks
    assert "bugfix-branch" in result
    bugfix = result["bugfix-branch"]
    assert bugfix.number == 124
    assert bugfix.checks_passing is False

    # Check pending branch with in-progress checks
    assert "pending-branch" in result
    pending = result["pending-branch"]
    assert pending.number == 125
    assert pending.is_draft is True
    assert pending.checks_passing is False  # In-progress treated as failing


def test_parse_github_pr_list_without_checks():
    """Test parsing PR list without check status."""
    json_data = load_fixture("github/pr_list_no_checks.json")
    result = parse_github_pr_list(json_data, include_checks=False)

    assert len(result) == 2

    # Check main feature - merged PR
    assert "main-feature" in result
    main_feature = result["main-feature"]
    assert main_feature.number == 201
    assert main_feature.state == "MERGED"
    assert main_feature.is_draft is False
    assert main_feature.checks_passing is None  # Not included

    # Check test branch - closed PR
    assert "test-branch" in result
    test = result["test-branch"]
    assert test.number == 202
    assert test.state == "CLOSED"
    assert test.is_draft is True
    assert test.checks_passing is None


def test_parse_github_pr_list_empty():
    """Test parsing empty PR list."""
    result = parse_github_pr_list("[]", include_checks=False)
    assert result == {}


def test_parse_github_pr_list_malformed_url():
    """Test parsing PR with malformed URL (should skip)."""
    json_str = """[
        {
            "number": 999,
            "headRefName": "bad-url-branch",
            "url": "https://not-github.com/something",
            "state": "OPEN",
            "isDraft": false
        }
    ]"""
    result = parse_github_pr_list(json_str, include_checks=False)
    # Should skip PRs with malformed URLs
    assert len(result) == 0


def test_parse_github_pr_status_single():
    """Test parsing single PR status."""
    json_data = load_fixture("github/pr_status_single.json")
    state, number, title = parse_github_pr_status(json_data)

    assert state == "OPEN"
    assert number == 456
    assert title == "Add new feature for improved performance"


def test_parse_github_pr_status_no_pr():
    """Test parsing status when no PR exists."""
    state, number, title = parse_github_pr_status("[]")

    assert state == "NONE"
    assert number is None
    assert title is None


def test_determine_checks_status_all_passing():
    """Test check status when all checks pass."""
    check_rollup = [
        {"status": "COMPLETED", "conclusion": "SUCCESS"},
        {"status": "COMPLETED", "conclusion": "SKIPPED"},
        {"status": "COMPLETED", "conclusion": "NEUTRAL"},
    ]
    result = _determine_checks_status(check_rollup)
    assert result is True


def test_determine_checks_status_some_failing():
    """Test check status when some checks fail."""
    check_rollup = [
        {"status": "COMPLETED", "conclusion": "SUCCESS"},
        {"status": "COMPLETED", "conclusion": "FAILURE"},
    ]
    result = _determine_checks_status(check_rollup)
    assert result is False


def test_determine_checks_status_in_progress():
    """Test check status when checks are in progress."""
    check_rollup = [
        {"status": "IN_PROGRESS"},
        {"status": "COMPLETED", "conclusion": "SUCCESS"},
    ]
    result = _determine_checks_status(check_rollup)
    assert result is False


def test_determine_checks_status_no_checks():
    """Test check status with no checks configured."""
    result = _determine_checks_status([])
    assert result is None
