"""Extract implementation plans from Claude session files.

This module provides functionality to extract plans from Claude Code sessions.
Plans are stored in ~/.claude/plans/{slug}.md files, and sessions reference
them via a 'slug' field in the session JSONL.

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


def get_plans_dir() -> Path:
    """Return the Claude plans directory path.

    Returns:
        Path to ~/.claude/plans/
    """
    return Path.home() / ".claude" / "plans"


def get_plan_slug_from_session(project_dir: Path, session_id: str | None = None) -> str | None:
    """Extract plan slug from Claude session files.

    Searches session JSONL for entries with a 'slug' field, which indicates
    a plan was created during the session.

    Args:
        project_dir: Path to Claude project directory
        session_id: Optional session ID to search within

    Returns:
        Plan slug string, or None if no slug found
    """
    # Check if project directory exists
    if not project_dir.exists():
        return None

    # Determine which files to search
    if session_id:
        files = [project_dir / f"{session_id}.jsonl"]
    else:
        # Search all session files sorted by modification time (most recent first)
        files = sorted(
            [f for f in project_dir.glob("*.jsonl") if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

    # Search for slug field
    for session_file in files:
        if not session_file.exists():
            continue
        with open(session_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    slug = data.get("slug")
                    if slug:
                        return slug
                except json.JSONDecodeError:
                    continue
    return None


def get_plan_from_slug(slug: str) -> str | None:
    """Read plan content from the Claude plans folder.

    Args:
        slug: Plan slug (e.g., "joyful-munching-hammock")

    Returns:
        Plan content as string, or None if plan file doesn't exist
    """
    plan_path = get_plans_dir() / f"{slug}.md"
    if not plan_path.exists():
        return None
    return plan_path.read_text(encoding="utf-8")


def get_latest_plan(working_dir: str, session_id: str | None = None) -> str | None:
    """Extract the latest plan from Claude session for the current project.

    Looks for slug in session JSONL, reads plan from ~/.claude/plans/{slug}.md

    Args:
        working_dir: Current working directory
        session_id: Optional session ID to search within

    Returns:
        Plan text as markdown string, or None if no plan found
    """
    project_dir = get_claude_project_dir(working_dir)

    slug = get_plan_slug_from_session(project_dir, session_id)
    if not slug:
        return None

    return get_plan_from_slug(slug)


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
