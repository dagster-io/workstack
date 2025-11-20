"""Tests for subprocess wrapper with rich error context."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from erk.core.subprocess import run_subprocess_with_context


def test_success_case_returns_completed_process() -> None:
    """Test that successful subprocess execution returns CompletedProcess."""
    with patch("erk.core.subprocess.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_result.stdout = "success output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Execute
        result = run_subprocess_with_context(
            ["git", "status"],
            operation_context="check git status",
            cwd=Path("/repo"),
        )

        # Verify
        assert result == mock_result
        assert result.returncode == 0
        assert result.stdout == "success output"

        # Verify subprocess.run was called with correct parameters
        mock_run.assert_called_once_with(
            ["git", "status"],
            cwd=Path("/repo"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )


def test_failure_with_stderr_includes_stderr_in_error() -> None:
    """Test that subprocess failure with stderr includes stderr in error message."""
    with patch("erk.core.subprocess.subprocess.run") as mock_run:
        # Setup failed execution with stderr
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "checkout", "nonexistent"],
            stderr="error: pathspec 'nonexistent' did not match any file(s) known to git",
        )
        mock_run.side_effect = error

        # Execute and verify exception
        with pytest.raises(RuntimeError) as exc_info:
            run_subprocess_with_context(
                ["git", "checkout", "nonexistent"],
                operation_context="checkout branch 'nonexistent'",
                cwd=Path("/repo"),
            )

        # Verify error message contains all expected parts
        error_message = str(exc_info.value)
        assert "Failed to checkout branch 'nonexistent'" in error_message
        assert "Command: git checkout nonexistent" in error_message
        assert "Exit code: 1" in error_message
        assert (
            "stderr: error: pathspec 'nonexistent' did not match any file(s) known to git"
            in error_message
        )


def test_failure_without_stderr_handles_gracefully() -> None:
    """Test that subprocess failure without stderr still produces useful error."""
    with patch("erk.core.subprocess.subprocess.run") as mock_run:
        # Setup failed execution without stderr
        error = subprocess.CalledProcessError(
            returncode=127,
            cmd=["nonexistent-command"],
            stderr=None,
        )
        mock_run.side_effect = error

        # Execute and verify exception
        with pytest.raises(RuntimeError) as exc_info:
            run_subprocess_with_context(
                ["nonexistent-command"],
                operation_context="run nonexistent command",
            )

        # Verify error message contains command and exit code but not stderr
        error_message = str(exc_info.value)
        assert "Failed to run nonexistent command" in error_message
        assert "Command: nonexistent-command" in error_message
        assert "Exit code: 127" in error_message
        # Should not have stderr line when stderr is None
        assert "stderr:" not in error_message


def test_failure_with_empty_stderr_omits_stderr_line() -> None:
    """Test that subprocess failure with empty stderr omits the stderr line."""
    with patch("erk.core.subprocess.subprocess.run") as mock_run:
        # Setup failed execution with empty stderr
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["command"],
            stderr="   \n  ",  # Whitespace only
        )
        mock_run.side_effect = error

        # Execute and verify exception
        with pytest.raises(RuntimeError) as exc_info:
            run_subprocess_with_context(
                ["command"],
                operation_context="run command",
            )

        # Verify error message omits stderr when it's only whitespace
        error_message = str(exc_info.value)
        assert "Failed to run command" in error_message
        assert "Command: command" in error_message
        assert "Exit code: 1" in error_message
        assert "stderr:" not in error_message


def test_exception_chaining_preserved() -> None:
    """Test that original CalledProcessError is preserved via exception chaining."""
    with patch("erk.core.subprocess.subprocess.run") as mock_run:
        # Setup failed execution
        original_error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "status"],
            stderr="fatal: not a git repository",
        )
        mock_run.side_effect = original_error

        # Execute and verify exception chaining
        with pytest.raises(RuntimeError) as exc_info:
            run_subprocess_with_context(
                ["git", "status"],
                operation_context="check git status",
            )

        # Verify original exception is preserved as __cause__
        assert exc_info.value.__cause__ is original_error
        assert isinstance(exc_info.value.__cause__, subprocess.CalledProcessError)


def test_parameter_pass_through() -> None:
    """Test that all kwargs are correctly passed through to subprocess.run."""
    with patch("erk.core.subprocess.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Execute with custom kwargs
        run_subprocess_with_context(
            ["echo", "test"],
            operation_context="echo test",
            cwd=Path("/tmp"),
            timeout=30,
            env={"VAR": "value"},
        )

        # Verify all parameters including custom kwargs were passed
        mock_run.assert_called_once_with(
            ["echo", "test"],
            cwd=Path("/tmp"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=30,
            env={"VAR": "value"},
        )


def test_check_false_behavior_no_exception() -> None:
    """Test that check=False prevents exception on non-zero exit."""
    with patch("erk.core.subprocess.subprocess.run") as mock_run:
        # Setup failed execution but with check=False
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 1
        mock_result.stderr = "some error"
        mock_run.return_value = mock_result

        # Execute with check=False - should NOT raise
        result = run_subprocess_with_context(
            ["command"],
            operation_context="run command",
            check=False,
        )

        # Verify result returned without exception
        assert result == mock_result
        assert result.returncode == 1


def test_custom_encoding_parameter() -> None:
    """Test that custom encoding parameter is passed through."""
    with patch("erk.core.subprocess.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Execute with custom encoding
        run_subprocess_with_context(
            ["cat", "file.txt"],
            operation_context="read file",
            encoding="latin-1",
        )

        # Verify custom encoding was used
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["encoding"] == "latin-1"


def test_capture_output_false_parameter() -> None:
    """Test that capture_output=False is passed through correctly."""
    with patch("erk.core.subprocess.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Execute with capture_output=False
        run_subprocess_with_context(
            ["echo", "test"],
            operation_context="echo test",
            capture_output=False,
        )

        # Verify capture_output=False was used
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["capture_output"] is False


def test_text_false_parameter() -> None:
    """Test that text=False is passed through correctly."""
    with patch("erk.core.subprocess.subprocess.run") as mock_run:
        # Setup successful execution
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Execute with text=False
        run_subprocess_with_context(
            ["command"],
            operation_context="run command",
            text=False,
        )

        # Verify text=False was used
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["text"] is False
