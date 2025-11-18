"""Tests for context gathering logic."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from dot_agent_kit.data.kits.command.kit_cli_commands.command.context import (
    GitStatus,
    gather_context,
    get_file_tree,
    get_git_status,
    is_git_repo,
)


class TestIsGitRepo:
    """Tests for is_git_repo function."""

    def test_is_git_repo_true(self, tmp_path: Path) -> None:
        """Test detecting a git repository."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = is_git_repo(tmp_path)

            assert result is True
            mock_run.assert_called_once()
            assert mock_run.call_args[0][0] == ["git", "rev-parse", "--git-dir"]

    def test_is_git_repo_false_not_repo(self, tmp_path: Path) -> None:
        """Test detecting non-git directory."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")

            result = is_git_repo(tmp_path)

            assert result is False

    def test_is_git_repo_false_no_git_command(self, tmp_path: Path) -> None:
        """Test handling missing git command."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = is_git_repo(tmp_path)

            assert result is False


class TestGetGitStatus:
    """Tests for get_git_status function."""

    def test_get_git_status_clean_repo(self, tmp_path: Path) -> None:
        """Test getting status from clean repository."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="main", returncode=0),  # branch
                MagicMock(stdout="", returncode=0),  # status
                MagicMock(
                    stdout="abc123 Initial commit\ndef456 Add feature\n", returncode=0
                ),  # log
            ]

            result = get_git_status(tmp_path)

            assert result.branch == "main"
            assert result.uncommitted_files == []
            assert len(result.recent_commits) == 2
            assert result.is_dirty is False

    def test_get_git_status_dirty_repo(self, tmp_path: Path) -> None:
        """Test getting status from dirty repository."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="feature-branch", returncode=0),  # branch
                MagicMock(stdout=" M file1.py\n?? file2.py\n", returncode=0),  # status
                MagicMock(stdout="abc123 Recent commit\n", returncode=0),  # log
            ]

            result = get_git_status(tmp_path)

            assert result.branch == "feature-branch"
            assert len(result.uncommitted_files) == 2
            assert result.is_dirty is True

    def test_get_git_status_strips_whitespace(self, tmp_path: Path) -> None:
        """Test that git status strips whitespace correctly."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="  main  \n", returncode=0),  # branch with whitespace
                MagicMock(stdout="", returncode=0),  # status
                MagicMock(stdout="", returncode=0),  # log
            ]

            result = get_git_status(tmp_path)

            assert result.branch == "main"


class TestGetFileTree:
    """Tests for get_file_tree function."""

    def test_get_file_tree_with_tree_command(self, tmp_path: Path) -> None:
        """Test file tree generation with tree command available."""
        expected_tree = ".\n├── file1.py\n└── dir/\n"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=expected_tree, returncode=0, stderr="")

            result = get_file_tree(tmp_path, max_depth=2)

            assert result == expected_tree
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "tree"
            assert "-L" in call_args
            assert "2" in call_args

    def test_get_file_tree_fallback_no_tree_command(self, tmp_path: Path) -> None:
        """Test file tree fallback when tree command unavailable."""
        # Setup: Create some files
        (tmp_path / "file1.py").write_text("", encoding="utf-8")
        (tmp_path / "file2.txt").write_text("", encoding="utf-8")
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = get_file_tree(tmp_path)

            # Should list items with directories marked with /
            assert "file1.py" in result
            assert "file2.txt" in result
            assert "subdir/" in result

    def test_get_file_tree_filters_hidden_files(self, tmp_path: Path) -> None:
        """Test that fallback filters hidden files except .claude and .github."""
        # Setup
        (tmp_path / ".hidden").write_text("", encoding="utf-8")
        (tmp_path / "visible.py").write_text("", encoding="utf-8")
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".github").mkdir()

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            result = get_file_tree(tmp_path)

            assert ".hidden" not in result
            assert "visible.py" in result
            assert ".claude/" in result
            assert ".github/" in result


class TestGatherContext:
    """Tests for gather_context function."""

    def test_gather_context_with_git(self, tmp_path: Path) -> None:
        """Test gathering context from git repository."""
        with patch(
            "dot_agent_kit.data.kits.command.kit_cli_commands.command.context.is_git_repo"
        ) as mock_is_git:
            with patch(
                "dot_agent_kit.data.kits.command.kit_cli_commands.command.context.get_git_status"
            ) as mock_git_status:
                with patch(
                    "dot_agent_kit.data.kits.command.kit_cli_commands.command.context.get_file_tree"
                ) as mock_tree:
                    mock_is_git.return_value = True
                    mock_git_status.return_value = GitStatus(
                        branch="main",
                        uncommitted_files=[],
                        recent_commits=["abc123 Commit message"],
                        is_dirty=False,
                    )
                    mock_tree.return_value = "file1.py\nfile2.py"

                    result = gather_context(tmp_path)

                    assert "Working Directory:" in result
                    assert "Git Status:" in result
                    assert "Branch: `main`" in result
                    assert "File Tree:" in result
                    assert "Environment:" in result

    def test_gather_context_without_git(self, tmp_path: Path) -> None:
        """Test gathering context from non-git directory."""
        with patch(
            "dot_agent_kit.data.kits.command.kit_cli_commands.command.context.is_git_repo"
        ) as mock_is_git:
            with patch(
                "dot_agent_kit.data.kits.command.kit_cli_commands.command.context.get_file_tree"
            ) as mock_tree:
                mock_is_git.return_value = False
                mock_tree.return_value = "file1.py"

                result = gather_context(tmp_path)

                assert "Working Directory:" in result
                assert "Git Status:" not in result
                assert "File Tree:" in result
                assert "Environment:" in result

    def test_gather_context_includes_environment(self, tmp_path: Path) -> None:
        """Test that context includes environment information."""
        with patch(
            "dot_agent_kit.data.kits.command.kit_cli_commands.command.context.is_git_repo"
        ) as mock_is_git:
            with patch(
                "dot_agent_kit.data.kits.command.kit_cli_commands.command.context.get_file_tree"
            ) as mock_tree:
                mock_is_git.return_value = False
                mock_tree.return_value = ""

                result = gather_context(tmp_path)

                assert "OS:" in result
                assert "Python:" in result
