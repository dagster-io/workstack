"""Output filtering for Claude CLI stream-json format.

This module provides functions to parse and filter Claude CLI output in stream-json
format, extracting relevant text content and tool summaries while suppressing
verbose/noisy tool invocations.
"""

import json
from pathlib import Path


def extract_text_content(message: dict) -> str | None:
    """Extract Claude's text response from assistant message.

    Args:
        message: Assistant message dict from stream-json

    Returns:
        Extracted text content, or None if no text found

    Example:
        >>> msg = {"type": "assistant_message", "content": [{"type": "text", "text": "Hello"}]}
        >>> extract_text_content(msg)
        'Hello'
    """
    content = message.get("content", [])
    if not isinstance(content, list):
        return None

    text_parts: list[str] = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())

    if not text_parts:
        return None

    return "\n".join(text_parts)


def summarize_tool_use(tool_use: dict, worktree_path: Path) -> str | None:
    """Create brief summary for important tools, None for suppressible tools.

    Args:
        tool_use: Tool use dict from stream-json content
        worktree_path: Path to worktree for relativizing file paths

    Returns:
        Brief summary string for important tools, None for suppressible tools

    Example:
        >>> tool = {"name": "Edit", "input": {"file_path": "/repo/src/file.py"}}
        >>> summarize_tool_use(tool, Path("/repo"))
        'Editing src/file.py...'
    """
    tool_name = tool_use.get("name")
    if not isinstance(tool_name, str):
        return None

    params = tool_use.get("input", {})
    if not isinstance(params, dict):
        params = {}

    # Suppress common/noisy tools
    if tool_name in ["Read", "Glob", "Grep"]:
        return None

    # Bash commands
    if tool_name == "Bash":
        command = params.get("command", "")
        if not isinstance(command, str):
            return None

        # Check for pytest
        if "pytest" in command:
            return "Running tests..."

        # Check for CI commands
        if "fast-ci" in command or "all-ci" in command:
            return "Running CI checks..."

        # Generic bash command
        return f"Running: {command[:50]}..."

    # Slash commands
    if tool_name == "SlashCommand":
        cmd = params.get("command", "")
        if not isinstance(cmd, str):
            return None

        if "/gt:submit-pr" in cmd or "/git:push-pr" in cmd:
            return "Creating pull request..."

        if "/fast-ci" in cmd or "/all-ci" in cmd:
            return "Running CI checks..."

        return f"Running {cmd}..."

    # File operations
    if tool_name == "Edit":
        filepath = params.get("file_path", "")
        if isinstance(filepath, str):
            relative = make_relative_to_worktree(filepath, worktree_path)
            return f"Editing {relative}..."

    if tool_name == "Write":
        filepath = params.get("file_path", "")
        if isinstance(filepath, str):
            relative = make_relative_to_worktree(filepath, worktree_path)
            return f"Writing {relative}..."

    # Default: show tool name for unknown tools
    return f"Using {tool_name}..."


def make_relative_to_worktree(filepath: str, worktree_path: Path) -> str:
    """Convert absolute path to worktree-relative path.

    Args:
        filepath: Absolute or relative file path
        worktree_path: Path to worktree root

    Returns:
        Path relative to worktree if possible, otherwise original filepath

    Example:
        >>> make_relative_to_worktree("/repo/src/file.py", Path("/repo"))
        'src/file.py'
    """
    path = Path(filepath)

    # Check if path is absolute and relative to worktree
    if path.is_absolute():
        if path.exists() and path.is_relative_to(worktree_path):
            return str(path.relative_to(worktree_path))

    return filepath


def extract_pr_url(tool_result_content: str) -> str | None:
    """Extract PR URL from simple_submit JSON output.

    Args:
        tool_result_content: Content string from tool_result

    Returns:
        PR URL if found in JSON, None otherwise

    Example:
        >>> content = '{"success": true, "pr_url": "https://github.com/user/repo/pull/123"}'
        >>> extract_pr_url(content)
        'https://github.com/user/repo/pull/123'
    """
    if not isinstance(tool_result_content, str):
        return None

    # Parse JSON safely - JSON parsing requires exception handling
    data: dict | None = None
    if tool_result_content.strip():
        try:
            parsed = json.loads(tool_result_content)
            if isinstance(parsed, dict):
                data = parsed
        except json.JSONDecodeError:
            return None

    if data is None:
        return None

    pr_url = data.get("pr_url")
    if isinstance(pr_url, str):
        return pr_url

    return None


def determine_spinner_status(tool_use: dict | None, command: str, worktree_path: Path) -> str:
    """Map current activity to spinner status message.

    Args:
        tool_use: Current tool use dict, or None if no tool running
        command: The slash command being executed
        worktree_path: Path to worktree for relativizing paths

    Returns:
        Status message for spinner

    Example:
        >>> determine_spinner_status(None, "/erk:implement-plan", Path("/repo"))
        'Running /erk:implement-plan...'
    """
    if tool_use is None:
        return f"Running {command}..."

    summary = summarize_tool_use(tool_use, worktree_path)
    if summary:
        return summary

    return f"Running {command}..."
