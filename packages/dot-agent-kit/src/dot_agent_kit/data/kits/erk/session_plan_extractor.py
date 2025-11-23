"""Extract implementation plans from Claude session files.

This module provides functionality to parse Claude session JSONL files and
extract the latest ExitPlanMode plan text. It supports both current-session
and all-sessions search modes for maximum flexibility.

All functions follow LBYL (Look Before You Leap) patterns and handle
errors explicitly at boundaries.
"""

import json
import os
from pathlib import Path


def get_claude_project_dir(working_dir: str) -> Path:
    """Convert working directory to Claude project directory path.

    Args:
        working_dir: Current working directory (e.g., "/Users/schrockn/code/erk")

    Returns:
        Path to Claude project directory

    Example:
        >>> get_claude_project_dir("/Users/schrockn/code/erk")
        Path('/Users/schrockn/.claude/projects/-Users-schrockn-code-erk')
    """
    # Replace slashes with hyphens and prepend with hyphen
    project_name = "-" + working_dir.replace("/", "-").lstrip("-")

    # Get Claude base directory from home
    claude_base = Path.home() / ".claude" / "projects"

    return claude_base / project_name


def extract_plan_from_session_line(data: dict) -> str | None:
    """Extract plan text from a single session line if it contains ExitPlanMode.

    Args:
        data: Parsed JSON object from session file line

    Returns:
        Plan text if found, None otherwise
    """
    # Check if this line has message content
    if "message" not in data:
        return None

    message = data.get("message", {})
    if "content" not in message:
        return None

    content = message.get("content", [])
    if not isinstance(content, list):
        return None

    # Look for ExitPlanMode tool use
    for item in content:
        if not isinstance(item, dict):
            continue

        # Check if this is ExitPlanMode tool use
        if item.get("type") == "tool_use" and item.get("name") == "ExitPlanMode":
            # Extract plan from input
            input_data = item.get("input", {})
            if isinstance(input_data, dict) and "plan" in input_data:
                plan_text = input_data.get("plan")
                if plan_text and isinstance(plan_text, str):
                    return plan_text

    return None


def get_latest_plan_from_session(project_dir: Path, session_id: str | None = None) -> str | None:
    """Extract the latest plan from Claude session files.

    Args:
        project_dir: Path to Claude project directory (e.g., -Users-schrockn-code-erk)
        session_id: Optional session ID to search within. If None, searches all sessions.

    Returns:
        Plan text as markdown string, or None if no plan found
    """
    plans = []

    # Check if project directory exists
    if not project_dir.exists():
        return None

    # Determine which files to search
    if session_id:
        # Search only the specified session
        files = [project_dir / f"{session_id}.jsonl"]
    else:
        # Search all session files, excluding agent files
        files = [
            f
            for f in project_dir.glob("*.jsonl")
            if f.is_file() and not f.name.startswith("agent-")
        ]

    # Search for ExitPlanMode occurrences
    for session_file in files:
        if not session_file.exists():
            continue

        # Read and parse each line of the JSONL file
        with open(session_file, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                # Parse JSON line
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue

                # Try to extract plan from this line
                plan_text = extract_plan_from_session_line(data)
                if plan_text:
                    # Add to plans list with timestamp for sorting
                    timestamp = data.get("timestamp", "")
                    plans.append(
                        {
                            "timestamp": timestamp,
                            "plan": plan_text,
                            "session_id": session_file.stem,
                            "line_num": line_num,
                        }
                    )

    # Return most recent plan by timestamp
    if not plans:
        return None

    # Sort by timestamp (most recent first)
    plans.sort(key=lambda x: x["timestamp"], reverse=True)
    return plans[0]["plan"]


def get_latest_plan(working_dir: str, session_id: str | None = None) -> str | None:
    """Extract the latest plan from Claude session for the current project.

    This is the main entry point for extracting plans from session files.

    Args:
        working_dir: Current working directory
        session_id: Optional session ID to search within

    Returns:
        Plan text as markdown string, or None if no plan found
    """
    # Get Claude project directory
    project_dir = get_claude_project_dir(working_dir)

    # Extract latest plan
    return get_latest_plan_from_session(project_dir, session_id)


def get_session_context() -> str | None:
    """Extract current session ID from environment if available.

    Returns:
        Session ID string or None if not in a Claude session
    """
    # Check for session ID in environment
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if session_id:
        return session_id

    # Could also check for session context files or other indicators
    # For now, return None if not found
    return None
