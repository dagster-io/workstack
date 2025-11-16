"""Utilities for generating shell integration scripts."""

import os
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path

from erk.cli.debug import debug_log

STALE_SCRIPT_MAX_AGE_SECONDS = 3600


def render_cd_script(path: Path, *, comment: str, success_message: str) -> str:
    """Generate shell script to change directory with feedback.

    Args:
        path: Target directory path to cd into.
        comment: Shell comment describing the operation.
        success_message: Message to echo after successful cd.

    Returns:
        Shell script that changes directory and shows success message.
    """
    path_str = str(path)
    quoted_path = "'" + path_str.replace("'", "'\\''") + "'"
    lines = [
        f"# {comment}",
        f"cd {quoted_path}",
        f'echo "{success_message}"',
    ]
    return "\n".join(lines) + "\n"


def write_script_to_temp(
    script_content: str,
    *,
    command_name: str,
    comment: str | None = None,
) -> Path:
    """Write shell script to temp file with unique UUID.

    Args:
        script_content: The shell script to write
        command_name: Command that generated this (e.g., 'sync', 'switch', 'create')
        comment: Optional comment to include in script header

    Returns:
        Path to the temp file

    Filename format: erk-{command}-{uuid}.sh
    """
    unique_id = uuid.uuid4().hex[:8]  # 8 chars sufficient (4 billion combinations)
    temp_dir = Path(tempfile.gettempdir())
    temp_file = temp_dir / f"erk-{command_name}-{unique_id}.sh"

    # Add metadata header
    header = [
        "#!/bin/bash",
        f"# erk {command_name}",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"# UUID: {unique_id}",
        f"# User: {os.getenv('USER', 'unknown')}",
        f"# Working dir: {Path.cwd()}",
    ]

    if comment:
        header.append(f"# {comment}")

    header.append("")  # Blank line before script

    full_content = "\n".join(header) + "\n" + script_content
    temp_file.write_text(full_content, encoding="utf-8")

    # Make executable for good measure
    temp_file.chmod(0o755)

    debug_log(f"write_script_to_temp: Created {temp_file}")
    debug_log(f"write_script_to_temp: Content:\n{full_content}")

    return temp_file


def cleanup_stale_scripts(*, max_age_seconds: int = STALE_SCRIPT_MAX_AGE_SECONDS) -> None:
    """Remove erk temp scripts older than max_age_seconds.

    Args:
        max_age_seconds: Maximum age before cleanup (default 1 hour)
    """
    temp_dir = Path(tempfile.gettempdir())
    cutoff = time.time() - max_age_seconds

    for script_file in temp_dir.glob("erk-*.sh"):
        if script_file.exists():
            try:
                if script_file.stat().st_mtime < cutoff:
                    script_file.unlink()
            except (FileNotFoundError, PermissionError):
                # Scripts may disappear between stat/unlink or be owned by another user.
                continue
