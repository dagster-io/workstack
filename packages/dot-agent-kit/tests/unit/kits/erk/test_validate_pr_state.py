"""Unit tests for validate-pr-state kit CLI command."""

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state import (
    ValidationResult,
    validate_pr_state,
    validate_pr_state_cmd,
)

# Test the validation logic directly


class TestValidatePrState:
    """Tests for the validate_pr_state function."""

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_pr_info")
    def test_no_pr_exists(self, mock_get_pr_info: MagicMock) -> None:
        """Test validation passes when no PR exists for branch."""
        mock_get_pr_info.return_value = None

        result = validate_pr_state(issue_number=123, branch_name="my-feature")

        assert result.valid is True
        assert result.pr_exists is False
        assert result.pr_number is None
        assert result.error is None

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_linked_issue")
    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_pr_info")
    def test_open_pr_same_issue(
        self, mock_get_pr_info: MagicMock, mock_get_linked_issue: MagicMock
    ) -> None:
        """Test validation passes for OPEN PR linked to same issue."""
        mock_get_pr_info.return_value = {"number": 456, "state": "OPEN"}
        mock_get_linked_issue.return_value = 123  # Same as issue_number

        result = validate_pr_state(issue_number=123, branch_name="my-feature")

        assert result.valid is True
        assert result.pr_exists is True
        assert result.pr_number == 456
        assert result.pr_state == "OPEN"
        assert result.linked_issue == 123
        assert result.error is None

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_linked_issue")
    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_pr_info")
    def test_open_pr_no_linked_issue(
        self, mock_get_pr_info: MagicMock, mock_get_linked_issue: MagicMock
    ) -> None:
        """Test validation passes for OPEN PR with no linked issue."""
        mock_get_pr_info.return_value = {"number": 456, "state": "OPEN"}
        mock_get_linked_issue.return_value = None

        result = validate_pr_state(issue_number=123, branch_name="my-feature")

        assert result.valid is True
        assert result.pr_exists is True
        assert result.pr_state == "OPEN"
        assert result.linked_issue is None
        assert result.error is None

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_linked_issue")
    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_pr_info")
    def test_closed_pr_fails(
        self, mock_get_pr_info: MagicMock, mock_get_linked_issue: MagicMock
    ) -> None:
        """Test validation fails for CLOSED PR."""
        mock_get_pr_info.return_value = {"number": 456, "state": "CLOSED"}
        mock_get_linked_issue.return_value = 123

        result = validate_pr_state(issue_number=123, branch_name="my-feature")

        assert result.valid is False
        assert result.pr_exists is True
        assert result.pr_state == "CLOSED"
        assert result.error_type == "pr_closed"
        assert result.error is not None
        assert "CLOSED" in result.error
        assert "gh pr reopen" in result.error

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_linked_issue")
    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_pr_info")
    def test_merged_pr_fails(
        self, mock_get_pr_info: MagicMock, mock_get_linked_issue: MagicMock
    ) -> None:
        """Test validation fails for MERGED PR."""
        mock_get_pr_info.return_value = {"number": 456, "state": "MERGED"}
        mock_get_linked_issue.return_value = 123

        result = validate_pr_state(issue_number=123, branch_name="my-feature")

        assert result.valid is False
        assert result.pr_exists is True
        assert result.pr_state == "MERGED"
        assert result.error_type == "pr_merged"
        assert result.error is not None
        assert "MERGED" in result.error

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_linked_issue")
    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_pr_info")
    def test_branch_collision_different_issue(
        self, mock_get_pr_info: MagicMock, mock_get_linked_issue: MagicMock
    ) -> None:
        """Test validation fails when PR is linked to different issue."""
        mock_get_pr_info.return_value = {"number": 456, "state": "OPEN"}
        mock_get_linked_issue.return_value = 999  # Different issue!

        result = validate_pr_state(issue_number=123, branch_name="my-feature")

        assert result.valid is False
        assert result.pr_exists is True
        assert result.error_type == "branch_collision"
        assert result.error is not None
        assert "#999" in result.error
        assert "#123" in result.error
        assert "collision" in result.error.lower()

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._post_comment")
    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_linked_issue")
    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_pr_info")
    def test_posts_comment_on_collision_when_flag_set(
        self,
        mock_get_pr_info: MagicMock,
        mock_get_linked_issue: MagicMock,
        mock_post_comment: MagicMock,
    ) -> None:
        """Test that error comment is posted when post_comment=True."""
        mock_get_pr_info.return_value = {"number": 456, "state": "OPEN"}
        mock_get_linked_issue.return_value = 999
        mock_post_comment.return_value = True

        result = validate_pr_state(issue_number=123, branch_name="my-feature", post_comment=True)

        assert result.valid is False
        mock_post_comment.assert_called_once()
        # Verify comment was posted to the right issue
        call_args = mock_post_comment.call_args
        assert call_args[0][0] == 123  # issue_number

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._post_comment")
    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_linked_issue")
    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state._get_pr_info")
    def test_no_comment_posted_when_flag_not_set(
        self,
        mock_get_pr_info: MagicMock,
        mock_get_linked_issue: MagicMock,
        mock_post_comment: MagicMock,
    ) -> None:
        """Test that no comment is posted when post_comment=False."""
        mock_get_pr_info.return_value = {"number": 456, "state": "CLOSED"}
        mock_get_linked_issue.return_value = 123

        result = validate_pr_state(issue_number=123, branch_name="my-feature", post_comment=False)

        assert result.valid is False
        mock_post_comment.assert_not_called()


# Test the CLI command


class TestValidatePrStateCli:
    """Tests for the validate-pr-state CLI command."""

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state.validate_pr_state")
    def test_cli_valid_result_exit_0(self, mock_validate: MagicMock) -> None:
        """Test CLI exits with code 0 when validation passes."""
        mock_validate.return_value = ValidationResult(valid=True, pr_exists=False)

        runner = CliRunner()
        result = runner.invoke(
            validate_pr_state_cmd,
            ["--issue-number", "123", "--branch-name", "my-feature"],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["valid"] is True
        assert output["pr_exists"] is False

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state.validate_pr_state")
    def test_cli_invalid_result_exit_1(self, mock_validate: MagicMock) -> None:
        """Test CLI exits with code 1 when validation fails."""
        mock_validate.return_value = ValidationResult(
            valid=False,
            pr_exists=True,
            pr_number=456,
            pr_state="CLOSED",
            error_type="pr_closed",
            error="PR is CLOSED",
        )

        runner = CliRunner()
        result = runner.invoke(
            validate_pr_state_cmd,
            ["--issue-number", "123", "--branch-name", "my-feature"],
        )

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["valid"] is False
        assert output["error_type"] == "pr_closed"

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state.validate_pr_state")
    def test_cli_passes_post_comment_flag(self, mock_validate: MagicMock) -> None:
        """Test CLI passes --post-comment flag to function."""
        mock_validate.return_value = ValidationResult(valid=True, pr_exists=False)

        runner = CliRunner()
        runner.invoke(
            validate_pr_state_cmd,
            ["--issue-number", "123", "--branch-name", "feat", "--post-comment"],
        )

        mock_validate.assert_called_once_with(
            issue_number=123,
            branch_name="feat",
            post_comment=True,
        )

    def test_cli_requires_issue_number(self) -> None:
        """Test CLI fails when --issue-number is missing."""
        runner = CliRunner()
        result = runner.invoke(
            validate_pr_state_cmd,
            ["--branch-name", "my-feature"],
        )

        assert result.exit_code != 0

    def test_cli_requires_branch_name(self) -> None:
        """Test CLI fails when --branch-name is missing."""
        runner = CliRunner()
        result = runner.invoke(
            validate_pr_state_cmd,
            ["--issue-number", "123"],
        )

        assert result.exit_code != 0

    @patch("dot_agent_kit.data.kits.erk.kit_cli_commands.erk.validate_pr_state.validate_pr_state")
    def test_cli_json_output_excludes_none_values(self, mock_validate: MagicMock) -> None:
        """Test CLI JSON output doesn't include None values."""
        mock_validate.return_value = ValidationResult(
            valid=True,
            pr_exists=True,
            pr_number=456,
            pr_state="OPEN",
            linked_issue=None,  # Should be excluded
            error=None,  # Should be excluded
        )

        runner = CliRunner()
        result = runner.invoke(
            validate_pr_state_cmd,
            ["--issue-number", "123", "--branch-name", "my-feature"],
        )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert "linked_issue" not in output
        assert "error" not in output
        assert "error_type" not in output
