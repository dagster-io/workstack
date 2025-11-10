"""Tests for shell integration output utilities."""

import sys
from io import StringIO

from workstack.cli.shell_integration.output import script_mode_echo


def test_script_mode_routes_to_stderr() -> None:
    """Test that script_mode=True routes output to stderr."""
    # Save original stderr/stdout
    original_stderr = sys.stderr
    original_stdout = sys.stdout
    captured_stderr = StringIO()
    captured_stdout = StringIO()

    try:
        sys.stderr = captured_stderr
        sys.stdout = captured_stdout

        # Call with script_mode=True
        script_mode_echo("test message", script_mode=True)

        # Check output went to stderr
        assert captured_stderr.getvalue() == "test message\n"
        assert captured_stdout.getvalue() == ""
    finally:
        sys.stderr = original_stderr
        sys.stdout = original_stdout


def test_non_script_mode_routes_to_stdout() -> None:
    """Test that script_mode=False routes output to stdout."""
    import sys
    from io import StringIO

    original_stderr = sys.stderr
    original_stdout = sys.stdout
    captured_stderr = StringIO()
    captured_stdout = StringIO()

    try:
        sys.stderr = captured_stderr
        sys.stdout = captured_stdout

        # Call with script_mode=False
        script_mode_echo("test message", script_mode=False)

        # Check output went to stdout
        assert captured_stdout.getvalue() == "test message\n"
        assert captured_stderr.getvalue() == ""
    finally:
        sys.stderr = original_stderr
        sys.stdout = original_stdout


def test_error_flag_forces_stderr_in_non_script_mode() -> None:
    """Test that error=True forces stderr even when script_mode=False."""
    import sys
    from io import StringIO

    original_stderr = sys.stderr
    original_stdout = sys.stdout
    captured_stderr = StringIO()
    captured_stdout = StringIO()

    try:
        sys.stderr = captured_stderr
        sys.stdout = captured_stdout

        # Call with script_mode=False but error=True
        script_mode_echo("error message", script_mode=False, error=True)

        # Check output went to stderr
        assert captured_stderr.getvalue() == "error message\n"
        assert captured_stdout.getvalue() == ""
    finally:
        sys.stderr = original_stderr
        sys.stdout = original_stdout
