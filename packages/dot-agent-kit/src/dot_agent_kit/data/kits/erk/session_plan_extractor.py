"""Extract implementation plans from Claude plans directory.

This module provides functionality to extract plans from ~/.claude/plans/.
Plans are stored as {slug}.md files. We simply get the most recently
modified plan file.

All functions follow LBYL (Look Before You Leap) patterns and handle
errors explicitly at boundaries.
"""

import os
from pathlib import Path


def get_plans_dir() -> Path:
    """Return the Claude plans directory path.

    Returns:
        Path to ~/.claude/plans/
    """
    return Path.home() / ".claude" / "plans"


def get_latest_plan(working_dir: str, session_id: str | None = None) -> str | None:
    """Get the most recently modified plan from ~/.claude/plans/.

    Args:
        working_dir: Current working directory (unused, kept for API compatibility)
        session_id: Optional session ID (unused, kept for API compatibility)

    Returns:
        Plan text as markdown string, or None if no plan found
    """
    # Silence unused parameter warnings
    _ = working_dir
    _ = session_id

    plans_dir = get_plans_dir()

    if not plans_dir.exists():
        return None

    # Get all .md files sorted by modification time (most recent first)
    plan_files = sorted(
        [f for f in plans_dir.glob("*.md") if f.is_file()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if not plan_files:
        return None

    # Return content of most recent plan
    return plan_files[0].read_text(encoding="utf-8")


def get_session_context() -> str | None:
    """Extract current session ID from environment if available.

    Claude Code sets SESSION_CONTEXT with format: session_id=<uuid>
    Also checks CLAUDE_SESSION_ID for backward compatibility.

    Returns:
        Session ID string or None if not in a Claude session
    """
    # Check for SESSION_CONTEXT (Claude Code format: session_id=<uuid>)
    session_context = os.environ.get("SESSION_CONTEXT")
    if session_context and "session_id=" in session_context:
        # Extract session_id from "session_id=<uuid>" format
        parts = session_context.split("session_id=")
        if len(parts) > 1:
            session_id = parts[1].strip()
            if session_id:
                return session_id

    # Check for CLAUDE_SESSION_ID (legacy format)
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if session_id:
        return session_id

    # Not in a Claude session
    return None
