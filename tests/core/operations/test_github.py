"""Tests for GitHub operations."""

import pytest
from erk_shared.github.parsing import _parse_github_pr_url
from erk_shared.integrations.time.fake import FakeTime

from erk.core.github.real import RealGitHub


def test_parse_github_pr_url_valid_urls() -> None:
    """Test parsing of valid GitHub PR URLs."""
    # Standard format
    result = _parse_github_pr_url("https://github.com/dagster-io/erk/pull/23")
    assert result == ("dagster-io", "erk")

    # Different owner/repo names
    result = _parse_github_pr_url("https://github.com/facebook/react/pull/12345")
    assert result == ("facebook", "react")

    # Single character names
    result = _parse_github_pr_url("https://github.com/a/b/pull/1")
    assert result == ("a", "b")

    # Names with hyphens
    result = _parse_github_pr_url("https://github.com/my-org/my-repo/pull/456")
    assert result == ("my-org", "my-repo")

    # Names with underscores
    result = _parse_github_pr_url("https://github.com/my_org/my_repo/pull/789")
    assert result == ("my_org", "my_repo")

    # Repo names with dots (valid in GitHub)
    result = _parse_github_pr_url("https://github.com/owner/repo.name/pull/100")
    assert result == ("owner", "repo.name")


def test_parse_github_pr_url_invalid_urls() -> None:
    """Test that invalid URLs return None."""
    # Not a GitHub URL
    assert _parse_github_pr_url("https://gitlab.com/owner/repo/pull/123") is None

    # Missing pull number
    assert _parse_github_pr_url("https://github.com/owner/repo/pull/") is None

    # Wrong path structure
    assert _parse_github_pr_url("https://github.com/owner/repo/issues/123") is None

    # Not a URL
    assert _parse_github_pr_url("not a url") is None

    # Empty string
    assert _parse_github_pr_url("") is None

    # Missing repo
    assert _parse_github_pr_url("https://github.com/owner/pull/123") is None


def test_parse_github_pr_url_edge_cases() -> None:
    """Test edge cases in URL parsing.

    Note: The regex is intentionally permissive about trailing content (query params,
    fragments, extra path segments) since it only needs to extract owner/repo from
    GitHub PR URLs returned by gh CLI, which are well-formed.
    """
    # PR number with leading zeros (valid)
    result = _parse_github_pr_url("https://github.com/owner/repo/pull/007")
    assert result == ("owner", "repo")

    # Very long PR number
    result = _parse_github_pr_url("https://github.com/owner/repo/pull/999999999")
    assert result == ("owner", "repo")

    # URL with query parameters (accepted - regex is permissive)
    result = _parse_github_pr_url("https://github.com/owner/repo/pull/123?tab=files")
    assert result == ("owner", "repo")

    # URL with fragment (accepted - regex is permissive)
    result = _parse_github_pr_url("https://github.com/owner/repo/pull/123#discussion")
    assert result == ("owner", "repo")

    # URL with extra path segments (accepted - regex is permissive)
    result = _parse_github_pr_url("https://github.com/owner/repo/pull/123/files")
    assert result == ("owner", "repo")


def test_build_batch_pr_query_has_contexts_nodes_wrapper() -> None:
    """Test that contexts field has nodes wrapper in fragment definition (regression test for bug).

    This is a regression test for a bug where the GraphQL query was missing the
    'nodes' wrapper around the inline fragments in the contexts field. The contexts
    field returns a connection object (StatusCheckRollupContextConnection), not a
    direct array, so inline fragments must be applied to nodes, not the connection.

    The bug was:
        contexts(last: 100) {
          ... on StatusContext { ... }  # WRONG - can't spread on connection
        }

    The fix is:
        contexts(last: 100) {
          nodes {  # CORRECT - spread on nodes
            ... on StatusContext { ... }
          }
        }
    """
    ops = RealGitHub(FakeTime())

    query = ops._build_batch_pr_query([123], "owner", "repo")

    # Critical: contexts must have nodes wrapper (in the fragment definition)
    assert "contexts(last: 100) {" in query
    assert "nodes {" in query

    # Verify the structure order in the fragment: contexts -> nodes -> fragments
    # This ensures nodes comes between contexts and the inline fragments
    fragment_start = query.index("fragment PRCICheckFields")
    contexts_idx = query.index("contexts(last: 100)", fragment_start)
    nodes_idx = query.index("nodes {", contexts_idx)
    status_context_idx = query.index("... on StatusContext", nodes_idx)

    # Ensure proper nesting order
    assert contexts_idx < nodes_idx < status_context_idx


def test_build_batch_pr_query_structure() -> None:
    """Test that GraphQL query has correct overall structure with named fragments."""
    ops = RealGitHub(FakeTime())

    query = ops._build_batch_pr_query([123, 456], "test-owner", "test-repo")

    # Validate fragment definition is present
    assert "fragment PRCICheckFields on PullRequest {" in query

    # Validate basic GraphQL syntax
    assert "query {" in query
    assert 'repository(owner: "test-owner", name: "test-repo")' in query

    # Validate PR aliases are present with fragment spread
    assert "pr_123: pullRequest(number: 123) {" in query
    assert "pr_456: pullRequest(number: 456) {" in query
    assert "...PRCICheckFields" in query

    # Validate required fields are in the fragment definition (only once)
    assert query.count("commits(last: 1)") == 1  # Only in fragment definition
    assert query.count("statusCheckRollup") == 1  # Only in fragment definition

    # Validate inline fragments for both types (in the fragment definition)
    assert "... on StatusContext {" in query
    assert "... on CheckRun {" in query

    # Validate fields within fragments
    assert "status" in query  # CheckRun field
    assert "conclusion" in query  # Both StatusContext and CheckRun
    assert "state" in query  # StatusContext and statusCheckRollup

    # Validate fragment spread is used for each PR
    assert query.count("...PRCICheckFields") == 2  # One for each PR


def test_build_batch_pr_query_multiple_prs() -> None:
    """Test that query correctly handles multiple PRs with unique aliases and fragments."""
    ops = RealGitHub(FakeTime())

    pr_numbers = [100, 200, 300]
    query = ops._build_batch_pr_query(pr_numbers, "owner", "repo")

    # Each PR should have a unique alias
    for pr_num in pr_numbers:
        alias = f"pr_{pr_num}: pullRequest(number: {pr_num})"
        assert alias in query

    # Verify all PRs are in the same repository query
    assert query.count('repository(owner: "owner", name: "repo")') == 1

    # With fragments, the structure is defined once in the fragment definition
    assert query.count("commits(last: 1)") == 1  # Only in fragment definition
    assert query.count("statusCheckRollup") == 1  # Only in fragment definition

    # Each PR should use the fragment spread
    assert query.count("...PRCICheckFields") == len(pr_numbers)


def test_parse_pr_ci_status_handles_missing_nodes() -> None:
    """Test that parser handles missing nodes field gracefully.

    This tests that the parser correctly handles the case where the contexts
    field is present but doesn't have a nodes wrapper (e.g., if the query
    structure is incorrect or the API response format changes).
    """
    ops = RealGitHub(FakeTime())

    # Simulate response with contexts but no nodes wrapper (old buggy structure)
    buggy_response = {
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "statusCheckRollup": {
                            "contexts": [  # Direct array, no nodes wrapper
                                {"status": "COMPLETED", "conclusion": "SUCCESS"}
                            ]
                        }
                    }
                }
            ]
        }
    }

    # Parser should handle this gracefully and return None
    # (since it expects contexts.nodes, not contexts as direct array)
    result = ops._parse_pr_ci_status(buggy_response)
    assert result is None


def test_parse_pr_ci_status_with_correct_structure() -> None:
    """Test that parser correctly handles the expected GraphQL response structure."""
    ops = RealGitHub(FakeTime())

    # Simulate correct response structure with contexts.nodes wrapper
    correct_response = {
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "statusCheckRollup": {
                            "contexts": {
                                "nodes": [
                                    {"status": "COMPLETED", "conclusion": "SUCCESS"},
                                    {"status": "COMPLETED", "conclusion": "SUCCESS"},
                                ]
                            }
                        }
                    }
                }
            ]
        }
    }

    # Parser should successfully extract and parse CI status
    result = ops._parse_pr_ci_status(correct_response)
    assert result is True  # All checks passing


def test_parse_pr_ci_status_with_failing_checks() -> None:
    """Test that parser correctly identifies failing checks."""
    ops = RealGitHub(FakeTime())

    response = {
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "statusCheckRollup": {
                            "contexts": {
                                "nodes": [
                                    {"status": "COMPLETED", "conclusion": "SUCCESS"},
                                    {"status": "COMPLETED", "conclusion": "FAILURE"},
                                ]
                            }
                        }
                    }
                }
            ]
        }
    }

    # Parser should detect failing check
    result = ops._parse_pr_ci_status(response)
    assert result is False


def test_parse_pr_ci_status_with_pending_checks() -> None:
    """Test that parser correctly identifies pending/in-progress checks."""
    ops = RealGitHub(FakeTime())

    response = {
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "statusCheckRollup": {
                            "contexts": {
                                "nodes": [
                                    {"status": "IN_PROGRESS", "conclusion": None},
                                ]
                            }
                        }
                    }
                }
            ]
        }
    }

    # Parser should detect incomplete check
    result = ops._parse_pr_ci_status(response)
    assert result is False


def test_build_title_batch_query_structure() -> None:
    """Test that title query has correct structure with only number and title fields."""
    ops = RealGitHub(FakeTime())

    query = ops._build_title_batch_query([123, 456], "test-owner", "test-repo")

    # Validate basic GraphQL syntax
    assert "query {" in query
    assert 'repository(owner: "test-owner", name: "test-repo")' in query

    # Validate PR aliases are present
    assert "pr_123: pullRequest(number: 123) {" in query
    assert "pr_456: pullRequest(number: 456) {" in query

    # Validate required fields (number and title only)
    assert "number" in query
    assert "title" in query

    # Verify query does NOT include CI fields
    assert "statusCheckRollup" not in query
    assert "mergeable" not in query
    assert "mergeStateStatus" not in query
    assert "commits(last: 1)" not in query
    assert "contexts" not in query


def test_fetch_pr_titles_batch_enriches_titles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fetch_pr_titles_batch enriches PRs with titles from GraphQL response."""
    ops = RealGitHub(FakeTime())

    # Create input PRs without titles
    from pathlib import Path

    from erk_shared.github.types import PullRequestInfo

    prs = {
        "feature-1": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/test-owner/test-repo/pull/123",
            is_draft=False,
            title=None,  # No title initially
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
        ),
        "feature-2": PullRequestInfo(
            number=456,
            state="OPEN",
            url="https://github.com/test-owner/test-repo/pull/456",
            is_draft=False,
            title=None,  # No title initially
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
        ),
    }

    # Mock GraphQL response with titles
    mock_response = {
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "title": "Add new feature",
                },
                "pr_456": {
                    "number": 456,
                    "title": "Fix bug",
                },
            }
        }
    }

    # Mock _execute_batch_pr_query to return our response
    monkeypatch.setattr(ops, "_execute_batch_pr_query", lambda query, repo_root: mock_response)

    # Execute
    result = ops.fetch_pr_titles_batch(prs, Path("/repo"))

    # Verify PRs are enriched with titles
    assert result["feature-1"].title == "Add new feature"
    assert result["feature-2"].title == "Fix bug"
    # Verify other fields are preserved
    assert result["feature-1"].number == 123
    assert result["feature-2"].number == 456


def test_fetch_pr_titles_batch_empty_input() -> None:
    """Test fetch_pr_titles_batch returns empty dict for empty input."""
    ops = RealGitHub(FakeTime())

    from pathlib import Path

    # Call with empty dict
    result = ops.fetch_pr_titles_batch({}, Path("/repo"))

    # Should return empty dict immediately without API call
    assert result == {}


def test_fetch_pr_titles_batch_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fetch_pr_titles_batch handles partial failures gracefully."""
    ops = RealGitHub(FakeTime())

    from pathlib import Path

    from erk_shared.github.types import PullRequestInfo

    # Create input PRs
    prs = {
        "feature-1": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/test-owner/test-repo/pull/123",
            is_draft=False,
            title=None,
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
        ),
        "feature-2": PullRequestInfo(
            number=456,
            state="OPEN",
            url="https://github.com/test-owner/test-repo/pull/456",
            is_draft=False,
            title=None,
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
        ),
    }

    # Mock GraphQL response with one PR present, one missing (None)
    mock_response = {
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    "title": "Add new feature",
                },
                "pr_456": None,  # PR not found or error
            }
        }
    }

    monkeypatch.setattr(ops, "_execute_batch_pr_query", lambda query, repo_root: mock_response)

    result = ops.fetch_pr_titles_batch(prs, Path("/repo"))

    # Successful PR should have title
    assert result["feature-1"].title == "Add new feature"
    # Failed PR should have None title
    assert result["feature-2"].title is None


def test_fetch_pr_titles_batch_missing_title_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test fetch_pr_titles_batch handles missing title field gracefully."""
    ops = RealGitHub(FakeTime())

    from pathlib import Path

    from erk_shared.github.types import PullRequestInfo

    # Create input PR
    prs = {
        "feature": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/test-owner/test-repo/pull/123",
            is_draft=False,
            title=None,
            checks_passing=None,
            owner="test-owner",
            repo="test-repo",
        ),
    }

    # Mock GraphQL response with PR data but missing title field
    mock_response = {
        "data": {
            "repository": {
                "pr_123": {
                    "number": 123,
                    # title field is missing
                },
            }
        }
    }

    monkeypatch.setattr(ops, "_execute_batch_pr_query", lambda query, repo_root: mock_response)

    result = ops.fetch_pr_titles_batch(prs, Path("/repo"))

    # Should handle missing field gracefully and set title=None
    assert result["feature"].title is None
    assert result["feature"].number == 123


def test_build_issue_pr_linkage_query_structure() -> None:
    """Test that issue-PR linkage query has correct structure with closingIssuesReferences."""
    ops = RealGitHub(FakeTime())

    query = ops._build_issue_pr_linkage_query([100, 200], "test-owner", "test-repo")

    # Validate basic GraphQL syntax
    assert "query {" in query
    assert 'repository(owner: "test-owner", name: "test-repo")' in query

    # Validate we're querying PRs with closingIssuesReferences (not issues with timeline)
    assert "pullRequests(" in query
    assert "closingIssuesReferences(" in query
    assert "timelineItems" not in query  # Old approach
    assert "CONNECTED_EVENT" not in query  # Old approach

    # Validate required PR fields
    assert "number" in query
    assert "state" in query
    assert "url" in query
    assert "isDraft" in query
    assert "title" in query
    assert "createdAt" in query
    assert "statusCheckRollup" in query
    assert "mergeable" in query

    # Validate closingIssuesReferences structure
    assert "closingIssuesReferences(first: 100)" in query
    assert "nodes {" in query  # Must have nodes wrapper for connection type


def test_parse_issue_pr_linkages_with_single_pr() -> None:
    """Test parsing GraphQL response with single PR linking to an issue."""
    ops = RealGitHub(FakeTime())

    # Mock response with PR linking to issue 100
    response = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 200,
                            "state": "OPEN",
                            "url": "https://github.com/owner/repo/pull/200",
                            "isDraft": False,
                            "title": "Fix bug",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "statusCheckRollup": {"state": "SUCCESS"},
                            "mergeable": "MERGEABLE",
                            "closingIssuesReferences": {"nodes": [{"number": 100}]},
                        }
                    ]
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should have one issue with one PR
    assert 100 in result
    assert len(result[100]) == 1

    pr = result[100][0]
    assert pr.number == 200
    assert pr.state == "OPEN"
    assert pr.url == "https://github.com/owner/repo/pull/200"
    assert pr.is_draft is False
    assert pr.title == "Fix bug"
    assert pr.checks_passing is True
    assert pr.has_conflicts is False


def test_parse_issue_pr_linkages_with_multiple_prs() -> None:
    """Test parsing response with multiple PRs linking to same issue."""
    ops = RealGitHub(FakeTime())

    # Mock response with two PRs linking to issue 100
    response = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 201,
                            "state": "OPEN",
                            "url": "https://github.com/owner/repo/pull/201",
                            "isDraft": False,
                            "title": "Recent PR",
                            "createdAt": "2024-01-02T00:00:00Z",
                            "statusCheckRollup": None,
                            "mergeable": "UNKNOWN",
                            "closingIssuesReferences": {"nodes": [{"number": 100}]},
                        },
                        {
                            "number": 200,
                            "state": "CLOSED",
                            "url": "https://github.com/owner/repo/pull/200",
                            "isDraft": False,
                            "title": "Older PR",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "statusCheckRollup": {"state": "FAILURE"},
                            "mergeable": "MERGEABLE",
                            "closingIssuesReferences": {"nodes": [{"number": 100}]},
                        },
                    ]
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should have one issue with two PRs, sorted by created_at descending
    assert 100 in result
    assert len(result[100]) == 2

    # Most recent PR should be first
    assert result[100][0].number == 201
    assert result[100][0].title == "Recent PR"

    # Older PR should be second
    assert result[100][1].number == 200
    assert result[100][1].title == "Older PR"


def test_parse_issue_pr_linkages_with_pr_linking_multiple_issues() -> None:
    """Test parsing response where single PR links to multiple issues."""
    ops = RealGitHub(FakeTime())

    # Mock response with one PR linking to issues 100 and 101
    response = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 200,
                            "state": "OPEN",
                            "url": "https://github.com/owner/repo/pull/200",
                            "isDraft": False,
                            "title": "Fix multiple bugs",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "statusCheckRollup": {"state": "SUCCESS"},
                            "mergeable": "MERGEABLE",
                            "closingIssuesReferences": {
                                "nodes": [
                                    {"number": 100},
                                    {"number": 101},
                                ]
                            },
                        }
                    ]
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should have two issues, each with the same PR
    assert 100 in result
    assert 101 in result
    assert len(result[100]) == 1
    assert len(result[101]) == 1

    # Both should point to same PR
    assert result[100][0].number == 200
    assert result[101][0].number == 200


def test_parse_issue_pr_linkages_handles_empty_closing_references() -> None:
    """Test parsing handles PRs with no closingIssuesReferences."""
    ops = RealGitHub(FakeTime())

    # Mock response with PR that doesn't close any issues
    response = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 200,
                            "state": "OPEN",
                            "url": "https://github.com/owner/repo/pull/200",
                            "isDraft": True,
                            "title": "WIP PR",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "statusCheckRollup": None,
                            "mergeable": "MERGEABLE",
                            "closingIssuesReferences": {
                                "nodes": []  # Empty - no issues linked
                            },
                        }
                    ]
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should return empty dict since no issues are linked
    assert result == {}


def test_parse_issue_pr_linkages_handles_null_nodes() -> None:
    """Test parsing handles null values in nodes arrays gracefully."""
    ops = RealGitHub(FakeTime())

    # Mock response with null PR node and null issue node
    response = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        None,  # Null PR node
                        {
                            "number": 200,
                            "state": "OPEN",
                            "url": "https://github.com/owner/repo/pull/200",
                            "isDraft": False,
                            "title": "Valid PR",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "statusCheckRollup": None,
                            "mergeable": "MERGEABLE",
                            "closingIssuesReferences": {
                                "nodes": [
                                    None,  # Null issue node
                                    {"number": 100},
                                ]
                            },
                        },
                    ]
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should skip null nodes and process valid ones
    assert 100 in result
    assert len(result[100]) == 1
    assert result[100][0].number == 200


def test_parse_issue_pr_linkages_handles_missing_optional_fields() -> None:
    """Test parsing handles missing optional fields (checks, conflicts)."""
    ops = RealGitHub(FakeTime())

    # Mock response with minimal fields
    response = {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": [
                        {
                            "number": 200,
                            "state": "MERGED",
                            "url": "https://github.com/owner/repo/pull/200",
                            "isDraft": None,  # Missing
                            "title": None,  # Missing
                            "createdAt": "2024-01-01T00:00:00Z",
                            "statusCheckRollup": None,  # No checks
                            "mergeable": None,  # Unknown
                            "closingIssuesReferences": {"nodes": [{"number": 100}]},
                        }
                    ]
                }
            }
        }
    }

    result = ops._parse_issue_pr_linkages(response, "owner", "repo")

    # Should handle missing fields gracefully
    assert 100 in result
    pr = result[100][0]
    assert pr.number == 200
    assert pr.is_draft is False  # Defaults to False
    assert pr.title is None
    assert pr.checks_passing is None
    assert pr.has_conflicts is None
