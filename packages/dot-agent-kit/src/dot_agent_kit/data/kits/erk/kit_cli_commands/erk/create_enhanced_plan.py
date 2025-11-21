#!/usr/bin/env python3
"""Create enhanced implementation plan from session logs (two-phase).

This script handles file operations for the create-enhanced-plan workflow,
leaving only AI-driven analysis in the Claude command layer. It operates in two phases:

Phase 1 (discover):
1. Find Claude Code project directory by matching cwd
2. Locate session log file by session ID
3. Preprocess session logs directly (no subprocess)
4. Return compressed XML and stats as JSON

Phase 2 (assemble):
1. Parse plan content and discoveries from input
2. Build enhanced plan structure with frontmatter
3. Add Critical Context section with discoveries
4. Link discoveries to plan steps
5. Return enhanced plan content as JSON

Usage:
    dot-agent run erk create-enhanced-plan discover --session-id <id> --cwd <path>
    dot-agent run erk create-enhanced-plan assemble <plan-file> <discoveries-file>

Output:
    JSON object with either success or error information

Exit Codes:
    0: Success
    1: Error (validation failed or operation failed)

Error Types:
    - project_not_found: Could not find Claude Code project directory
    - session_log_not_found: Session log file not found
    - preprocessing_failed: Failed to preprocess session logs

Examples:
    $ dot-agent run erk create-enhanced-plan discover --session-id abc123 --cwd /Users/foo/repo
    {"compressed_xml": "<session>...</session>", "stats": {...}}

    $ dot-agent run erk create-enhanced-plan assemble plan.md discoveries.json
    {"content": "...", "filename": "enhanced-plan.md"}
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import click

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.preprocess_session import (
    deduplicate_assistant_messages,
    deduplicate_documentation_blocks,
    discover_agent_logs,
    generate_compressed_xml,
    is_empty_session,
    is_warmup_session,
    process_log_file,
    truncate_tool_parameters,
)


@dataclass
class DiscoverResult:
    """Success result from discover phase."""

    success: bool
    compressed_xml: str
    log_path: str
    session_id: str
    stats: dict[str, str | int]


@dataclass
class DiscoverError:
    """Error result from discover phase."""

    success: bool
    error: str
    help: str
    context: dict[str, str]


@dataclass
class AssembleResult:
    """Success result from assemble phase."""

    success: bool
    content: str
    filename: str
    stats: dict[str, int]


@dataclass
class AssembleError:
    """Error result from assemble phase."""

    success: bool
    error: str
    help: str
    context: dict[str, str]


def _find_project_dir(cwd: Path) -> Path | None:
    """Locate Claude Code project directory by matching cwd.

    Project directories are stored in ~/.claude/projects/ with escaped paths.
    Example: /Users/foo/bar → -Users-foo-bar

    Args:
        cwd: Current working directory to match

    Returns:
        Path to project directory if found, None otherwise
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None

    # Convert cwd to escaped format
    escaped_cwd = str(cwd).replace("/", "-")

    # Search for matching project directory
    for project_dir in projects_dir.iterdir():
        if project_dir.is_dir() and escaped_cwd in project_dir.name:
            return project_dir

    return None


def _locate_session_log(project_dir: Path, session_id: str) -> Path | None:
    """Find session log file in project directory.

    Session logs are named: <session-id>.jsonl

    Args:
        project_dir: Path to Claude Code project directory
        session_id: Session ID to locate

    Returns:
        Path to session log file if found, None otherwise
    """
    if not project_dir.exists():
        return None

    log_path = project_dir / f"{session_id}.jsonl"
    if log_path.exists():
        return log_path
    return None


def _preprocess_logs(log_path: Path, session_id: str) -> tuple[str, dict[str, str | int]]:
    """Preprocess session logs and return compressed XML + stats.

    Calls preprocessing functions directly instead of subprocess for performance.

    Args:
        log_path: Path to session log file
        session_id: Session ID for filtering

    Returns:
        Tuple of (compressed XML string, stats dictionary)

    Raises:
        FileNotFoundError: If log file doesn't exist
        Exception: If preprocessing fails
    """
    if not log_path.exists():
        raise FileNotFoundError(f"Session log not found: {log_path}")

    # Process main session log
    entries, total_entries, skipped_entries = process_log_file(
        log_path, session_id=session_id, enable_filtering=True
    )

    # Check for empty/warmup sessions
    if is_empty_session(entries):
        raise ValueError("Empty session detected - no meaningful content")

    if is_warmup_session(entries):
        raise ValueError("Warmup session detected - no meaningful content")

    # Apply all optimization filters
    entries = deduplicate_documentation_blocks(entries)
    entries = truncate_tool_parameters(entries)
    entries = deduplicate_assistant_messages(entries)

    # Generate main session XML
    xml_sections = [generate_compressed_xml(entries, enable_pruning=True)]

    # Discover and process agent logs
    agent_logs = discover_agent_logs(log_path)
    for agent_log in agent_logs:
        agent_entries, agent_total, agent_skipped = process_log_file(
            agent_log, session_id=session_id, enable_filtering=True
        )

        # Apply filtering for agent logs
        if is_empty_session(agent_entries):
            continue
        if is_warmup_session(agent_entries):
            continue
        agent_entries = deduplicate_documentation_blocks(agent_entries)
        agent_entries = truncate_tool_parameters(agent_entries)
        agent_entries = deduplicate_assistant_messages(agent_entries)

        # Generate XML with source label
        source_label = f"agent-{agent_log.stem.replace('agent-', '')}"
        agent_xml = generate_compressed_xml(
            agent_entries, source_label=source_label, enable_pruning=True
        )
        xml_sections.append(agent_xml)

    # Combine all XML sections
    xml_content = "\n\n".join(xml_sections)

    # Calculate compression metrics
    original_size = len(log_path.read_text(encoding="utf-8"))
    compressed_size = len(xml_content)
    reduction_pct = ((original_size - compressed_size) / original_size) * 100 if original_size > 0 else 0

    stats = {
        "entries_processed": total_entries - skipped_entries,
        "entries_skipped": skipped_entries,
        "token_reduction_pct": f"{reduction_pct:.1f}%",
        "original_size": original_size,
        "compressed_size": compressed_size,
    }

    return xml_content, stats


def execute_discover(session_id: str, cwd: Path) -> DiscoverResult | DiscoverError:
    """Execute discovery phase and return structured result.

    Args:
        session_id: Session ID to locate and process
        cwd: Current working directory

    Returns:
        DiscoverResult on success, DiscoverError on failure
    """
    # Find project directory
    project_dir = _find_project_dir(cwd)
    if project_dir is None:
        return DiscoverError(
            success=False,
            error="Project directory not found",
            help=f"Could not find Claude Code project for {cwd}",
            context={"cwd": str(cwd)},
        )

    # Locate session log
    log_path = _locate_session_log(project_dir, session_id)
    if log_path is None:
        return DiscoverError(
            success=False,
            error="Session log not found",
            help=f"No log file found for session {session_id}",
            context={"session_id": session_id, "project_dir": str(project_dir)},
        )

    # Preprocess logs
    try:
        compressed_xml, stats = _preprocess_logs(log_path, session_id)
    except Exception as e:
        return DiscoverError(
            success=False,
            error="Preprocessing failed",
            help=str(e),
            context={"log_path": str(log_path)},
        )

    # Return structured result (NO temp file needed)
    return DiscoverResult(
        success=True,
        compressed_xml=compressed_xml,
        log_path=str(log_path),
        session_id=session_id,
        stats=stats,
    )


def _extract_title(plan_lines: list[str]) -> str:
    """Extract plan title from first heading.

    Args:
        plan_lines: List of plan content lines

    Returns:
        Extracted title or default
    """
    for line in plan_lines:
        if line.startswith("# "):
            return line.lstrip("# ").strip()
    return "Implementation Plan"


def _generate_filename(plan_lines: list[str]) -> str:
    """Generate filename from plan title (max 30 chars base).

    Args:
        plan_lines: List of plan content lines

    Returns:
        Slugified filename with enhanced-plan suffix
    """
    title = _extract_title(plan_lines)
    # Slugify title: lowercase, replace spaces with hyphens, limit length
    slug = title.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    slug = slug[:30]  # Worktree name limit
    return f"{slug}-enhanced-plan.md"


def _extract_summary(plan_lines: list[str]) -> str:
    """Extract summary section from plan.

    Args:
        plan_lines: List of plan content lines

    Returns:
        Summary text or placeholder
    """
    # Find content between first heading and second ## heading
    in_summary = False
    summary_lines = []

    for line in plan_lines:
        if line.startswith("# "):
            in_summary = True
            continue
        if line.startswith("## ") and in_summary:
            break
        if in_summary:
            summary_lines.append(line)

    summary_text = "\n".join(summary_lines).strip()
    if summary_text:
        return summary_text + "\n"
    return "Implementation plan created during planning session.\n"


def _format_discovery_categories(categories: dict[str, list[str]]) -> str:
    """Format discoveries by category.

    Args:
        categories: Dictionary mapping category names to discovery lists

    Returns:
        Formatted markdown string
    """
    output = []
    for category, items in categories.items():
        output.append(f"#### {category}\n")
        for item in items:
            output.append(f"- {item}")
        output.append("")
    return "\n".join(output)


def _format_failed_attempts(attempts: list[dict[str, str]]) -> str:
    """Format failed attempts section.

    Args:
        attempts: List of failed attempt dictionaries

    Returns:
        Formatted markdown string
    """
    output = ["#### Failed Approaches Discovered\n"]
    for attempt in attempts:
        name = attempt.get("name", "Unknown")
        reason = attempt.get("reason", "No reason provided")
        output.append(f"- **{name}**: {reason}")
    output.append("")
    return "\n".join(output)


def execute_assemble(plan_content: str, discoveries: dict) -> AssembleResult | AssembleError:
    """Assemble enhanced plan from content and discoveries.

    Args:
        plan_content: Markdown content of the plan
        discoveries: Dictionary containing categorized discoveries

    Returns:
        AssembleResult on success, AssembleError on failure
    """
    # Parse plan markdown
    plan_lines = plan_content.splitlines()

    # Parse discoveries structure
    discovery_categories = discoveries.get("categories", {})
    failed_attempts = discoveries.get("failed_attempts", [])
    raw_log = discoveries.get("raw_discoveries", [])
    session_id = discoveries.get("session_id", "unknown")

    # Generate frontmatter with enrichment metadata
    timestamp = datetime.now(timezone.utc).isoformat()
    frontmatter = f"""---
enriched_by_create_enhanced_plan: true
session_id: {session_id}
discovery_count: {len(raw_log)}
timestamp: {timestamp}
---
"""

    # Build enhanced structure
    enhanced_plan = [frontmatter]
    enhanced_plan.append(f"# {_extract_title(plan_lines)} - Enhanced Implementation Guide\n")

    # Add Executive Summary
    enhanced_plan.append("## Executive Summary\n")
    enhanced_plan.append(_extract_summary(plan_lines))

    # Add Critical Context section with discoveries
    enhanced_plan.append("---\n")
    enhanced_plan.append("## Critical Context from Planning\n")
    enhanced_plan.append("### What We Learned\n")
    if discovery_categories:
        enhanced_plan.append(_format_discovery_categories(discovery_categories))
    else:
        enhanced_plan.append("No categorized discoveries recorded.\n")

    # Add Failed Attempts section
    if failed_attempts:
        enhanced_plan.append("### What Didn't Work\n")
        enhanced_plan.append(_format_failed_attempts(failed_attempts))

    # Add Raw Discoveries Log
    if raw_log:
        enhanced_plan.append("### Raw Discoveries Log\n")
        for discovery in raw_log:
            enhanced_plan.append(f"- {discovery}")
        enhanced_plan.append("")

    # Add original plan
    enhanced_plan.append("---\n")
    enhanced_plan.append("## Implementation Plan\n")
    enhanced_plan.append("\n".join(plan_lines))

    return AssembleResult(
        success=True,
        content="\n".join(enhanced_plan),
        filename=_generate_filename(plan_lines),
        stats={
            "discovery_count": len(raw_log),
            "categories": len(discovery_categories),
            "failed_attempts": len(failed_attempts),
        },
    )


@click.group()
def create_enhanced_plan() -> None:
    """Create enhanced implementation plan from session logs."""
    pass


@click.command()
@click.option("--session-id", required=True, help="Session ID to process")
@click.option(
    "--cwd", required=True, type=click.Path(exists=True, path_type=Path), help="Current working directory"
)
def discover(session_id: str, cwd: Path) -> None:
    """Phase 1: Discover and preprocess session logs."""
    try:
        result = execute_discover(session_id, cwd)
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, DiscoverError):
            raise SystemExit(1)

    except Exception as e:
        error = DiscoverError(
            success=False,
            error="Unexpected error during discovery",
            help=str(e),
            context={"error": str(e)},
        )
        click.echo(json.dumps(asdict(error), indent=2), err=True)
        raise SystemExit(1) from None


@click.command()
@click.argument("plan_content", type=click.File("r"))
@click.argument("discoveries", type=click.File("r"))
def assemble(plan_content, discoveries) -> None:
    """Phase 2: Assemble enhanced plan with discoveries."""
    try:
        plan_text = plan_content.read()
        discoveries_data = json.load(discoveries)

        result = execute_assemble(plan_text, discoveries_data)
        click.echo(json.dumps(asdict(result), indent=2))

        if isinstance(result, AssembleError):
            raise SystemExit(1)

    except Exception as e:
        error = AssembleError(
            success=False,
            error="Unexpected error during assembly",
            help=str(e),
            context={"error": str(e)},
        )
        click.echo(json.dumps(asdict(error), indent=2), err=True)
        raise SystemExit(1) from None


# Register subcommands
create_enhanced_plan.add_command(discover)
create_enhanced_plan.add_command(assemble)
