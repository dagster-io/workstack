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


def construct_claude_project_name(working_dir: str) -> str:
    """Convert working directory path to Claude project directory name.

    Claude converts all special characters (slashes, dots, etc.) to hyphens
    when creating project directory names.

    Args:
        working_dir: Absolute path to working directory

    Returns:
        Project directory name with leading hyphen

    Example:
        >>> construct_claude_project_name("/Users/schrockn/code/erk")
        '-Users-schrockn-code-erk'
        >>> construct_claude_project_name("/Users/schrockn/.erk/repos/erk")
        '-Users-schrockn--erk-repos-erk'
        >>> construct_claude_project_name("/Users/schrockn/.config/app")
        '-Users-schrockn--config-app'
    """
    # Replace slashes and dots with hyphens, then prepend with hyphen
    # Claude converts all special characters to hyphens when creating project directories
    return "-" + working_dir.replace("/", "-").replace(".", "-").lstrip("-")


def get_claude_project_dir(working_dir: str) -> Path:
    """Convert working directory to Claude project directory path.

    Args:
        working_dir: Current working directory (e.g., "/Users/schrockn/code/erk")

    Returns:
        Path to Claude project directory

    Example:
        >>> get_claude_project_dir("/Users/schrockn/code/erk")
        Path('/Users/schrockn/.claude/projects/-Users-schrockn-code-erk')
        >>> get_claude_project_dir("/Users/schrockn/.erk/repos/erk")
        Path('/Users/schrockn/.claude/projects/-Users-schrockn--erk-repos-erk')
    """
    # Get Claude base directory from home
    claude_base = Path.home() / ".claude" / "projects"

    # Convert working directory to project name
    project_name = construct_claude_project_name(working_dir)

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

    Searches all session files including agent subprocess files for ExitPlanMode entries.
    Plans can be created in Plan agent subprocesses, so agent files must be included.

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
        # Search all session files including agent files
        # Agent files may contain plans created in Plan agent subprocesses
        # Sort files by modification time (most recent first) for efficiency
        files = sorted(
            [f for f in project_dir.glob("*.jsonl") if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

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
