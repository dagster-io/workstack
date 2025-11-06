"""Smoke tests for submit_branch.py script."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add script to path
SCRIPT_DIR = (
    Path(__file__).parent.parent.parent.parent
    / "packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/skills/gt-graphite/scripts"
)
sys.path.insert(0, str(SCRIPT_DIR))

# Import after path modification - noqa suppresses E402 (module import not at top)
from submit_branch import (  # noqa: E402
    extract_title_and_body,
    get_current_branch,
    has_uncommitted_changes,
    main,
)


class TestExtractTitleAndBody:
    """Tests for extract_title_and_body() pure function."""

    def test_single_line_message(self) -> None:
        """Test extracting title from single-line commit message."""
        result = extract_title_and_body("Add new feature")

        assert result == ("Add new feature", "")

    def test_multiline_message(self) -> None:
        """Test extracting title and body from multiline message."""
        message = "Add new feature\n\nThis is the body\nwith multiple lines"
        result = extract_title_and_body(message)

        assert result == ("Add new feature", "This is the body\nwith multiple lines")

    def test_message_with_extra_whitespace(self) -> None:
        """Test that whitespace is stripped correctly."""
        message = "  Add new feature  \n\n  Body content  "
        result = extract_title_and_body(message)

        assert result == ("Add new feature", "Body content")

    def test_empty_body(self) -> None:
        """Test message with title and empty body section."""
        message = "Add new feature\n\n"
        result = extract_title_and_body(message)

        assert result == ("Add new feature", "")


class TestGetCurrentBranch:
    """Tests for get_current_branch()."""

    def test_returns_branch_name(self) -> None:
        """Test getting current branch name."""
        mock_result = Mock()
        mock_result.stdout = "feature-branch\n"

        with patch("submit_branch.subprocess.run", return_value=mock_result) as mock_run:
            result = get_current_branch()

            mock_run.assert_called_once_with(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True,
            )
            assert result == "feature-branch"

    def test_strips_whitespace(self) -> None:
        """Test that whitespace is stripped from branch name."""
        mock_result = Mock()
        mock_result.stdout = "  feature-branch  \n"

        with patch("submit_branch.subprocess.run", return_value=mock_result):
            result = get_current_branch()

            assert result == "feature-branch"


class TestHasUncommittedChanges:
    """Tests for has_uncommitted_changes()."""

    def test_returns_true_when_changes_exist(self) -> None:
        """Test detecting uncommitted changes."""
        mock_result = Mock()
        mock_result.stdout = " M file.txt\n"

        with patch("submit_branch.subprocess.run", return_value=mock_result) as mock_run:
            result = has_uncommitted_changes()

            mock_run.assert_called_once_with(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )
            assert result is True

    def test_returns_false_when_no_changes(self) -> None:
        """Test no uncommitted changes."""
        mock_result = Mock()
        mock_result.stdout = ""

        with patch("submit_branch.subprocess.run", return_value=mock_result):
            result = has_uncommitted_changes()

            assert result is False

    def test_returns_false_when_only_whitespace(self) -> None:
        """Test empty output is treated as no changes."""
        mock_result = Mock()
        mock_result.stdout = "  \n  "

        with patch("submit_branch.subprocess.run", return_value=mock_result):
            result = has_uncommitted_changes()

            assert result is False


class TestMainEntryPoint:
    """Smoke tests for main() entry point."""

    def test_main_no_subcommand(self) -> None:
        """Test main with no subcommand returns error."""
        with patch("sys.argv", ["submit_branch.py"]):
            exit_code = main()

            assert exit_code == 1

    def test_main_invalid_subcommand(self) -> None:
        """Test main with invalid subcommand returns error."""
        with patch("sys.argv", ["submit_branch.py", "invalid"]):
            exit_code = main()

            assert exit_code == 1

    def test_main_prepare_success(self) -> None:
        """Smoke test for prepare subcommand."""
        with (
            patch("sys.argv", ["submit_branch.py", "prepare"]),
            patch("submit_branch.get_current_branch", return_value="feature-branch"),
            patch("submit_branch.has_uncommitted_changes", return_value=False),
            patch("submit_branch.squash_commits", return_value=True),
            patch("submit_branch.get_parent_branch", return_value="main"),
        ):
            exit_code = main()

            assert exit_code == 0

    def test_main_amend_missing_message(self) -> None:
        """Test amend subcommand without message argument."""
        with patch("sys.argv", ["submit_branch.py", "amend"]):
            exit_code = main()

            assert exit_code == 1

    def test_main_amend_success(self) -> None:
        """Smoke test for amend subcommand."""
        with (
            patch("sys.argv", ["submit_branch.py", "amend", "New commit message"]),
            patch("submit_branch.get_current_branch", return_value="feature-branch"),
            patch("submit_branch.amend_commit_message", return_value=True),
        ):
            exit_code = main()

            assert exit_code == 0

    def test_main_submit_success(self) -> None:
        """Smoke test for submit subcommand."""
        with (
            patch("sys.argv", ["submit_branch.py", "submit"]),
            patch("submit_branch.get_current_branch", return_value="feature-branch"),
            patch("submit_branch.submit_branch", return_value=(True, "Success")),
            patch("submit_branch.get_pr_info", return_value=(123, "https://github.com/...")),
        ):
            exit_code = main()

            assert exit_code == 0

    def test_main_update_pr_missing_message(self) -> None:
        """Test update-pr subcommand without message argument."""
        with patch("sys.argv", ["submit_branch.py", "update-pr"]):
            exit_code = main()

            assert exit_code == 1

    def test_main_update_pr_success(self) -> None:
        """Smoke test for update-pr subcommand."""
        with (
            patch("sys.argv", ["submit_branch.py", "update-pr", "Commit message"]),
            patch("submit_branch.get_current_branch", return_value="feature-branch"),
            patch("submit_branch.get_pr_info", return_value=(123, "https://github.com/...")),
            patch("submit_branch.update_pr_metadata", return_value=True),
        ):
            exit_code = main()

            assert exit_code == 0

    def test_main_update_pr_no_pr_exists(self) -> None:
        """Test update-pr when no PR exists (should succeed gracefully)."""
        with (
            patch("sys.argv", ["submit_branch.py", "update-pr", "Commit message"]),
            patch("submit_branch.get_current_branch", return_value="feature-branch"),
            patch("submit_branch.get_pr_info", return_value=None),
        ):
            exit_code = main()

            assert exit_code == 0
