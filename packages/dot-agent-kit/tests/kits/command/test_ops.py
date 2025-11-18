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
        """Test that RealClaudeCliOps correctly invokes subprocess with streaming."""
        ops = RealClaudeCliOps()

        # Mock subprocess.Popen to return success with JSONL output
        mock_process = MagicMock()
        mock_process.stdout = iter([])  # Empty output for this test
        mock_process.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            with patch("builtins.print") as mock_print:
                result = ops.execute_command(
                    command_name="test",
                    cwd=Path("/fake/path"),
                    json_output=False,
                )

                # Verify result
                assert result.returncode == 0

                # Verify status message was printed
                mock_print.assert_called_once_with("Executing command: /test...", flush=True)

                # Verify subprocess.Popen was called correctly
                mock_popen.assert_called_once()
                call_args = mock_popen.call_args

                # Check command arguments include stream-json and verbose
                cmd = call_args[0][0]
                assert cmd[0] == "claude"
                assert "--print" in cmd
                assert "--verbose" in cmd
                assert "--permission-mode" in cmd
                assert "bypassPermissions" in cmd
                assert "--setting-sources" in cmd
                assert "project" in cmd
                assert "--output-format" in cmd
                assert "stream-json" in cmd
                assert "/test" in cmd

                # Check keyword arguments
                assert call_args[1]["cwd"] == Path("/fake/path")
                assert call_args[1]["stdout"] is not None
                assert call_args[1]["stderr"] is not None
                assert call_args[1]["text"] is True
                assert call_args[1]["bufsize"] == 1

    def test_failed_execution_with_subprocess(self) -> None:
        """Test that RealClaudeCliOps propagates non-zero exit codes."""
        ops = RealClaudeCliOps()

        # Mock subprocess.Popen to return failure
        mock_process = MagicMock()
        mock_process.stdout = iter([])  # Empty output
        mock_process.wait.return_value = 1

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("builtins.print"):
                result = ops.execute_command(
                    command_name="test",
                    cwd=Path("/fake/path"),
                    json_output=False,
                )

                # Verify exit code propagated
                assert result.returncode == 1

    def test_always_uses_stream_json_format(self) -> None:
        """Test that stream-json is always used regardless of json_output parameter."""
        ops = RealClaudeCliOps()

        # Mock subprocess.Popen
        mock_process = MagicMock()
        mock_process.stdout = iter([])  # Empty output
        mock_process.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            with patch("builtins.print"):
                # Test with json_output=True
                ops.execute_command(
                    command_name="test",
                    cwd=Path("/fake/path"),
                    json_output=True,
                )

                # Verify --output-format stream-json in command
                call_args = mock_popen.call_args
                cmd = call_args[0][0]
                assert "--output-format" in cmd
                assert "stream-json" in cmd

                # Reset mock
                mock_popen.reset_mock()

                # Test with json_output=False - should still use stream-json
                ops.execute_command(
                    command_name="test2",
                    cwd=Path("/fake/path"),
                    json_output=False,
                )

                # Verify stream-json still used
                call_args = mock_popen.call_args
                cmd = call_args[0][0]
                assert "--output-format" in cmd
                assert "stream-json" in cmd

    def test_namespaced_command_passed_to_subprocess(self) -> None:
        """Test that namespaced commands are passed correctly."""
        ops = RealClaudeCliOps()

        # Mock subprocess.Popen
        mock_process = MagicMock()
        mock_process.stdout = iter([])  # Empty output
        mock_process.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
            with patch("builtins.print"):
                ops.execute_command(
                    command_name="gt:submit-branch",
                    cwd=Path("/fake/path"),
                    json_output=False,
                )

                # Verify namespace in command
                call_args = mock_popen.call_args
                cmd = call_args[0][0]
                assert "/gt:submit-branch" in cmd

    def test_file_not_found_error_propagates(self) -> None:
        """Test that FileNotFoundError is propagated when claude binary not found."""
        ops = RealClaudeCliOps()

        # Mock subprocess.Popen to raise FileNotFoundError
        with patch("subprocess.Popen", side_effect=FileNotFoundError):
            with patch("builtins.print"):
                with pytest.raises(FileNotFoundError):
                    ops.execute_command(
                        command_name="test",
                        cwd=Path("/fake/path"),
                        json_output=False,
                    )

    def test_parses_jsonl_and_extracts_text(self) -> None:
        """Test that JSONL output is parsed and text is extracted from assistant messages."""
        import json

        ops = RealClaudeCliOps()

        # Create JSONL output with assistant messages
        jsonl_output = [
            json.dumps({"role": "assistant", "content": [{"type": "text", "text": "Hello "}]}),
            json.dumps({"role": "assistant", "content": [{"type": "text", "text": "World!"}]}),
        ]

        # Mock subprocess.Popen
        mock_process = MagicMock()
        mock_process.stdout = iter(jsonl_output)
        mock_process.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("builtins.print") as mock_print:
                result = ops.execute_command(
                    command_name="test",
                    cwd=Path("/fake/path"),
                    json_output=False,
                )

                # Verify result
                assert result.returncode == 0

                # Verify print was called for status + each text chunk
                assert mock_print.call_count == 3
                # First call: status message
                assert mock_print.call_args_list[0] == (
                    ("Executing command: /test...",),
                    {"flush": True},
                )
                # Second call: "Hello "
                assert mock_print.call_args_list[1] == (("Hello ",), {"end": "", "flush": True})
                # Third call: "World!"
                assert mock_print.call_args_list[2] == (("World!",), {"end": "", "flush": True})

    def test_handles_malformed_json_gracefully(self) -> None:
        """Test that malformed JSON lines are printed as-is without crashing."""
        ops = RealClaudeCliOps()

        # Create output with malformed JSON
        output = [
            "This is not JSON\n",
            '{"incomplete": ',
        ]

        # Mock subprocess.Popen
        mock_process = MagicMock()
        mock_process.stdout = iter(output)
        mock_process.wait.return_value = 0

        with patch("subprocess.Popen", return_value=mock_process):
            with patch("builtins.print") as mock_print:
                result = ops.execute_command(
                    command_name="test",
                    cwd=Path("/fake/path"),
                    json_output=False,
                )

                # Verify result
                assert result.returncode == 0

                # Verify print was called for status + malformed lines
                assert mock_print.call_count == 3
                # First call: status message
                assert mock_print.call_args_list[0] == (
                    ("Executing command: /test...",),
                    {"flush": True},
                )
                # Malformed lines printed as-is
                assert mock_print.call_args_list[1] == (
                    ("This is not JSON\n",),
                    {"end": "", "flush": True},
                )
                assert mock_print.call_args_list[2] == (
                    ('{"incomplete": ',),
                    {"end": "", "flush": True},
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
