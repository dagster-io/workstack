"""Tests for CLI Ensure utility class."""

import pytest

from erk.cli.ensure import Ensure


class TestEnsureNotNone:
    """Tests for Ensure.not_none method."""

    def test_returns_value_when_not_none(self) -> None:
        """Ensure.not_none returns the value unchanged when not None."""
        result = Ensure.not_none("hello", "Value is None")
        assert result == "hello"

    def test_returns_value_preserves_type(self) -> None:
        """Ensure.not_none preserves the type of the returned value."""
        value: int | None = 42
        result = Ensure.not_none(value, "Value is None")
        assert result == 42
        # Type checker should infer result as int, not int | None

    def test_exits_when_none(self) -> None:
        """Ensure.not_none raises SystemExit when value is None."""
        with pytest.raises(SystemExit) as exc_info:
            Ensure.not_none(None, "Value is None")
        assert exc_info.value.code == 1

    def test_error_message_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ensure.not_none outputs error message with red Error prefix to stderr."""
        with pytest.raises(SystemExit):
            Ensure.not_none(None, "Custom error message")

        captured = capsys.readouterr()
        # user_output routes to stderr for shell integration
        assert "Error:" in captured.err
        assert "Custom error message" in captured.err

    def test_works_with_complex_types(self) -> None:
        """Ensure.not_none works with complex types like dicts and lists."""
        data: dict[str, int] | None = {"key": 123}
        result = Ensure.not_none(data, "Data is None")
        assert result == {"key": 123}

    def test_zero_is_not_none(self) -> None:
        """Ensure.not_none returns 0 since 0 is not None."""
        result = Ensure.not_none(0, "Value is None")
        assert result == 0

    def test_empty_string_is_not_none(self) -> None:
        """Ensure.not_none returns empty string since empty string is not None."""
        result = Ensure.not_none("", "Value is None")
        assert result == ""

    def test_empty_list_is_not_none(self) -> None:
        """Ensure.not_none returns empty list since empty list is not None."""
        result: list[str] | None = []
        actual = Ensure.not_none(result, "Value is None")
        assert actual == []

    def test_false_is_not_none(self) -> None:
        """Ensure.not_none returns False since False is not None."""
        result = Ensure.not_none(False, "Value is None")
        assert result is False


class TestEnsureParseGithubIssueReference:
    """Tests for Ensure.parse_github_issue_reference method."""

    def test_parse_valid_number(self) -> None:
        """Ensure.parse_github_issue_reference parses valid issue number."""
        result = Ensure.parse_github_issue_reference("123")
        assert result == 123

    def test_parse_valid_url(self) -> None:
        """Ensure.parse_github_issue_reference parses valid GitHub URL."""
        result = Ensure.parse_github_issue_reference("https://github.com/owner/repo/issues/456")
        assert result == 456

    def test_exits_on_invalid_input(self) -> None:
        """Ensure.parse_github_issue_reference exits on invalid input."""
        with pytest.raises(SystemExit) as exc_info:
            Ensure.parse_github_issue_reference("invalid")
        assert exc_info.value.code == 1

    def test_exits_on_zero(self) -> None:
        """Ensure.parse_github_issue_reference exits on zero."""
        with pytest.raises(SystemExit) as exc_info:
            Ensure.parse_github_issue_reference("0")
        assert exc_info.value.code == 1


class TestEnsureGithubApiCall:
    """Tests for Ensure.github_api_call method."""

    def test_returns_operation_result(self) -> None:
        """Ensure.github_api_call returns the operation result on success."""
        result = Ensure.github_api_call(lambda: 42)
        assert result == 42

    def test_preserves_return_type(self) -> None:
        """Ensure.github_api_call preserves return type."""
        result = Ensure.github_api_call(lambda: {"key": "value"})
        assert result == {"key": "value"}

    def test_exits_on_runtime_error(self) -> None:
        """Ensure.github_api_call exits when operation raises RuntimeError."""
        with pytest.raises(SystemExit) as exc_info:
            Ensure.github_api_call(lambda: (_ for _ in ()).throw(RuntimeError("API error")))
        assert exc_info.value.code == 1

    def test_error_message_without_context(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ensure.github_api_call outputs error message without context."""
        with pytest.raises(SystemExit):
            Ensure.github_api_call(lambda: (_ for _ in ()).throw(RuntimeError("API failed")))

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "API failed" in captured.err

    def test_error_message_with_context(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ensure.github_api_call outputs error message with context."""
        with pytest.raises(SystemExit):
            Ensure.github_api_call(
                lambda: (_ for _ in ()).throw(RuntimeError("Not found")),
                error_context="Failed to fetch issue",
            )

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Failed to fetch issue: Not found" in captured.err

    def test_non_runtime_errors_propagate(self) -> None:
        """Ensure.github_api_call lets non-RuntimeError exceptions propagate."""
        with pytest.raises(ValueError):
            Ensure.github_api_call(lambda: (_ for _ in ()).throw(ValueError("Different error")))
