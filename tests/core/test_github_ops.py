"""Tests for GitHub operations batched CI status and mergeability fetching."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from erk.core.github_ops import PullRequestInfo, RealGitHubOps


@pytest.fixture
def mock_execute():
    """Create a mock execute function for testing."""
    return Mock()


@pytest.fixture
def github_ops(mock_execute):
    """Create RealGitHubOps instance with mocked executor."""
    return RealGitHubOps(execute_fn=mock_execute)


@pytest.fixture
def sample_prs():
    """Sample PRs for testing."""
    return {
        "feature-1": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            checks_passing=None,
            owner="owner",
            repo="repo",
            has_conflicts=None,
        ),
        "feature-2": PullRequestInfo(
            number=456,
            state="OPEN",
            url="https://github.com/owner/repo/pull/456",
            is_draft=False,
            checks_passing=None,
            owner="owner",
            repo="repo",
            has_conflicts=None,
        ),
    }


def test_enrich_prs_with_ci_status_batch_includes_mergeability(
    github_ops, mock_execute, sample_prs
):
    """Test CI batch method also enriches mergeability."""
    # Mock GraphQL response with both CI status and mergeability data
    mock_execute.return_value = """{
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                    "commits": {
                        "nodes": []
                    }
                },
                "pr_456": {
                    "number": 456,
                    "mergeable": "CONFLICTING",
                    "mergeStateStatus": "DIRTY",
                    "commits": {
                        "nodes": []
                    }
                }
            }
        }
    }"""

    repo_root = Path("/test/repo")
    result = github_ops.enrich_prs_with_ci_status_batch(sample_prs, repo_root)

    # Verify PRs were enriched with mergeability
    assert result["feature-1"].has_conflicts is False  # MERGEABLE
    assert result["feature-2"].has_conflicts is True  # CONFLICTING

    # Verify other fields unchanged
    assert result["feature-1"].number == 123
    assert result["feature-2"].number == 456


def test_enrich_prs_with_ci_status_batch_empty(github_ops, mock_execute):
    """Test empty input returns empty dict without API call."""
    result = github_ops.enrich_prs_with_ci_status_batch({}, Path("/test/repo"))

    # Verify no API call made
    mock_execute.assert_not_called()

    # Verify empty dict returned
    assert result == {}


def test_enrich_prs_with_ci_status_batch_partial_failure(github_ops, mock_execute, sample_prs):
    """Test partial failures don't break entire batch."""
    # Mock response with one PR missing
    mock_execute.return_value = """{
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                    "commits": {
                        "nodes": []
                    }
                },
                "pr_456": null
            }
        }
    }"""

    repo_root = Path("/test/repo")
    result = github_ops.enrich_prs_with_ci_status_batch(sample_prs, repo_root)

    # Verify successful PR got mergeability
    assert result["feature-1"].has_conflicts is False

    # Verify failed PR has has_conflicts=None
    assert result["feature-2"].has_conflicts is None


def test_enrich_prs_with_ci_status_batch_unknown_mergeability(github_ops, mock_execute, sample_prs):
    """Test UNKNOWN mergeability state handled correctly."""
    # Mock response with UNKNOWN state
    mock_execute.return_value = """{
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "mergeable": "UNKNOWN",
                    "mergeStateStatus": "UNKNOWN",
                    "commits": {
                        "nodes": []
                    }
                },
                "pr_456": {
                    "number": 456,
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                    "commits": {
                        "nodes": []
                    }
                }
            }
        }
    }"""

    repo_root = Path("/test/repo")
    result = github_ops.enrich_prs_with_ci_status_batch(sample_prs, repo_root)

    # Verify UNKNOWN state returns None (not True or False)
    assert result["feature-1"].has_conflicts is None

    # Verify other PR works correctly
    assert result["feature-2"].has_conflicts is False


def test_enrich_prs_with_ci_status_batch_missing_mergeable_field(
    github_ops, mock_execute, sample_prs
):
    """Test missing mergeable field handled gracefully."""
    # Mock response with missing mergeable field
    mock_execute.return_value = """{
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "mergeStateStatus": "CLEAN",
                    "commits": {
                        "nodes": []
                    }
                },
                "pr_456": {
                    "number": 456,
                    "mergeable": "MERGEABLE",
                    "mergeStateStatus": "CLEAN",
                    "commits": {
                        "nodes": []
                    }
                }
            }
        }
    }"""

    repo_root = Path("/test/repo")
    result = github_ops.enrich_prs_with_ci_status_batch(sample_prs, repo_root)

    # Verify missing field returns None
    assert result["feature-1"].has_conflicts is None

    # Verify other PR works correctly
    assert result["feature-2"].has_conflicts is False


def test_build_batch_pr_query_includes_mergeability(github_ops):
    """Test GraphQL query builder includes mergeability fields."""
    pr_numbers = [123, 456]
    owner = "test-owner"
    repo = "test-repo"

    query = github_ops._build_batch_pr_query(pr_numbers, owner, repo)

    # Verify query contains fragment definition with both CI and mergeability fields
    assert "fragment PRCICheckFields on PullRequest" in query
    assert "mergeable" in query
    assert "mergeStateStatus" in query
    assert "statusCheckRollup" in query

    # Verify query contains aliased PR queries
    assert "pr_123: pullRequest(number: 123)" in query
    assert "pr_456: pullRequest(number: 456)" in query

    # Verify query contains fragment spreads
    assert "...PRCICheckFields" in query

    # Verify repository query
    assert f'repository(owner: "{owner}", name: "{repo}")' in query


def test_parse_pr_mergeability_conflicting(github_ops):
    """Test parsing CONFLICTING mergeability status."""
    pr_data = {"mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}
    result = github_ops._parse_pr_mergeability(pr_data)
    assert result is True


def test_parse_pr_mergeability_mergeable(github_ops):
    """Test parsing MERGEABLE mergeability status."""
    pr_data = {"mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN"}
    result = github_ops._parse_pr_mergeability(pr_data)
    assert result is False


def test_parse_pr_mergeability_unknown(github_ops):
    """Test parsing UNKNOWN mergeability status."""
    pr_data = {"mergeable": "UNKNOWN", "mergeStateStatus": "UNKNOWN"}
    result = github_ops._parse_pr_mergeability(pr_data)
    assert result is None


def test_parse_pr_mergeability_none_input(github_ops):
    """Test parsing None input."""
    result = github_ops._parse_pr_mergeability(None)
    assert result is None


def test_parse_pr_mergeability_missing_field(github_ops):
    """Test parsing data with missing mergeable field."""
    pr_data = {"mergeStateStatus": "CLEAN"}
    result = github_ops._parse_pr_mergeability(pr_data)
    assert result is None
