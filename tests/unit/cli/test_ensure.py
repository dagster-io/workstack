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


class TestEnsureSucceeds:
    """Tests for Ensure.succeeds method."""

    def test_returns_value_on_success(self) -> None:
        """Ensure.succeeds returns operation result when no exception."""
        result = Ensure.succeeds(lambda: "success", "Should not fail")
        assert result == "success"

    def test_preserves_return_type(self) -> None:
        """Ensure.succeeds preserves operation return type."""
        result: int = Ensure.succeeds(lambda: 42, "Should not fail")
        assert result == 42

    def test_exits_on_exception(self) -> None:
        """Ensure.succeeds raises SystemExit when operation raises exception."""
        def failing_operation() -> str:
            raise RuntimeError("Network error")

        with pytest.raises(SystemExit) as exc_info:
            Ensure.succeeds(failing_operation, "Failed to connect")
        assert exc_info.value.code == 1

    def test_custom_exception_type(self) -> None:
        """Ensure.succeeds catches specified exception type."""
        def failing_operation() -> str:
            raise OSError("File not found")

        with pytest.raises(SystemExit):
            Ensure.succeeds(failing_operation, "I/O failed", exception_type=OSError)

    def test_does_not_catch_other_exceptions(self) -> None:
        """Ensure.succeeds does not catch exceptions of different type."""
        def failing_operation() -> str:
            raise ValueError("Wrong type")

        # ValueError should propagate, not be caught
        with pytest.raises(ValueError):
            Ensure.succeeds(failing_operation, "Failed", exception_type=RuntimeError)

    def test_error_message_format(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ensure.succeeds outputs error with red Error prefix."""
        def failing_operation() -> str:
            raise RuntimeError("API timeout")

        with pytest.raises(SystemExit):
            Ensure.succeeds(failing_operation, "API call failed")

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "API call failed" in captured.err
        assert "API timeout" in captured.err

    def test_preserves_exception_chain(self) -> None:
        """Ensure.succeeds maintains exception chain with from e."""
        def failing_operation() -> str:
            raise RuntimeError("Original error")

        with pytest.raises(SystemExit) as exc_info:
            Ensure.succeeds(failing_operation, "Operation failed")

        # Verify exception chaining
        assert exc_info.value.__cause__.__class__.__name__ == "RuntimeError"
        assert str(exc_info.value.__cause__) == "Original error"


class TestEnsureIntegrationCall:
    """Tests for Ensure.integration_call convenience method."""

    def test_returns_value_on_success(self) -> None:
        """Ensure.integration_call returns result on success."""
        result = Ensure.integration_call(
            lambda: {"key": "value"},
            "Should not fail"
        )
        assert result == {"key": "value"}

    def test_catches_runtime_error(self) -> None:
        """Ensure.integration_call catches RuntimeError from integration layer."""
        def failing_operation() -> str:
            raise RuntimeError("API error")

        with pytest.raises(SystemExit):
            Ensure.integration_call(failing_operation, "Integration failed")


class TestEnsureFileOperation:
    """Tests for Ensure.file_operation convenience method."""

    def test_returns_value_on_success(self) -> None:
        """Ensure.file_operation returns result on success."""
        result = Ensure.file_operation(
            lambda: "file content",
            "Should not fail"
        )
        assert result == "file content"

    def test_catches_os_error(self) -> None:
        """Ensure.file_operation catches OSError from file operations."""
        def failing_operation() -> str:
            raise OSError("Permission denied")

        with pytest.raises(SystemExit):
            Ensure.file_operation(failing_operation, "File read failed")
