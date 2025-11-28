#!/usr/bin/env python3
"""Extract plan file name from Claude Code session.

This command searches session logs in ~/.claude/projects/ for plan file writes
and returns the plan filename.

Usage:
    # Auto-detect session from environment
    dot-agent run erk session-get-plan

    # Explicit session ID
    dot-agent run erk session-get-plan --session-id abc-123-def

    # JSON output (default)
    {
      "success": true,
      "session_id": "abc-123-def",
      "plan_filename": "ethereal-plotting-sunbeam.md",
      "plan_path": "/Users/foo/.claude/plans/ethereal-plotting-sunbeam.md"
    }

    # Plain text output (for scripting)
    dot-agent run erk session-get-plan --text
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import click


# Patterns to exclude (agent logs and temp files)
EXCLUDED_PREFIXES = ("agent-", "temp-", "tmp-", "draft-")


@dataclass
class PlanResult:
    """Success result."""

    success: bool
    session_id: str
    plan_filename: str
    plan_path: str
    warning: str | None = None


@dataclass
class PlanError:
    """Error result."""

    success: bool
    error: str
    session_id: str | None
    help: str


def _is_excluded_pattern(filename: str) -> bool:
    """Check if filename matches exclusion patterns.

    Args:
        filename: Plan filename to check

    Returns:
        True if filename should be excluded
    """
    return any(filename.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


def _looks_like_uuid(value: str) -> bool:
    """Check if string looks like a UUID.

    Args:
        value: String to check

    Returns:
        True if string looks like a UUID (lowercase hex with dashes)
    """
    # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    return bool(uuid_pattern.match(value))


def _get_session_id_from_env() -> str | None:
    """Extract session ID from SESSION_CONTEXT env var.

    The session_id_injector_hook sets SESSION_CONTEXT env var with format:
    "session_id=<uuid>" or bare UUID.

    Returns:
        Session ID if found, None otherwise
    """
    session_context = os.environ.get("SESSION_CONTEXT")
    if not session_context:
        return None

    # Format 1: "session_id=<uuid>"
    if "session_id=" in session_context:
        parts = session_context.split("session_id=")
        if len(parts) == 2:
            return parts[1].strip()

    # Format 2: Bare UUID
    if _looks_like_uuid(session_context.strip()):
        return session_context.strip()

    return None


def _find_session_file(session_id: str, projects_dir: Path) -> Path | PlanError:
    """Find session JSONL file in projects directory.

    Args:
        session_id: Session UUID to search for
        projects_dir: Path to ~/.claude/projects/

    Returns:
        Path to session file or PlanError if not found
    """
    if not projects_dir.exists():
        return PlanError(
            success=False,
            error="Projects directory not found",
            session_id=session_id,
            help=f"Directory {projects_dir} does not exist",
        )

    # Search all project directories
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        session_file = project_dir / f"{session_id}.jsonl"
        if session_file.exists() and session_file.is_file():
            return session_file

    return PlanError(
        success=False,
        error="Session file not found",
        session_id=session_id,
        help=f"Session {session_id[:8]}... not found in {projects_dir}",
    )


def _extract_plan_filename(session_file: Path) -> str | PlanError:
    """Parse JSONL and extract plan filename.

    Args:
        session_file: Path to session JSONL file

    Returns:
        Plan filename or PlanError if not found
    """
    try:
        content = session_file.read_text(encoding="utf-8")
    except OSError as e:
        return PlanError(
            success=False,
            error="Cannot read session file",
            session_id=session_file.stem,
            help=f"OS error: {e}",
        )

    # Pattern: cat > ~/.claude/plans/<name>.md
    # or: plans/<name>.md in tool result content
    # Updated to accept hyphens, underscores, and digits
    plan_pattern = re.compile(r"plans/([a-z0-9_-]+\.md)")

    found_plans: list[str] = []

    for line in content.splitlines():
        if not line.strip():
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue  # Skip malformed lines

        # Check user entries (tool results)
        if entry.get("type") == "user":
            content_str = str(entry.get("message", {}).get("content", ""))
            matches = plan_pattern.findall(content_str)

            # Filter out excluded patterns
            for match in matches:
                if not _is_excluded_pattern(match):
                    found_plans.append(match)

    if not found_plans:
        return PlanError(
            success=False,
            error="No plan file found in session",
            session_id=session_file.stem,
            help="Session may not have created a plan",
        )

    # Return last plan (most recent if multiple)
    return found_plans[-1]


def find_plan_in_session(session_id: str, projects_dir: Path) -> PlanResult | PlanError:
    """Find plan filename from session JSONL.

    Args:
        session_id: Session UUID
        projects_dir: Path to ~/.claude/projects/

    Returns:
        PlanResult with plan info or PlanError
    """
    # Step 1: Find session file
    session_file = _find_session_file(session_id, projects_dir)
    if isinstance(session_file, PlanError):
        return session_file

    # Step 2: Parse JSONL and find plan
    plan_filename = _extract_plan_filename(session_file)
    if isinstance(plan_filename, PlanError):
        return plan_filename

    # Step 3: Verify plan exists
    plan_path = Path.home() / ".claude" / "plans" / plan_filename
    warning = None if plan_path.exists() else "Plan file no longer exists"

    return PlanResult(
        success=True,
        session_id=session_id,
        plan_filename=plan_filename,
        plan_path=str(plan_path),
        warning=warning,
    )


def _output_result(result: PlanResult | PlanError, text_mode: bool) -> None:
    """Output result in requested format.

    Args:
        result: Result to output
        text_mode: If True, output plain filename only
    """
    if text_mode and isinstance(result, PlanResult):
        # Plain filename for scripting
        click.echo(result.plan_filename)
    else:
        # JSON output (default)
        if isinstance(result, PlanResult):
            output = {
                "success": result.success,
                "session_id": result.session_id,
                "plan_filename": result.plan_filename,
                "plan_path": result.plan_path,
            }
            if result.warning:
                output["warning"] = result.warning
        else:
            output = {
                "success": result.success,
                "error": result.error,
                "session_id": result.session_id,
                "help": result.help,
            }

        click.echo(json.dumps(output, indent=2))


@click.command(name="session-get-plan")
@click.option(
    "--session-id",
    type=str,
    help="Session UUID (auto-detected from SESSION_CONTEXT if not provided)",
)
@click.option(
    "--text",
    is_flag=True,
    help="Output plain filename only (for scripting)",
)
def session_get_plan(session_id: str | None, text: bool) -> None:
    """Extract plan file name from Claude Code session.

    Searches session logs in ~/.claude/projects/ for plan file writes
    and returns the plan filename.

    Examples:
        # Auto-detect from environment
        dot-agent run erk session-get-plan

        # Explicit session ID
        dot-agent run erk session-get-plan --session-id abc-123

        # Plain text output
        dot-agent run erk session-get-plan --text
    """
    # Resolve session ID
    if not session_id:
        session_id = _get_session_id_from_env()

    if not session_id:
        result = PlanError(
            success=False,
            error="No session ID provided",
            session_id=None,
            help="Use --session-id or run within Claude Code session",
        )
        _output_result(result, text)
        raise SystemExit(1)

    # Find plan
    projects_dir = Path.home() / ".claude" / "projects"
    result = find_plan_in_session(session_id, projects_dir)

    # Output result
    _output_result(result, text)

    # Exit with error if failed
    if not result.success:
        raise SystemExit(1)


if __name__ == "__main__":
    session_get_plan()
