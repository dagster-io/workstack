"""Tests for ScriptResult output methods."""

import sys
from io import StringIO
from pathlib import Path

from workstack.core.script_writer import ScriptResult


def test_output_for_shell_integration_routes_to_stdout() -> None:
    """Test that output_for_shell_integration() routes to stdout."""
    # Arrange
    result = ScriptResult(
        path=Path("/tmp/test_script.sh"),
        content="#!/bin/bash\necho 'test'",
    )

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        # Act
        result.output_for_shell_integration()

        # Assert
        output = sys.stdout.getvalue()
        assert output == "/tmp/test_script.sh"
    finally:
        sys.stdout = old_stdout


def test_output_path_for_user_routes_to_stderr() -> None:
    """Test that output_path_for_user() routes to stderr."""
    # Arrange
    result = ScriptResult(
        path=Path("/tmp/test_script.sh"),
        content="#!/bin/bash\necho 'test'",
    )

    # Capture stderr
    old_stderr = sys.stderr
    sys.stderr = StringIO()

    try:
        # Act
        result.output_path_for_user()

        # Assert
        output = sys.stderr.getvalue()
        assert output == "/tmp/test_script.sh"
    finally:
        sys.stderr = old_stderr


def test_idempotency_prevents_duplicate_output() -> None:
    """Test that calling output methods multiple times only outputs once."""
    # Arrange
    result = ScriptResult(
        path=Path("/tmp/test_script.sh"),
        content="#!/bin/bash\necho 'test'",
    )

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        # Act - call twice
        result.output_for_shell_integration()
        result.output_for_shell_integration()

        # Assert - only one output
        output = sys.stdout.getvalue()
        assert output == "/tmp/test_script.sh"
        assert output.count("/tmp/test_script.sh") == 1
    finally:
        sys.stdout = old_stdout


def test_path_access_still_works() -> None:
    """Test backward compatibility - path attribute still accessible."""
    # Arrange
    result = ScriptResult(
        path=Path("/tmp/test_script.sh"),
        content="#!/bin/bash\necho 'test'",
    )

    # Act & Assert
    assert result.path == Path("/tmp/test_script.sh")
    assert str(result.path) == "/tmp/test_script.sh"


def test_fake_script_writer_integration() -> None:
    """Test that ScriptResult works with FakeScriptWriterOps."""
    from tests.fakes.script_writer import FakeScriptWriterOps

    # Arrange
    fake_ops = FakeScriptWriterOps()

    # Act
    result = fake_ops.write_activation_script(
        "cd /some/path",
        command_name="test",
        comment="test script",
    )

    # Assert - result should have new methods
    assert hasattr(result, "output_for_shell_integration")
    assert hasattr(result, "output_path_for_user")
    assert result.path.name.startswith("workstack-test-")


def test_str_method_returns_path() -> None:
    """Test that __str__() returns string representation of path."""
    # Arrange
    result = ScriptResult(
        path=Path("/tmp/test_script.sh"),
        content="#!/bin/bash\necho 'test'",
    )

    # Act & Assert
    assert str(result) == "/tmp/test_script.sh"
