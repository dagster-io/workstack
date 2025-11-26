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


class TestEnsureGtAuthenticated:
    """Tests for Ensure.gt_authenticated method."""

    def test_passes_when_gt_installed_and_authenticated(self) -> None:
        """Ensure.gt_authenticated passes when gt is installed and authenticated."""
        from unittest.mock import MagicMock, patch

        # Mock shutil.which to return a path (gt is installed)
        with patch("shutil.which", return_value="/usr/local/bin/gt"):
            # Mock subprocess.run to return success (gt is authenticated)
            mock_result = MagicMock()
            mock_result.returncode = 0
            with patch("subprocess.run", return_value=mock_result):
                # Should not raise
                Ensure.gt_authenticated()

    def test_exits_when_gt_not_installed(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ensure.gt_authenticated raises SystemExit when gt is not installed."""
        from unittest.mock import patch

        with patch("shutil.which", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                Ensure.gt_authenticated()
            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Graphite CLI (gt) is not installed" in captured.err
        assert "graphite.dev/docs/install" in captured.err

    def test_exits_when_gt_not_authenticated(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ensure.gt_authenticated raises SystemExit when gt is not authenticated."""
        from unittest.mock import MagicMock, patch

        with patch("shutil.which", return_value="/usr/local/bin/gt"):
            # Mock subprocess.run to return failure (gt is not authenticated)
            mock_result = MagicMock()
            mock_result.returncode = 1
            with patch("subprocess.run", return_value=mock_result):
                with pytest.raises(SystemExit) as exc_info:
                    Ensure.gt_authenticated()
                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Graphite CLI (gt) is not authenticated" in captured.err
        assert "gt auth --token" in captured.err
        assert "app.graphite.dev/activate" in captured.err
