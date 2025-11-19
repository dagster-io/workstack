"""Tests for RealGitHub with mocked subprocess execution.

These tests verify that RealGitHub correctly calls gh CLI commands and handles
responses. We use a mock executor function instead of actual subprocess calls.
"""

import json
import subprocess
from pathlib import Path

import pytest

from erk.core.github.real import RealGitHub
from tests.conftest import load_fixture

# ============================================================================
# get_prs_for_repo() Tests
# ============================================================================


def test_get_prs_for_repo_with_checks() -> None:
    """Test fetching PRs with CI check status."""

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        if "pr" in cmd and "list" in cmd:
            if "statusCheckRollup" in str(cmd):
                return load_fixture("github/pr_list_with_checks.json")
        return "[]"

    ops = RealGitHub(execute_fn=mock_execute)
    result = ops.get_prs_for_repo(Path("/repo"), include_checks=True)

    assert len(result) == 3
    assert "feature-branch" in result
    assert result["feature-branch"].number == 123
    assert result["feature-branch"].checks_passing is True


def test_get_prs_for_repo_without_checks() -> None:
    """Test fetching PRs without CI check status."""

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        if "pr" in cmd and "list" in cmd:
            return load_fixture("github/pr_list_no_checks.json")
        return "[]"

    ops = RealGitHub(execute_fn=mock_execute)
    result = ops.get_prs_for_repo(Path("/repo"), include_checks=False)

    assert len(result) == 2
    assert "main-feature" in result
    assert result["main-feature"].checks_passing is None


def test_get_prs_for_repo_command_failure() -> None:
    """Test that get_prs_for_repo gracefully handles command failures."""

    def mock_execute_failure(cmd: list[str], cwd: Path) -> str:
        raise subprocess.CalledProcessError(1, cmd)

    ops = RealGitHub(execute_fn=mock_execute_failure)
    result = ops.get_prs_for_repo(Path("/repo"), include_checks=False)

    # Should return empty dict on failure
    assert result == {}


def test_get_prs_for_repo_json_decode_error() -> None:
    """Test that get_prs_for_repo gracefully handles malformed JSON."""

    def mock_execute_bad_json(cmd: list[str], cwd: Path) -> str:
        return "not valid json"

    ops = RealGitHub(execute_fn=mock_execute_bad_json)
    result = ops.get_prs_for_repo(Path("/repo"), include_checks=False)

    # Should return empty dict on JSON error
    assert result == {}


# ============================================================================
# get_pr_status() Tests
# ============================================================================


def test_get_pr_status_open_pr() -> None:
    """Test getting PR status for a branch with an open PR."""

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        if "--head" in cmd and "branch-name" in str(cmd):
            return load_fixture("github/pr_status_single.json")
        return "[]"

    ops = RealGitHub(execute_fn=mock_execute)
    state, number, title = ops.get_pr_status(Path("/repo"), "branch-name", debug=False)

    assert state == "OPEN"
    assert number == 456
    assert title == "Add new feature for improved performance"


def test_get_pr_status_no_pr() -> None:
    """Test getting PR status when no PR exists."""

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        return "[]"

    ops = RealGitHub(execute_fn=mock_execute)
    state, number, title = ops.get_pr_status(Path("/repo"), "no-pr-branch", debug=False)

    assert state == "NONE"
    assert number is None
    assert title is None


def test_get_pr_status_command_failure() -> None:
    """Test that get_pr_status gracefully handles command failures."""

    def mock_execute_failure(cmd: list[str], cwd: Path) -> str:
        raise subprocess.CalledProcessError(1, cmd)

    ops = RealGitHub(execute_fn=mock_execute_failure)
    state, number, title = ops.get_pr_status(Path("/repo"), "branch", debug=False)

    # Should return NONE status on failure
    assert state == "NONE"
    assert number is None
    assert title is None


def test_get_pr_status_debug_output(capsys) -> None:
    """Test debug output for PR status command."""

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        return load_fixture("github/pr_status_single.json")

    ops = RealGitHub(execute_fn=mock_execute)
    state, number, title = ops.get_pr_status(Path("/repo"), "test-branch", debug=True)

    assert state == "OPEN"
    assert number == 456


# ============================================================================
# get_pr_base_branch() Tests
# ============================================================================


def test_get_pr_base_branch_success() -> None:
    """Test getting PR base branch successfully."""

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        if "pr" in cmd and "view" in cmd and "baseRefName" in str(cmd):
            return "main\n"
        return ""

    ops = RealGitHub(execute_fn=mock_execute)
    result = ops.get_pr_base_branch(Path("/repo"), 123)

    assert result == "main"


def test_get_pr_base_branch_with_whitespace() -> None:
    """Test that get_pr_base_branch strips whitespace."""

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        if "pr" in cmd and "view" in cmd:
            return "  feature-branch  \n"
        return ""

    ops = RealGitHub(execute_fn=mock_execute)
    result = ops.get_pr_base_branch(Path("/repo"), 456)

    assert result == "feature-branch"


def test_get_pr_base_branch_command_failure() -> None:
    """Test that get_pr_base_branch returns None on command failure."""

    def mock_execute_failure(cmd: list[str], cwd: Path) -> str:
        raise subprocess.CalledProcessError(1, cmd)

    ops = RealGitHub(execute_fn=mock_execute_failure)
    result = ops.get_pr_base_branch(Path("/repo"), 123)

    assert result is None


def test_get_pr_base_branch_file_not_found() -> None:
    """Test that get_pr_base_branch returns None when gh CLI not installed."""

    def mock_execute_not_found(cmd: list[str], cwd: Path) -> str:
        raise FileNotFoundError("gh command not found")

    ops = RealGitHub(execute_fn=mock_execute_not_found)
    result = ops.get_pr_base_branch(Path("/repo"), 123)

    assert result is None


# ============================================================================
# update_pr_base_branch() Tests
# ============================================================================


def test_update_pr_base_branch_success() -> None:
    """Test updating PR base branch successfully."""
    called_with = []

    def mock_execute(cmd: list[str], cwd: Path) -> str:
        called_with.append(cmd)
        return ""

    ops = RealGitHub(execute_fn=mock_execute)
    ops.update_pr_base_branch(Path("/repo"), 123, "new-base")

    # Verify command was called correctly
    assert len(called_with) == 1
    assert called_with[0] == ["gh", "pr", "edit", "123", "--base", "new-base"]


def test_update_pr_base_branch_command_failure() -> None:
    """Test that update_pr_base_branch gracefully handles command failures."""

    def mock_execute_failure(cmd: list[str], cwd: Path) -> str:
        raise subprocess.CalledProcessError(1, cmd)

    ops = RealGitHub(execute_fn=mock_execute_failure)

    # Should not raise exception - graceful degradation
    ops.update_pr_base_branch(Path("/repo"), 123, "new-base")


def test_update_pr_base_branch_file_not_found() -> None:
    """Test that update_pr_base_branch gracefully handles missing gh CLI."""

    def mock_execute_not_found(cmd: list[str], cwd: Path) -> str:
        raise FileNotFoundError("gh command not found")

    ops = RealGitHub(execute_fn=mock_execute_not_found)

    # Should not raise exception - graceful degradation
    ops.update_pr_base_branch(Path("/repo"), 123, "new-base")


# ============================================================================
# get_pr_mergeability() Tests
# ============================================================================


def test_get_pr_mergeability_mergeable() -> None:
    """Test getting mergeability status for a mergeable PR."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify command structure
        assert cmd == ["gh", "pr", "view", "123", "--json", "mergeable,mergeStateStatus"]
        assert kwargs["cwd"] == repo_root
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["encoding"] == "utf-8"
        assert kwargs["check"] is True

        # Return mock response
        result = subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps({"mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN"}),
            stderr="",
        )
        return result

    # Patch subprocess.run in the github_ops module

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub()
        result = ops.get_pr_mergeability(repo_root, 123)

        assert result is not None
        assert result.mergeable == "MERGEABLE"
        assert result.merge_state_status == "CLEAN"
    finally:
        subprocess.run = original_run


def test_get_pr_mergeability_conflicting() -> None:
    """Test getting mergeability status for a PR with conflicts."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        result = subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps({"mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"}),
            stderr="",
        )
        return result

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub()
        result = ops.get_pr_mergeability(repo_root, 456)

        assert result is not None
        assert result.mergeable == "CONFLICTING"
        assert result.merge_state_status == "DIRTY"
    finally:
        subprocess.run = original_run


def test_get_pr_mergeability_unknown() -> None:
    """Test getting mergeability status when GitHub hasn't computed it yet."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        result = subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps({"mergeable": "UNKNOWN", "mergeStateStatus": "UNKNOWN"}),
            stderr="",
        )
        return result

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub()
        result = ops.get_pr_mergeability(repo_root, 789)

        assert result is not None
        assert result.mergeable == "UNKNOWN"
        assert result.merge_state_status == "UNKNOWN"
    finally:
        subprocess.run = original_run


def test_get_pr_mergeability_command_failure() -> None:
    """Test that get_pr_mergeability returns None on command failure."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(1, cmd, stderr="PR not found")

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub()
        result = ops.get_pr_mergeability(repo_root, 999)

        assert result is None
    finally:
        subprocess.run = original_run


def test_get_pr_mergeability_json_decode_error() -> None:
    """Test that get_pr_mergeability returns None on malformed JSON."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        result = subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="not valid json", stderr=""
        )
        return result

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub()
        result = ops.get_pr_mergeability(repo_root, 123)

        assert result is None
    finally:
        subprocess.run = original_run


def test_get_pr_mergeability_missing_key() -> None:
    """Test that get_pr_mergeability returns None when JSON is missing required keys."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Missing mergeStateStatus key
        result = subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=json.dumps({"mergeable": "MERGEABLE"}), stderr=""
        )
        return result

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub()
        result = ops.get_pr_mergeability(repo_root, 123)

        assert result is None
    finally:
        subprocess.run = original_run


def test_get_pr_mergeability_file_not_found() -> None:
    """Test that get_pr_mergeability returns None when gh CLI not installed."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise FileNotFoundError("gh command not found")

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub()
        result = ops.get_pr_mergeability(repo_root, 123)

        assert result is None
    finally:
        subprocess.run = original_run


# ============================================================================
# merge_pr() Tests
# ============================================================================


def test_merge_pr_with_squash() -> None:
    """Test merge_pr calls gh pr merge with squash strategy."""
    repo_root = Path("/repo")
    pr_number = 123

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify correct command is called
        assert cmd == ["gh", "pr", "merge", "123", "--squash"]
        assert kwargs["cwd"] == repo_root
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is True

        # Return mock successful result
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="✓ Merged pull request #123\n",
            stderr="",
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub()
        # Should not raise
        ops.merge_pr(repo_root, pr_number, squash=True, verbose=False)
    finally:
        subprocess.run = original_run


def test_merge_pr_without_squash() -> None:
    """Test merge_pr can be called without squash strategy."""
    repo_root = Path("/repo")
    pr_number = 456

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify squash flag is NOT included when squash=False
        assert cmd == ["gh", "pr", "merge", "456"]
        assert "--squash" not in cmd

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="✓ Merged pull request #456\n",
            stderr="",
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub()
        ops.merge_pr(repo_root, pr_number, squash=False, verbose=False)
    finally:
        subprocess.run = original_run


def test_merge_pr_raises_on_failure() -> None:
    """Test merge_pr raises CalledProcessError when gh pr merge fails."""
    repo_root = Path("/repo")
    pr_number = 789

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(1, cmd, stderr="PR not found")

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub()

        # Should raise CalledProcessError
        with pytest.raises(subprocess.CalledProcessError):
            ops.merge_pr(repo_root, pr_number, squash=True, verbose=False)
    finally:
        subprocess.run = original_run
