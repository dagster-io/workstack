"""Integration tests for GraphiteOps with minimal mocking."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.conftest import load_fixture
from workstack.core.graphite_ops import RealGraphiteOps


def test_graphite_ops_get_prs_with_mock_gitops():
    """Test GraphiteOps getting PR info with mocked GitOps."""
    # Create a mock GitOps that returns a test git directory
    mock_git_ops = MagicMock()
    test_git_dir = Path("/test/.git")
    mock_git_ops.get_git_common_dir.return_value = test_git_dir

    # Mock file reading - use side_effect to handle the call correctly
    fixture_data = load_fixture("graphite/graphite_pr_info.json")

    with (
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "read_text", return_value=fixture_data),
    ):
        ops = RealGraphiteOps()
        result = ops.get_prs_from_graphite(mock_git_ops, Path("/test"))

    assert len(result) == 3
    assert "feature-stack-1" in result
    assert result["feature-stack-1"].number == 101
    assert result["feature-stack-1"].state == "OPEN"


def test_graphite_ops_get_prs_no_git_dir():
    """Test getting PR info when git dir cannot be determined."""
    mock_git_ops = MagicMock()
    mock_git_ops.get_git_common_dir.return_value = None

    ops = RealGraphiteOps()
    result = ops.get_prs_from_graphite(mock_git_ops, Path("/test"))

    assert result == {}


def test_graphite_ops_get_prs_file_not_exists():
    """Test getting PR info when .graphite_pr_info doesn't exist."""
    mock_git_ops = MagicMock()
    mock_git_ops.get_git_common_dir.return_value = Path("/test/.git")

    with patch.object(Path, "exists") as mock_exists:
        mock_exists.return_value = False

        ops = RealGraphiteOps()
        result = ops.get_prs_from_graphite(mock_git_ops, Path("/test"))

    assert result == {}


def test_graphite_ops_get_prs_json_error():
    """Test that malformed JSON in .graphite_pr_info raises JSONDecodeError."""
    mock_git_ops = MagicMock()
    mock_git_ops.get_git_common_dir.return_value = Path("/test/.git")

    with (
        patch.object(Path, "exists") as mock_exists,
        patch.object(Path, "read_text") as mock_read_text,
    ):
        mock_exists.return_value = True
        mock_read_text.return_value = "not valid json"

        ops = RealGraphiteOps()
        with pytest.raises(json.JSONDecodeError):
            ops.get_prs_from_graphite(mock_git_ops, Path("/test"))


def test_graphite_ops_get_all_branches():
    """Test getting all branches from Graphite cache."""
    mock_git_ops = MagicMock()
    mock_git_ops.get_git_common_dir.return_value = Path("/test/.git")

    # Mock get_branch_head to return commit SHAs
    def mock_get_branch_head(repo_root, branch_name):
        commit_map = {
            "main": "abc123",
            "feature-1": "def456",
            "feature-1-sub": "ghi789",
            "feature-2": "jkl012",
        }
        return commit_map.get(branch_name)

    mock_git_ops.get_branch_head = mock_get_branch_head

    fixture_data = load_fixture("graphite/graphite_cache_persist.json")

    with (
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "read_text", return_value=fixture_data),
    ):
        ops = RealGraphiteOps()
        result = ops.get_all_branches(mock_git_ops, Path("/test"))

    assert len(result) == 4
    assert "main" in result
    assert result["main"].is_trunk is True
    assert result["main"].commit_sha == "abc123"
    assert result["main"].children == ["feature-1", "feature-2"]

    assert "feature-1" in result
    assert result["feature-1"].parent == "main"
    assert result["feature-1"].children == ["feature-1-sub"]


def test_graphite_ops_get_all_branches_no_cache():
    """Test getting branches when cache file doesn't exist."""
    mock_git_ops = MagicMock()
    mock_git_ops.get_git_common_dir.return_value = Path("/test/.git")

    with patch.object(Path, "exists") as mock_exists:
        mock_exists.return_value = False

        ops = RealGraphiteOps()
        result = ops.get_all_branches(mock_git_ops, Path("/test"))

    assert result == {}


def test_graphite_ops_get_all_branches_json_error():
    """Test that malformed JSON in .graphite_cache_persist raises JSONDecodeError."""
    mock_git_ops = MagicMock()
    mock_git_ops.get_git_common_dir.return_value = Path("/test/.git")

    with (
        patch.object(Path, "exists") as mock_exists,
        patch.object(Path, "read_text") as mock_read_text,
    ):
        mock_exists.return_value = True
        mock_read_text.return_value = "not valid json"

        ops = RealGraphiteOps()
        with pytest.raises(json.JSONDecodeError):
            ops.get_all_branches(mock_git_ops, Path("/test"))


def test_graphite_ops_get_all_branches_caches_results():
    """Test that get_all_branches() caches results for repeated calls."""
    mock_git_ops = MagicMock()
    mock_git_ops.get_git_common_dir.return_value = Path("/test/.git")

    # Mock get_branch_head to return commit SHAs with call tracking
    commit_map = {
        "main": "abc123",
        "feature-1": "def456",
        "feature-1-sub": "ghi789",
        "feature-2": "jkl012",
    }
    mock_git_ops.get_branch_head.side_effect = lambda repo_root, branch_name: commit_map.get(
        branch_name
    )

    fixture_data = load_fixture("graphite/graphite_cache_persist.json")

    with (
        patch.object(Path, "exists", return_value=True) as mock_exists,
        patch.object(Path, "read_text", return_value=fixture_data) as mock_read_text,
    ):
        ops = RealGraphiteOps()

        # First call - should read from file and call git
        result1 = ops.get_all_branches(mock_git_ops, Path("/test"))

        # Second call - should use cache
        result2 = ops.get_all_branches(mock_git_ops, Path("/test"))

    # Verify caching: file operations called only once
    assert mock_exists.call_count == 1, (
        "exists() should only be called once (cached on second call)"
    )
    assert mock_read_text.call_count == 1, (
        "read_text() should only be called once (cached on second call)"
    )

    # Verify git operations called once per branch (4 branches in fixture)
    expected_git_calls = 4
    assert mock_git_ops.get_branch_head.call_count == expected_git_calls, (
        f"get_branch_head() should be called {expected_git_calls} times "
        "(once per branch, cached on second call)"
    )

    # Verify both calls return same result
    assert result1 == result2
    assert len(result1) == 4


def test_graphite_url_construction():
    """Test Graphite URL construction."""
    ops = RealGraphiteOps()
    url = ops.get_graphite_url("dagster-io", "workstack", 42)

    assert url == "https://app.graphite.dev/github/pr/dagster-io/workstack/42"


def test_graphite_ops_sync_with_mock():
    """Test gt sync with mocked subprocess."""
    with patch("subprocess.run") as mock_run:
        ops = RealGraphiteOps()
        ops.sync(Path("/test"), force=False, quiet=False)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["gt", "sync"]
        assert call_args[1]["cwd"] == Path("/test")
        assert call_args[1]["check"] is True


def test_graphite_ops_sync_with_force():
    """Test gt sync with force flag."""
    with patch("subprocess.run") as mock_run:
        ops = RealGraphiteOps()
        ops.sync(Path("/test"), force=True, quiet=False)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["gt", "sync", "-f"]


def test_graphite_ops_sync_with_quiet():
    """Test gt sync with quiet flag."""
    with patch("subprocess.run") as mock_run:
        ops = RealGraphiteOps()
        ops.sync(Path("/test"), force=False, quiet=True)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["gt", "sync", "--quiet"]


def test_graphite_ops_sync_with_force_and_quiet():
    """Test gt sync with both force and quiet flags."""
    with patch("subprocess.run") as mock_run:
        ops = RealGraphiteOps()
        ops.sync(Path("/test"), force=True, quiet=True)

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["gt", "sync", "-f", "--quiet"]
