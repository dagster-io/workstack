#!/usr/bin/env python3
"""Create enhanced implementation plan from session logs (two-phase).

This script handles file operations for the enhance-and-save-plan workflow,
leaving only AI-driven analysis in the Claude command layer. It operates in two phases:

Phase 1 (discover):
1. Find Claude Code project directory by matching cwd
2. Locate session log file by session ID
3. Preprocess session logs directly (no subprocess)
4. Return compressed XML and stats as JSON

Phase 2 (assemble):
1. Parse plan content and discoveries from input
2. Return raw inputs for LLM composition (NO templates or text generation)

Usage:
    dot-agent run erk enhance-and-save-plan discover --session-id <id> --cwd <path>
    dot-agent run erk enhance-and-save-plan assemble <plan-file> <discoveries-file>

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
    $ dot-agent run erk enhance-and-save-plan discover --session-id abc123 --cwd /Users/foo/repo
    {"compressed_xml": "<session>...</session>", "stats": {...}}

    $ dot-agent run erk enhance-and-save-plan assemble plan.md discoveries.json
    {"plan_content": "## Plan...", "discoveries": {...}}
"""

import json
from dataclasses import asdict, dataclass
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
    """Success result from assemble phase (returns inputs for LLM composition)."""

    success: bool
    plan_content: str
    discoveries: dict


@dataclass
class AssembleError:
    """Error result from assemble phase."""

    success: bool
    error: str
    help: str
    context: dict[str, str]


def _find_project_dir(cwd: Path) -> Path | None:
    """Locate Claude Code project directory by matching cwd.

    Claude Code encodes filesystem paths to project folder names using:
    - Replace "/" with "-"
    - Replace "." with "-"

    Example:
        /Users/foo/.config/bar → -Users-foo--config-bar
        (note the double dash where .config becomes --config)

    This function performs exact matching on the encoded path to avoid
    ambiguity when multiple projects share path prefixes.

    Args:
        cwd: Current working directory to match

    Returns:
        Path to project directory if found, None otherwise
    """
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return None

    # Convert cwd to escaped format (both slashes and dots)
    encoded_path = str(cwd).replace("/", "-").replace(".", "-")

    # Use exact match to avoid false positives from substring matching
    project_dir = projects_dir / encoded_path
    if project_dir.exists() and project_dir.is_dir():
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
    if original_size > 0:
        reduction_pct = ((original_size - compressed_size) / original_size) * 100
    else:
        reduction_pct = 0

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


def execute_assemble(plan_content: str, discoveries: dict) -> AssembleResult | AssembleError:
    """Return plan and discoveries for LLM composition (NO text generation).

    This function does pure infrastructure work: reading inputs and returning them
    as JSON for the LLM to compose. NO parsing, NO templates, NO text munging.

    Args:
        plan_content: Markdown content of the plan
        discoveries: Dictionary containing categorized discoveries

    Returns:
        AssembleResult with raw inputs for LLM composition
    """
    # Infrastructure only: return inputs for LLM composition
    # The LLM will handle all composition, naming, formatting, and structure
    return AssembleResult(
        success=True,
        plan_content=plan_content,
        discoveries=discoveries,
    )


@click.group()
def enhance_and_save_plan() -> None:
    """Create enhanced implementation plan from session logs."""
    pass


@click.command()
@click.option("--session-id", required=True, help="Session ID to process")
@click.option(
    "--cwd",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Current working directory",
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
enhance_and_save_plan.add_command(discover)
enhance_and_save_plan.add_command(assemble)
