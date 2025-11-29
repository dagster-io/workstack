"""Unit tests for real_ops.py subprocess integration with mocked subprocess.

These tests verify that real subprocess-based implementations construct commands
correctly and parse outputs properly. All subprocess calls are mocked to ensure
fast execution. For integration tests with real subprocess calls, see
tests/integration/kits/gt/test_real_git_ops.py.

Test organization:
- TestRealGitGtKitOps: Git operations (6 methods, mocked subprocess)
- TestRealGraphiteGtKitOps: Graphite operations (6 methods, mocked subprocess)
- TestRealGtKitOps: Composite operations (3 accessor methods)

Note: GitHub operations are now tested via GitHubAdapter tests since
RealGitHubGtKit was consolidated into the GitHub ABC + GitHubAdapter pattern.
"""

import subprocess
from unittest.mock import Mock, patch

from erk_shared.integrations.gt import (
    CommandResult,
    GitHubAdapter,
    RealGitGtKit,
    RealGraphiteGtKit,
    RealGtKit,
)


class TestRealGitGtKitOps:
    """Unit tests for RealGitGtKit with mocked subprocess calls."""

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_get_current_branch(self, mock_run: Mock) -> None:
        """Test get_current_branch constructs command and parses output correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "main\n"
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        branch_name = ops.get_current_branch()

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "branch", "--show-current"]

        # Verify output parsing
        assert branch_name == "main"

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_has_uncommitted_changes_clean(self, mock_run: Mock) -> None:
        """Test has_uncommitted_changes returns False when repo is clean."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""  # Empty output = clean repo
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        result = ops.has_uncommitted_changes()

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "status", "--porcelain"]

        # Verify return value
        assert result is False

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_has_uncommitted_changes_dirty(self, mock_run: Mock) -> None:
        """Test has_uncommitted_changes returns True when repo has changes."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = " M file.txt\n"  # Modified file
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        result = ops.has_uncommitted_changes()

        # Verify return value
        assert result is True

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_add_all(self, mock_run: Mock) -> None:
        """Test add_all constructs command correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        result = ops.add_all()

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "add", "."]

        # Verify return value
        assert result is True

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_commit(self, mock_run: Mock) -> None:
        """Test commit constructs command with message correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        result = ops.commit("Test commit message")

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "commit", "-m", "Test commit message"]

        # Verify return value
        assert result is True

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_amend_commit(self, mock_run: Mock) -> None:
        """Test amend_commit constructs command with message correctly."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        result = ops.amend_commit("Amended message")

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "commit", "--amend", "-m", "Amended message"]

        # Verify return value
        assert result is True

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_count_commits_in_branch(self, mock_run: Mock) -> None:
        """Test count_commits_in_branch constructs command and parses count."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "3\n"
        mock_run.return_value = mock_result

        ops = RealGitGtKit()
        count = ops.count_commits_in_branch("main")

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["git", "rev-list", "--count", "main..HEAD"]

        # Verify output parsing
        assert count == 3


class TestRealGraphiteGtKitOps:
    """Unit tests for RealGraphiteGtKit with mocked subprocess calls."""

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_get_parent_branch(self, mock_run: Mock) -> None:
        """Test get_parent_branch constructs command and parses output."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "main\n"
        mock_run.return_value = mock_result

        ops = RealGraphiteGtKit()
        result = ops.get_parent_branch()

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["gt", "parent"]

        # Verify output parsing
        assert result == "main"

    @patch("erk_shared.integrations.gt.real.subprocess.run")
    def test_get_children_branches(self, mock_run: Mock) -> None:
        """Test get_children_branches constructs command and parses output."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "feature-1\nfeature-2\n"
        mock_run.return_value = mock_result

        ops = RealGraphiteGtKit()
        result = ops.get_children_branches()

        # Verify correct command was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args == ["gt", "children"]

        # Verify output parsing
        assert result == ["feature-1", "feature-2"]

    def test_squash_commits(self) -> None:
        """Test squash_commits returns CommandResult and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGraphiteGtKit()
            result = ops.squash_commits()

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gt", "squash", "--no-edit", "--no-interactive"],
                capture_output=True,
                text=True,
                check=False,
            )

            # Verify return type matches interface contract
            assert isinstance(result, CommandResult)
            assert result.success is True

        # Test failure case
        mock_result.returncode = 1
        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ):
            ops = RealGraphiteGtKit()
            result = ops.squash_commits()
            assert isinstance(result, CommandResult)
            assert result.success is False

    def test_submit(self) -> None:
        """Test submit returns CommandResult and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "PR created successfully"
        mock_result.stderr = ""

        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGraphiteGtKit()
            result = ops.submit(publish=False, restack=False)

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gt", "submit", "--no-edit", "--no-interactive"],
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )

            # Verify return type matches interface contract
            assert isinstance(result, CommandResult)
            assert isinstance(result.success, bool)
            assert isinstance(result.stdout, str)
            assert isinstance(result.stderr, str)
            assert result.success is True
            assert result.stdout == "PR created successfully"
            assert result.stderr == ""

        # Test with publish=True, restack=True
        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGraphiteGtKit()
            result = ops.submit(publish=True, restack=True)

            # Verify flags are added
            mock_run.assert_called_once_with(
                ["gt", "submit", "--no-edit", "--no-interactive", "--publish", "--restack"],
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )

    def test_submit_timeout(self) -> None:
        """Test submit handles TimeoutExpired exception correctly."""
        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["gt", "submit"], timeout=120),
        ):
            ops = RealGraphiteGtKit()
            result = ops.submit(publish=True, restack=True)

            # Verify error is handled gracefully
            assert isinstance(result, CommandResult)
            assert result.success is False
            assert "timed out after 120 seconds" in result.stderr
            assert result.stdout == ""

    def test_restack(self) -> None:
        """Test restack returns CommandResult and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Restacked successfully"
        mock_result.stderr = ""

        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGraphiteGtKit()
            result = ops.restack()

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gt", "restack", "--no-interactive"],
                capture_output=True,
                text=True,
                check=False,
            )

            # Verify return type matches interface contract
            assert result.success is True
            assert result.stdout == "Restacked successfully"
            assert result.stderr == ""

        # Test failure case
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Failed to restack"
        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ):
            ops = RealGraphiteGtKit()
            result = ops.restack()
            assert result.success is False
            assert result.stderr == "Failed to restack"

    def test_navigate_to_child(self) -> None:
        """Test navigate_to_child returns bool and calls correct command."""
        mock_result = Mock()
        mock_result.returncode = 0

        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            ops = RealGraphiteGtKit()
            result = ops.navigate_to_child()

            # Verify correct command was called
            mock_run.assert_called_once_with(
                ["gt", "up"], capture_output=True, text=True, check=False
            )

            # Verify return type matches interface contract
            assert isinstance(result, bool)
            assert result is True

        # Test failure case
        mock_result.returncode = 1
        with patch(
            "erk_shared.integrations.gt.real.subprocess.run",
            return_value=mock_result,
        ):
            ops = RealGraphiteGtKit()
            result = ops.navigate_to_child()
            assert result is False


class TestRealGtKitOps:
    """Unit tests for RealGtKit composite operations."""

    def test_git(self) -> None:
        """Test git() returns RealGitGtKit instance."""
        ops = RealGtKit()

        # Get git operations interface
        git_ops = ops.git()

        # Verify return type matches interface contract
        assert isinstance(git_ops, RealGitGtKit)

    def test_graphite(self) -> None:
        """Test graphite() returns RealGraphiteGtKit instance."""
        ops = RealGtKit()

        # Get graphite operations interface
        graphite_ops = ops.graphite()

        # Verify return type matches interface contract
        assert isinstance(graphite_ops, RealGraphiteGtKit)

    def test_github(self) -> None:
        """Test github() returns GitHubAdapter instance."""
        ops = RealGtKit()

        # Get github operations interface
        github_ops = ops.github()

        # Verify return type matches interface contract
        # RealGtKit now uses GitHubAdapter to wrap RealGitHub
        assert isinstance(github_ops, GitHubAdapter)
