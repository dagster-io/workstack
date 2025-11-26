"""Tests for parse_issue_reference utility."""

import pytest

from erk.cli.parse_issue_reference import parse_issue_reference


class TestParseIssueReference:
    """Tests for parse_issue_reference function."""

    def test_parse_plain_number(self) -> None:
        """Parse plain issue number successfully."""
        result = parse_issue_reference("123")
        assert result == 123

    def test_parse_github_url(self) -> None:
        """Parse GitHub issue URL successfully."""
        result = parse_issue_reference("https://github.com/owner/repo/issues/456")
        assert result == 456

    def test_parse_github_url_with_fragment(self) -> None:
        """Parse GitHub issue URL with fragment (comment anchor) successfully."""
        result = parse_issue_reference("https://github.com/owner/repo/issues/789#issuecomment-123")
        assert result == 789

    def test_parse_github_url_with_query_string(self) -> None:
        """Parse GitHub issue URL with query string successfully."""
        result = parse_issue_reference("https://github.com/owner/repo/issues/999?foo=bar")
        assert result == 999

    def test_parse_github_url_with_trailing_slash(self) -> None:
        """Parse GitHub issue URL with trailing slash successfully."""
        result = parse_issue_reference("https://github.com/owner/repo/issues/111/")
        assert result == 111

    def test_parse_large_issue_number(self) -> None:
        """Parse large issue numbers successfully."""
        result = parse_issue_reference("999999")
        assert result == 999999

    def test_reject_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Reject zero as invalid issue number."""
        with pytest.raises(SystemExit) as exc_info:
            parse_issue_reference("0")
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "must be a positive integer" in captured.err

    def test_reject_negative_number(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Reject negative numbers as invalid issue numbers."""
        with pytest.raises(SystemExit) as exc_info:
            parse_issue_reference("-1")
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Invalid issue number or URL" in captured.err

    def test_reject_non_numeric(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Reject non-numeric input."""
        with pytest.raises(SystemExit) as exc_info:
            parse_issue_reference("abc")
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Invalid issue number or URL" in captured.err

    def test_reject_empty_string(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Reject empty string input."""
        with pytest.raises(SystemExit) as exc_info:
            parse_issue_reference("")
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Invalid issue number or URL" in captured.err

    def test_reject_url_without_issue_number(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Reject GitHub URL without issue number."""
        with pytest.raises(SystemExit) as exc_info:
            parse_issue_reference("https://github.com/owner/repo/issues/")
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Invalid issue number or URL" in captured.err

    def test_error_message_shows_expected_formats(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Error message shows expected input formats."""
        with pytest.raises(SystemExit):
            parse_issue_reference("invalid")

        captured = capsys.readouterr()
        assert "Expected formats:" in captured.err
        assert "Plain number: 123" in captured.err
        assert "GitHub URL: https://github.com/owner/repo/issues/456" in captured.err

    def test_whitespace_in_number_rejected(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Reject numbers with whitespace."""
        with pytest.raises(SystemExit) as exc_info:
            parse_issue_reference("12 3")
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Invalid issue number or URL" in captured.err

    def test_leading_zeros_accepted(self) -> None:
        """Accept numbers with leading zeros (parsed as integers)."""
        result = parse_issue_reference("00123")
        assert result == 123
