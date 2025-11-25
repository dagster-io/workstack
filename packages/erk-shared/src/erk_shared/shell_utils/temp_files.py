"""Temporary file utilities for shell scripts."""

import os
import stat
import tempfile
import time
from pathlib import Path

# Directory for temporary shell scripts
TEMP_SCRIPT_DIR = Path(tempfile.gettempdir()) / "erk-scripts"


def write_script_to_temp(script_content: str, prefix: str = "erk-") -> Path:
    """Write a shell script to a temporary file.

    Args:
        script_content: The script content to write
        prefix: Prefix for the temporary file name

    Returns:
        Path to the created script file
    """
    TEMP_SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    # Create temp file with .sh extension
    fd, path = tempfile.mkstemp(suffix=".sh", prefix=prefix, dir=TEMP_SCRIPT_DIR)
    try:
        os.write(fd, script_content.encode())
    finally:
        os.close(fd)

    # Make executable
    script_path = Path(path)
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)

    return script_path


def cleanup_stale_scripts(max_age_seconds: int = 3600) -> int:
    """Clean up stale temporary scripts.

    Args:
        max_age_seconds: Maximum age in seconds before a script is considered stale

    Returns:
        Number of scripts cleaned up
    """
    if not TEMP_SCRIPT_DIR.exists():
        return 0

    cleaned = 0
    now = time.time()

    for script in TEMP_SCRIPT_DIR.glob("erk-*.sh"):
        try:
            age = now - script.stat().st_mtime
            if age > max_age_seconds:
                script.unlink()
                cleaned += 1
        except OSError:
            # File might have been deleted by another process
            pass

    return cleaned
