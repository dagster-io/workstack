"""Unit tests for git context collection functionality."""

import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from erk.integrations.github.git_context import collect_plan_git_context


class TestCollectPlanGitContext:
    """Tests for collect_plan_git_context function."""

    def test_normal_repo_with_commits(self, tmp_path: Path) -> None:
        """Test collecting git context from a normal repository."""
        # Mock successful git commands
        with patch("subprocess.run") as mock_run:
            # Setup mock responses for each git command
            mock_responses = [
                # git rev-parse HEAD
                MagicMock(
                    stdout="abc123def456789012345678901234567890123",
                    stderr="",
                    returncode=0,
                ),
                # git rev-parse --abbrev-ref HEAD
                MagicMock(
                    stdout="main",
                    stderr="",
                    returncode=0,
                ),
                # git log -5
                MagicMock(
                    stdout=(
                        "abc123\x00Fix bug\x00John Doe\x001 hour ago\n"
                        "def456\x00Add feature\x00Jane Smith\x002 hours ago\n"
                        "ghi789\x00Update docs\x00Bob Johnson\x003 hours ago\n"
                    ),
                    stderr="",
                    returncode=0,
                ),
            ]
            mock_run.side_effect = mock_responses

            # Call the function
            result = collect_plan_git_context(tmp_path)

            # Verify structure
            assert "base_commit" in result
            assert result["base_commit"] == "abc123def456789012345678901234567890123"
            assert result["branch"] == "main"
            assert len(result["recent_commits"]) == 3
            assert result["recent_commits"][0]["sha"] == "abc123"
            assert result["recent_commits"][0]["message"] == "Fix bug"
            assert result["recent_commits"][0]["author"] == "John Doe"
            assert result["recent_commits"][0]["date"] == "1 hour ago"
            assert "timestamp" in result

            # Verify timestamp is valid ISO 8601
            timestamp = datetime.fromisoformat(result["timestamp"])
            assert timestamp.tzinfo is not None

    def test_detached_head_fails(self, tmp_path: Path) -> None:
        """Test that detached HEAD state raises ValueError."""
        with patch("subprocess.run") as mock_run:
            mock_responses = [
                # git rev-parse HEAD (succeeds)
                MagicMock(
                    stdout="abc123def456789012345678901234567890123",
                    stderr="",
                    returncode=0,
                ),
                # git rev-parse --abbrev-ref HEAD (returns HEAD for detached)
                MagicMock(
                    stdout="HEAD",
                    stderr="",
                    returncode=0,
                ),
            ]
            mock_run.side_effect = mock_responses

            with pytest.raises(ValueError) as exc_info:
                collect_plan_git_context(tmp_path)

            assert "detached HEAD" in str(exc_info.value)

    def test_empty_repo_fails(self, tmp_path: Path) -> None:
        """Test that empty repository (no commits) raises ValueError."""
        with patch("subprocess.run") as mock_run:
            # git rev-parse HEAD fails with empty repo error
            mock_run.side_effect = subprocess.CalledProcessError(
                128,
                ["git", "rev-parse", "HEAD"],
                stderr="fatal: ambiguous argument 'HEAD': unknown revision",
            )

            with pytest.raises(ValueError) as exc_info:
                collect_plan_git_context(tmp_path)

            assert "empty repository" in str(exc_info.value)

    def test_less_than_five_commits(self, tmp_path: Path) -> None:
        """Test repository with fewer than 5 commits."""
        with patch("subprocess.run") as mock_run:
            mock_responses = [
                # git rev-parse HEAD
                MagicMock(
                    stdout="abc123def456789012345678901234567890123",
                    stderr="",
                    returncode=0,
                ),
                # git rev-parse --abbrev-ref HEAD
                MagicMock(
                    stdout="feature-branch",
                    stderr="",
                    returncode=0,
                ),
                # git log -5 (only returns 2 commits)
                MagicMock(
                    stdout=(
                        "abc123\x00Initial commit\x00Alice\x001 day ago\n"
                        "def456\x00Second commit\x00Bob\x002 days ago\n"
                    ),
                    stderr="",
                    returncode=0,
                ),
            ]
            mock_run.side_effect = mock_responses

            result = collect_plan_git_context(tmp_path)

            # Should succeed with fewer commits
            assert len(result["recent_commits"]) == 2
            assert result["recent_commits"][0]["sha"] == "abc123"
            assert result["recent_commits"][1]["sha"] == "def456"

    def test_git_command_failure_propagates(self, tmp_path: Path) -> None:
        """Test that git command failures propagate as CalledProcessError."""
        with patch("subprocess.run") as mock_run:
            # Simulate general git failure
            mock_run.side_effect = subprocess.CalledProcessError(
                1,
                ["git", "rev-parse", "HEAD"],
                stderr="fatal: not a git repository",
            )

            with pytest.raises(subprocess.CalledProcessError):
                collect_plan_git_context(tmp_path)

    def test_short_sha_format(self, tmp_path: Path) -> None:
        """Test that commit SHAs are shortened to 7 characters."""
        with patch("subprocess.run") as mock_run:
            mock_responses = [
                # git rev-parse HEAD (returns full SHA)
                MagicMock(
                    stdout="1234567890abcdef1234567890abcdef12345678",
                    stderr="",
                    returncode=0,
                ),
                # git rev-parse --abbrev-ref HEAD
                MagicMock(
                    stdout="main",
                    stderr="",
                    returncode=0,
                ),
                # git log -5 (with full SHAs)
                MagicMock(
                    stdout="1234567890abcdef\x00Commit message\x00Author\x00Time\n",
                    stderr="",
                    returncode=0,
                ),
            ]
            mock_run.side_effect = mock_responses

            result = collect_plan_git_context(tmp_path)

            # Base commit should be full SHA
            assert len(result["base_commit"]) == 40
            # Recent commit SHAs should be shortened
            assert len(result["recent_commits"][0]["sha"]) == 7
            assert result["recent_commits"][0]["sha"] == "1234567"
