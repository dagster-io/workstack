"""Unit tests for RealGitOps with mocked subprocess calls.

These tests verify that RealGitOps correctly constructs subprocess commands
for external tools (git) without actually executing them.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from workstack.core.gitops import RealGitOps


def test_list_remote_branches() -> None:
    """Test git branch -r with mocked subprocess."""
    with patch("subprocess.run") as mock_run:
        # Arrange: Configure mock to return sample remote branches
        mock_run.return_value = MagicMock(
            stdout="origin/main\norigin/feature-1\norigin/feature-2\n",
            returncode=0,
        )

        # Act: Call the method
        ops = RealGitOps()
        branches = ops.list_remote_branches(Path("/test/repo"))

        # Assert: Verify command construction
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "branch", "-r", "--format=%(refname:short)"]
        assert call_args[1]["cwd"] == Path("/test/repo")
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["check"] is True

        # Assert: Verify parsing
        assert branches == ["origin/main", "origin/feature-1", "origin/feature-2"]


def test_list_remote_branches_empty() -> None:
    """Test git branch -r returns empty list when no remotes."""
    with patch("subprocess.run") as mock_run:
        # Arrange: Configure mock to return empty output
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        # Act: Call the method
        ops = RealGitOps()
        branches = ops.list_remote_branches(Path("/test/repo"))

        # Assert: Verify empty list returned
        assert branches == []


def test_list_remote_branches_strips_whitespace() -> None:
    """Test git branch -r strips whitespace from branch names."""
    with patch("subprocess.run") as mock_run:
        # Arrange: Configure mock with extra whitespace
        mock_run.return_value = MagicMock(
            stdout="  origin/main  \n  origin/feature  \n\n",
            returncode=0,
        )

        # Act: Call the method
        ops = RealGitOps()
        branches = ops.list_remote_branches(Path("/test/repo"))

        # Assert: Verify whitespace stripped
        assert branches == ["origin/main", "origin/feature"]


def test_create_tracking_branch() -> None:
    """Test git branch --track with mocked subprocess."""
    with patch("subprocess.run") as mock_run:
        # Act: Call the method
        ops = RealGitOps()
        ops.create_tracking_branch(Path("/test/repo"), "feature-1", "origin/feature-1")

        # Assert: Verify command construction
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "branch", "--track", "feature-1", "origin/feature-1"]
        assert call_args[1]["cwd"] == Path("/test/repo")
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["check"] is True


def test_create_tracking_branch_with_different_names() -> None:
    """Test git branch --track with local and remote names different."""
    with patch("subprocess.run") as mock_run:
        # Act: Call the method with different branch names
        ops = RealGitOps()
        ops.create_tracking_branch(Path("/test/repo"), "local-name", "upstream/remote-name")

        # Assert: Verify command construction
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "branch", "--track", "local-name", "upstream/remote-name"]
