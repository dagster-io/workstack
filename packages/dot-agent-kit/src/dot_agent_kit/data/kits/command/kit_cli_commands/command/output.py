"""Progress indicators and output formatting for command execution."""

import json
from typing import Any

import click
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

from dot_agent_kit.cli.output import user_output


def show_progress(message: AssistantMessage) -> None:
    """Show progress indicators for tool execution."""
    for block in message.content:
        if isinstance(block, ToolUseBlock):
            show_tool_progress(block.name)
        elif isinstance(block, TextBlock):
            # Only show significant text (filter out short thinking fragments)
            if len(block.text.strip()) > 20:
                user_output(block.text)


def show_tool_progress(tool_name: str) -> None:
    """Show user-friendly progress for tool execution."""
    indicators = {
        "Bash": "🔨 Running command...",
        "Task": "⚙️  Invoking agent...",
        "Read": "📖 Reading files...",
        "Write": "✏️  Writing files...",
        "Edit": "✏️  Editing files...",
        "Glob": "🔍 Finding files...",
        "Grep": "🔍 Searching code...",
        "Skill": "📚 Loading skill...",
        "SlashCommand": "⚡ Running command...",
        "MultiEdit": "✏️  Editing multiple files...",
        "Delete": "🗑️  Deleting files...",
        "Search": "🔎 Searching codebase...",
        "WebFetch": "🌐 Fetching web content...",
        "WebSearch": "🌐 Searching web...",
    }

    message = indicators.get(tool_name, f"⚙️  Executing {tool_name}...")
    user_output(message)


def format_result(result: ResultMessage) -> str:
    """Format result message for human-readable output."""
    lines = []

    if result.is_error:
        lines.append(click.style("❌ Command failed", fg="red", bold=True))
    else:
        lines.append(click.style("✅ Command completed", fg="green", bold=True))

    lines.append(f"\n⏱️  Duration: {result.duration_ms}ms")
    lines.append(f"🔄 Turns: {result.num_turns}")

    if result.total_cost_usd is not None:
        lines.append(f"💰 Cost: ${result.total_cost_usd:.4f}")

    return "\n".join(lines)


def format_result_json(result: ResultMessage, data: dict[str, Any]) -> str:
    """Format result as JSON for machine consumption."""
    return json.dumps(
        {
            "success": not result.is_error,
            "duration_ms": result.duration_ms,
            "turns": result.num_turns,
            "cost_usd": result.total_cost_usd,
            "session_id": result.session_id,
            "data": data,
        },
        indent=2,
    )
