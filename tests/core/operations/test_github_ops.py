"""Tests for GitHub operations."""

from erk.core.github_ops import RealGitHubOps, _parse_github_pr_url


def test_parse_github_pr_url_valid_urls() -> None:
    """Test parsing of valid GitHub PR URLs."""
    # Standard format
    result = _parse_github_pr_url("https://github.com/dagster-io/workstack/pull/23")
    assert result == ("dagster-io", "workstack")

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
    ops = RealGitHubOps()

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
    ops = RealGitHubOps()

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
    ops = RealGitHubOps()

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
    ops = RealGitHubOps()

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
    ops = RealGitHubOps()

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
    ops = RealGitHubOps()

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
    ops = RealGitHubOps()

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
