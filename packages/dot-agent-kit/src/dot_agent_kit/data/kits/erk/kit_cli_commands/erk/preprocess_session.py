#!/usr/bin/env python3
"""
Session Log Preprocessor

Compresses JSONL session logs to XML format by removing metadata and deduplicating messages.
This command is invoked via dot-agent run erk preprocess-session <log-path>.
"""

import json
import tempfile
from pathlib import Path

import click


def escape_xml(text: str) -> str:
    """Minimal XML escaping for special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def deduplicate_assistant_messages(entries: list[dict]) -> list[dict]:
    """Remove duplicate assistant text when tool_use present."""
    deduplicated = []
    prev_assistant_text = None

    for entry in entries:
        if entry["type"] == "assistant":
            message_content = entry["message"].get("content", [])

            # Extract text and tool uses separately
            text_blocks = [c for c in message_content if c.get("type") == "text"]
            tool_uses = [c for c in message_content if c.get("type") == "tool_use"]

            current_text = text_blocks[0]["text"] if text_blocks else None

            # If text same as previous AND there's a tool_use, drop the duplicate text
            if current_text == prev_assistant_text and tool_uses:
                # Keep only tool_use content
                entry["message"]["content"] = tool_uses

            prev_assistant_text = current_text

        deduplicated.append(entry)

    return deduplicated


def generate_compressed_xml(entries: list[dict], source_label: str | None = None) -> str:
    """Generate coarse-grained XML from filtered entries."""
    xml_lines = ["<session>"]

    # Add source label if provided (for agent logs)
    if source_label:
        xml_lines.append(f'  <meta source="{escape_xml(source_label)}" />')

    # Extract session metadata once (from first entry with gitBranch)
    for entry in entries:
        # Check in the original entry structure (before filtering)
        if "gitBranch" in entry:
            branch = entry["gitBranch"]
            xml_lines.append(f'  <meta branch="{escape_xml(branch)}" />')
            break

    for entry in entries:
        entry_type = entry["type"]
        message = entry.get("message", {})

        if entry_type == "user":
            # Extract user content
            content = message.get("content", "")
            if isinstance(content, list):
                # Handle list of content blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = "\n".join(text_parts)
            xml_lines.append(f"  <user>{escape_xml(content)}</user>")

        elif entry_type == "assistant":
            # Extract text and tool uses
            content_blocks = message.get("content", [])
            for content in content_blocks:
                if content.get("type") == "text":
                    text = content.get("text", "")
                    if text.strip():  # Only include non-empty text
                        xml_lines.append(f"  <assistant>{escape_xml(text)}</assistant>")
                elif content.get("type") == "tool_use":
                    tool_name = content.get("name", "")
                    tool_id = content.get("id", "")
                    escaped_name = escape_xml(tool_name)
                    escaped_id = escape_xml(tool_id)
                    xml_lines.append(f'  <tool_use name="{escaped_name}" id="{escaped_id}">')
                    input_params = content.get("input", {})
                    for key, value in input_params.items():
                        escaped_key = escape_xml(key)
                        escaped_value = escape_xml(str(value))
                        xml_lines.append(f'    <param name="{escaped_key}">{escaped_value}</param>')
                    xml_lines.append("  </tool_use>")

        elif entry_type == "tool_result":
            # Handle tool results - preserve verbosity
            content_blocks = message.get("content", [])
            tool_use_id = message.get("tool_use_id", "")

            # Extract result content
            result_parts = []
            for block in content_blocks:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        result_parts.append(block.get("text", ""))
                    elif "text" in block:
                        result_parts.append(block["text"])
                elif isinstance(block, str):
                    result_parts.append(block)

            result_text = "\n".join(result_parts)
            xml_lines.append(f'  <tool_result tool="{escape_xml(tool_use_id)}">')
            xml_lines.append(escape_xml(result_text))
            xml_lines.append("  </tool_result>")

    xml_lines.append("</session>")
    return "\n".join(xml_lines)


def process_log_file(
    log_path: Path, session_id: str | None = None, source_label: str | None = None
) -> tuple[list[dict], int, int]:
    """Process a single JSONL log file and return filtered entries.

    Args:
        log_path: Path to the JSONL log file
        session_id: Optional session ID to filter entries by
        source_label: Optional label for agent logs

    Returns:
        Tuple of (filtered entries, total entries count, skipped entries count)
    """
    entries = []
    total_entries = 0
    skipped_entries = 0

    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        entry = json.loads(line)
        total_entries += 1

        # Filter by session ID if provided
        if session_id is not None:
            entry_session = entry.get("sessionId")
            # Include if sessionId matches OR if sessionId field missing (backward compat)
            if entry_session is not None and entry_session != session_id:
                skipped_entries += 1
                continue

        # Filter out noise entries
        if entry.get("type") == "file-history-snapshot":
            continue

        # Keep minimal fields but preserve gitBranch for metadata extraction
        filtered = {
            "type": entry["type"],
            "message": entry.get("message", {}),
        }

        # Preserve gitBranch for metadata (will be extracted in XML generation)
        if "gitBranch" in entry:
            filtered["gitBranch"] = entry["gitBranch"]

        # Drop usage metadata from assistant messages
        if "usage" in filtered["message"]:
            del filtered["message"]["usage"]

        entries.append(filtered)

    return entries, total_entries, skipped_entries


def discover_agent_logs(session_log_path: Path) -> list[Path]:
    """Discover agent logs in the same directory as the session log."""
    log_dir = session_log_path.parent
    agent_logs = sorted(log_dir.glob("agent-*.jsonl"))
    return agent_logs


@click.command()
@click.argument("log_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--session-id",
    type=str,
    default=None,
    help="Filter JSONL entries by session ID before preprocessing",
)
@click.option(
    "--include-agents/--no-include-agents",
    default=True,
    help="Include agent logs from same directory (default: True)",
)
def preprocess_session(log_path: Path, session_id: str | None, include_agents: bool) -> None:
    """Preprocess session log JSONL to compressed XML format.

    By default, automatically discovers and includes agent logs (agent-*.jsonl)
    from the same directory as the main session log.

    Args:
        log_path: Path to the main session JSONL file
        session_id: Optional session ID to filter entries by
        include_agents: Whether to include agent logs
    """
    # Process main session log
    entries, total_entries, skipped_entries = process_log_file(log_path, session_id=session_id)
    entries = deduplicate_assistant_messages(entries)

    # Show diagnostic output if filtering by session ID
    if session_id is not None:
        click.echo(f"✅ Filtered JSONL by session ID: {session_id[:8]}...", err=True)
        click.echo(
            f"📊 Included {total_entries - skipped_entries} entries, "
            f"skipped {skipped_entries} entries",
            err=True,
        )

    # Generate main session XML
    xml_sections = [generate_compressed_xml(entries)]

    # Discover and process agent logs if requested
    if include_agents:
        agent_logs = discover_agent_logs(log_path)
        for agent_log in agent_logs:
            agent_entries, agent_total, agent_skipped = process_log_file(
                agent_log, session_id=session_id
            )
            agent_entries = deduplicate_assistant_messages(agent_entries)

            # Generate XML with source label
            source_label = f"agent-{agent_log.stem.replace('agent-', '')}"
            agent_xml = generate_compressed_xml(agent_entries, source_label=source_label)
            xml_sections.append(agent_xml)

    # Combine all XML sections
    xml_content = "\n\n".join(xml_sections)

    # Write to temp file and print path
    filename_session_id = log_path.stem  # Extract session ID from filename
    temp_file = Path(tempfile.gettempdir()) / f"session-{filename_session_id}-compressed.xml"
    temp_file.write_text(xml_content, encoding="utf-8")

    # Print path to stdout for command capture
    click.echo(str(temp_file))


if __name__ == "__main__":
    preprocess_session()
