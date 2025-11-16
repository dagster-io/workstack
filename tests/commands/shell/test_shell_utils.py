"""Tests for shell_utils module."""

import os
import tempfile
import time
from pathlib import Path

from erk.cli.shell_utils import cleanup_stale_scripts, write_script_to_temp


def test_write_script_to_temp() -> None:
    """Test that temp scripts are written with correct metadata."""
    script_content = "cd /foo\necho 'hello'\n"

    temp_path = write_script_to_temp(
        script_content,
        command_name="test",
        comment="test comment",
    )

    # File should exist
    assert temp_path.exists()

    # Should be in temp directory
    assert temp_path.parent == Path(tempfile.gettempdir())

    # Should have correct pattern
    assert temp_path.name.startswith("workstack-test-")
    assert temp_path.name.endswith(".sh")

    # Should contain metadata header
    content = temp_path.read_text()
    assert "#!/bin/bash" in content
    assert "# workstack test" in content
    assert "# test comment" in content
    assert script_content in content

    # Cleanup
    temp_path.unlink()


def test_cleanup_stale_scripts() -> None:
    """Test that old scripts are removed."""
    # Create an old script
    old_script = Path(tempfile.gettempdir()) / "workstack-old-12345678.sh"
    old_script.write_text("# old script\n")

    # Set mtime to 2 hours ago
    two_hours_ago = time.time() - 7200
    os.utime(old_script, (two_hours_ago, two_hours_ago))

    # Create a new script
    new_script = Path(tempfile.gettempdir()) / "workstack-new-87654321.sh"
    new_script.write_text("# new script\n")

    # Cleanup scripts older than 1 hour
    cleanup_stale_scripts(max_age_seconds=3600)

    # Old should be gone, new should remain
    assert not old_script.exists()
    assert new_script.exists()

    # Cleanup
    new_script.unlink(missing_ok=True)
