#!/usr/bin/env python3
"""Create enhanced implementation plan from session logs (two-phase).

This script handles file operations for the enhance-and-save-plan workflow,
leaving only AI-driven analysis in the Claude command layer. It operates in two phases:

Phase 1 (discover):
1. Find Claude Code project directory by matching cwd
2. Locate session log file by session ID
3. Preprocess session logs directly (no subprocess)
4. Optionally chunk XML into batches (streaming mode)
5. Return compressed XML/batches and stats as JSON

Phase 2 (assemble):
1. Parse plan content and discoveries from input
2. Return raw inputs for LLM composition (NO templates or text generation)

Streaming Mode:
    When --streaming flag is used, large XML sessions are chunked into batches
    of ~10 tool sequences each. This enables:
    - Incremental processing with better latency perception
    - Memory-efficient analysis with smaller context per batch
    - Automatic fallback to single-pass for small sessions
    - Foundation for future parallel processing

Usage:
    dot-agent run erk enhance-and-save-plan discover --session-id <id> --cwd <path>
    dot-agent run erk enhance-and-save-plan discover --session-id <id> --cwd <path> --streaming
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
    # Standard mode (single XML)
    $ dot-agent run erk enhance-and-save-plan discover --session-id abc123 --cwd /Users/foo/repo
    {"compressed_xml": "<session>...</session>", "stats": {...}}

    # Streaming mode (batched XML)
    $ dot-agent run erk enhance-and-save-plan discover --session-id abc123 --cwd /Users/foo/repo --streaming
    {"mode": "streaming", "batches": ["<session>...</session>", ...], "batch_count": 3, "stats": {...}}

    # Assemble phase
    $ dot-agent run erk enhance-and-save-plan assemble plan.md discoveries.json
    {"plan_content": "## Plan...", "discoveries": {...}}
"""

import json
import xml.etree.ElementTree as ET
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
class StreamingDiscoverResult:
    """Success result from discover phase in streaming mode."""

    success: bool
    mode: str
    batches: list[str]
    batch_count: int
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


def _chunk_xml_by_natural_boundaries(xml_content: str, target_sections: int = 10) -> list[str]:
    """Chunk XML into batches by natural conversation boundaries.

    Groups tool sequences (user → tool_use → tool_result → assistant reasoning)
    into batches of approximately target_sections sequences each.

    Args:
        xml_content: Full compressed XML session content
        target_sections: Target number of tool sequences per batch (default: 10)

    Returns:
        List of XML chunks, each containing a <session> wrapper with batched content
    """
    # Parse XML to identify sequences
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        # If XML is malformed, return as single batch
        return [xml_content]

    # Extract metadata (first element is usually <meta>)
    meta_element = root.find("meta")
    meta_str = ""
    if meta_element is not None:
        branch = meta_element.get("branch", "")
        if branch:
            meta_str = f'  <meta branch="{branch}" />\n'

    # Group children into sequences
    sequences: list[list[ET.Element]] = []
    current_sequence: list[ET.Element] = []

    for child in root:
        if child.tag == "meta":
            continue  # Skip meta, handled separately

        current_sequence.append(child)

        # A sequence typically ends with an assistant message after tool results
        if child.tag == "assistant" and len(current_sequence) > 1:
            sequences.append(current_sequence)
            current_sequence = []

    # Handle any remaining elements
    if current_sequence:
        sequences.append(current_sequence)

    # If we have fewer sequences than target, return as single batch
    if len(sequences) <= target_sections:
        return [xml_content]

    # Batch sequences
    batches: list[str] = []
    for i in range(0, len(sequences), target_sections):
        batch_sequences = sequences[i : i + target_sections]

        # Reconstruct XML for this batch
        batch_lines = ["<session>"]
        if meta_str:
            batch_lines.append(meta_str.rstrip())

        for sequence in batch_sequences:
            for elem in sequence:
                batch_lines.append(_element_to_xml_string(elem))

        batch_lines.append("</session>")
        batches.append("\n".join(batch_lines))

    return batches


def _element_to_xml_string(elem: ET.Element, indent: str = "  ") -> str:
    """Convert an XML element back to string format with proper indentation.

    Args:
        elem: XML element to convert
        indent: Indentation string (default: 2 spaces)

    Returns:
        String representation of the element
    """
    lines: list[str] = []

    # Opening tag with attributes
    if elem.attrib:
        attrs = " ".join(f'{k}="{v}"' for k, v in elem.attrib.items())
        opening_tag = f"{indent}<{elem.tag} {attrs}>"
    else:
        opening_tag = f"{indent}<{elem.tag}>"

    # Handle self-closing or empty elements
    if not elem.text and not list(elem):
        if elem.attrib:
            attrs = " ".join(f'{k}="{v}"' for k, v in elem.attrib.items())
            return f"{indent}<{elem.tag} {attrs} />"
        return f"{indent}<{elem.tag} />"

    lines.append(opening_tag)

    # Add text content if present
    if elem.text and elem.text.strip():
        text = elem.text.strip()
        if "\n" in text:
            # Multi-line text
            for line in text.split("\n"):
                lines.append(line)
        else:
            # Single line text
            lines[-1] = f"{opening_tag}{text}</{elem.tag}>"
            return lines[-1]

    # Add child elements
    for child in elem:
        lines.append(_element_to_xml_string(child, indent + "  "))

    # Closing tag
    lines.append(f"{indent}</{elem.tag}>")

    return "\n".join(lines)


def execute_discover(session_id: str, cwd: Path, streaming: bool = False) -> DiscoverResult | StreamingDiscoverResult | DiscoverError:
    """Execute discovery phase and return structured result.

    Args:
        session_id: Session ID to locate and process
        cwd: Current working directory
        streaming: If True, chunk XML into batches for incremental processing

    Returns:
        DiscoverResult or StreamingDiscoverResult on success, DiscoverError on failure
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

    # Return streaming result if requested
    if streaming:
        batches = _chunk_xml_by_natural_boundaries(compressed_xml)
        return StreamingDiscoverResult(
            success=True,
            mode="streaming",
            batches=batches,
            batch_count=len(batches),
            log_path=str(log_path),
            session_id=session_id,
            stats=stats,
        )

    # Return standard result (NO temp file needed)
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
@click.option(
    "--streaming",
    is_flag=True,
    default=False,
    help="Enable streaming mode (chunk XML into batches for incremental processing)",
)
def discover(session_id: str, cwd: Path, streaming: bool) -> None:
    """Phase 1: Discover and preprocess session logs."""
    try:
        result = execute_discover(session_id, cwd, streaming=streaming)
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
