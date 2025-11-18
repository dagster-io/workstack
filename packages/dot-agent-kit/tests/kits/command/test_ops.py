"""Layer 2 tests: Adapter implementation tests with mocking."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dot_agent_kit.data.kits.command.kit_cli_commands.command.ops import (
    FakeClaudeCliOps,
    RealClaudeCliOps,
)


class TestRealClaudeCliOps:
    """Layer 2: Test real implementation with mocked subprocess."""

    def test_successful_execution_with_subprocess(self) -> None:
        """Test that RealClaudeCliOps correctly invokes subprocess."""
        ops = RealClaudeCliOps()

        # Mock subprocess.run to return success
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify result
            assert result.returncode == 0

            # Verify subprocess.run was called correctly
            mock_run.assert_called_once()
            call_args = mock_run.call_args

            # Check command arguments
            cmd = call_args[0][0]
            assert cmd[0] == "claude"
            assert "--print" in cmd
            assert "--permission-mode" in cmd
            assert "bypassPermissions" in cmd
            assert "--setting-sources" in cmd
            assert "project" in cmd
            assert "/test" in cmd

            # Check keyword arguments
            assert call_args[1]["check"] is False
            assert call_args[1]["cwd"] == Path("/fake/path")

    def test_failed_execution_with_subprocess(self) -> None:
        """Test that RealClaudeCliOps propagates non-zero exit codes."""
        ops = RealClaudeCliOps()

        # Mock subprocess.run to return failure
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            result = ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify exit code propagated
            assert result.returncode == 1

    def test_json_output_flag_passed_to_subprocess(self) -> None:
        """Test that json_output=True adds --output-format json to command."""
        ops = RealClaudeCliOps()

        # Mock subprocess.run
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            ops.execute_command(
                command_name="test",
                cwd=Path("/fake/path"),
                json_output=True,
            )

            # Verify --output-format json in command
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert "--output-format" in cmd
            assert "json" in cmd

    def test_namespaced_command_passed_to_subprocess(self) -> None:
        """Test that namespaced commands are passed correctly."""
        ops = RealClaudeCliOps()

        # Mock subprocess.run
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            ops.execute_command(
                command_name="gt:submit-branch",
                cwd=Path("/fake/path"),
                json_output=False,
            )

            # Verify namespace in command
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            assert "/gt:submit-branch" in cmd

    def test_file_not_found_error_propagates(self) -> None:
        """Test that FileNotFoundError is propagated when claude binary not found."""
        ops = RealClaudeCliOps()

        # Mock subprocess.run to raise FileNotFoundError
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                ops.execute_command(
                    command_name="test",
                    cwd=Path("/fake/path"),
                    json_output=False,
                )


class TestFakeClaudeCliOps:
    """Layer 1: Test fake implementation itself."""

    def test_records_executions(self) -> None:
        """Test that fake records all executions."""
        fake = FakeClaudeCliOps()

        # Execute multiple times
        fake.execute_command("test1", Path("/path1"), False)
        fake.execute_command("test2", Path("/path2"), True)

        # Verify executions recorded
        assert fake.get_execution_count() == 2
        assert len(fake.executions) == 2

        # Verify details
        assert fake.executions[0] == ("test1", Path("/path1"), False)
        assert fake.executions[1] == ("test2", Path("/path2"), True)

    def test_get_last_execution(self) -> None:
        """Test get_last_execution returns most recent execution."""
        fake = FakeClaudeCliOps()

        # Initially no executions
        assert fake.get_last_execution() is None

        # Execute
        fake.execute_command("test", Path("/path"), False)

        # Verify last execution
        last = fake.get_last_execution()
        assert last == ("test", Path("/path"), False)

    def test_configured_returncode(self) -> None:
        """Test that configured return code is returned."""
        fake = FakeClaudeCliOps()

        # Default is 0
        result = fake.execute_command("test", Path("/path"), False)
        assert result.returncode == 0

        # Configure to return 1
        fake.set_next_returncode(1)
        result = fake.execute_command("test", Path("/path"), False)
        assert result.returncode == 1

    def test_file_not_found_error(self) -> None:
        """Test that fake can be configured to raise FileNotFoundError."""
        fake = FakeClaudeCliOps()

        # Default does not raise
        fake.execute_command("test", Path("/path"), False)

        # Configure to raise
        fake.set_file_not_found_error(True)
        with pytest.raises(FileNotFoundError):
            fake.execute_command("test", Path("/path"), False)

    def test_executions_property_returns_copy(self) -> None:
        """Test that executions property returns a copy, not original list."""
        fake = FakeClaudeCliOps()

        fake.execute_command("test", Path("/path"), False)

        # Get executions
        executions1 = fake.executions
        executions2 = fake.executions

        # Should be equal but not same object
        assert executions1 == executions2
        assert executions1 is not executions2

        # Modifying returned list should not affect internal state
        executions1.clear()
        assert fake.get_execution_count() == 1
