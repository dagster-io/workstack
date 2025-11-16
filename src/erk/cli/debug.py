"""Debug logging utilities for workstack.

Provides debug logging functionality when WORKSTACK_DEBUG=1 is set.
Debug logs are written to /tmp/workstack-debug.log for troubleshooting.
"""

import os
from datetime import datetime
from pathlib import Path


def is_debug() -> bool:
    """Check if debug mode is enabled via WORKSTACK_DEBUG environment variable."""
    return os.getenv("WORKSTACK_DEBUG") == "1"


def debug_log(message: str) -> None:
    """Write a timestamped debug message to the debug log file.

    Only writes if WORKSTACK_DEBUG=1 is set in the environment.
    Logs are appended to /tmp/workstack-debug.log.

    Args:
        message: The debug message to log
    """
    if not is_debug():
        return

    log_file = Path("/tmp/workstack-debug.log")
    timestamp = datetime.now().isoformat()

    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
