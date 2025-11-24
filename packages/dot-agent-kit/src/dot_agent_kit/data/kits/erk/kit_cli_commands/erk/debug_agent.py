#!/usr/bin/env python3
"""
Debug Agent Command

Inspect failed agent runs from a session by showing execution logs and errors.
This command is invoked via: dot-agent run erk debug-agent
"""

import json
import os
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def get_session_id_from_env() -> str | None:
    """Extract session ID from SESSION_CONTEXT environment variable.

    The session_id_injector_hook sets SESSION_CONTEXT env var with format:
    "session_id=<uuid>"

    Returns:
        Session ID if found, None otherwise
    """
    session_context = os.environ.get("SESSION_CONTEXT")
    if not session_context:
        return None

    # Parse "session_id=<uuid>" format
    if "session_id=" in session_context:
        parts = session_context.split("session_id=")
        if len(parts) == 2:
            return parts[1].strip()

    return None


def find_project_dir_for_session(session_id: str) -> Path | None:
    """Find the project directory containing logs for a session ID.

    Agent logs are stored in:
    ~/.claude/projects/<project-path-with-session>/agent-<agent-id>.jsonl

    Args:
        session_id: Session ID to search for

    Returns:
        Path to project directory if found, None otherwise
    """
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        return None

    # Search for directories containing the session ID
    for project_dir in claude_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # Check if any JSONL file in this directory contains the session ID
        for jsonl_file in project_dir.glob("*.jsonl"):
            if not jsonl_file.exists():
                continue

            # Read first few lines to check for session ID
            try:
                lines = jsonl_file.read_text(encoding="utf-8").splitlines()[:10]
                for line in lines:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if entry.get("sessionId") == session_id:
                        return project_dir
            except (json.JSONDecodeError, OSError):
                continue

    return None


def discover_agent_logs(project_dir: Path) -> list[Path]:
    """Discover agent log files in a project directory.

    Args:
        project_dir: Directory to search for agent logs

    Returns:
        List of paths to agent-*.jsonl files
    """
    return sorted(project_dir.glob("agent-*.jsonl"))


def parse_agent_log(log_path: Path, session_id: str) -> dict:
    """Parse an agent log file and extract execution information.

    Args:
        log_path: Path to agent log JSONL file
        session_id: Session ID to filter entries

    Returns:
        Dict with agent execution info:
        {
            "agent_id": str,
            "agent_type": str,
            "started_at": str,
            "status": "success" | "failed",
            "task_description": str,
            "tool_calls": list[dict]
        }
    """
    agent_id = log_path.stem.replace("agent-", "")
    agent_type = "unknown"
    started_at = "unknown"
    task_description = ""
    tool_calls = []
    has_failures = False

    lines = log_path.read_text(encoding="utf-8").splitlines()

    for line in lines:
        if not line.strip():
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Filter by session ID
        if entry.get("sessionId") != session_id:
            continue

        entry_type = entry.get("type")
        message = entry.get("message", {})

        # Extract agent type and task from first user message
        if entry_type == "user" and not task_description:
            content = message.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                content = "\n".join(text_parts)
            task_description = str(content)[:500]  # Truncate for display

            # Try to extract agent type from prompt
            if "subagent_type=" in task_description:
                parts = task_description.split("subagent_type=")
                if len(parts) > 1:
                    type_part = parts[1].split()[0].strip("\"'")
                    agent_type = type_part

        # Extract tool calls
        if entry_type == "assistant":
            content_blocks = message.get("content", [])
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    tool_name = block.get("name", "")
                    tool_id = block.get("id", "")
                    tool_input = block.get("input", {})

                    tool_calls.append(
                        {
                            "tool": tool_name,
                            "tool_id": tool_id,
                            "input": tool_input,
                            "result": None,
                            "exit_code": None,
                            "error": None,
                        }
                    )

        # Extract tool results
        if entry_type == "tool_result":
            tool_use_id = message.get("tool_use_id", "")

            # Find corresponding tool call
            for tool_call in tool_calls:
                if tool_call["tool_id"] == tool_use_id:
                    # Extract result content
                    content_blocks = message.get("content", [])
                    result_parts = []
                    is_error = message.get("is_error", False)

                    for block in content_blocks:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                result_parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            result_parts.append(block)

                    result_text = "\n".join(result_parts)
                    tool_call["result"] = result_text
                    tool_call["is_error"] = is_error

                    # Try to extract exit code from Bash results
                    if tool_call["tool"] == "Bash" and "Exit code" in result_text:
                        for line_text in result_text.split("\n"):
                            if "Exit code" in line_text:
                                parts = line_text.split("Exit code")
                                if len(parts) > 1:
                                    code_str = parts[1].strip().split()[0]
                                    try:
                                        tool_call["exit_code"] = int(code_str)
                                        if tool_call["exit_code"] != 0:
                                            has_failures = True
                                            tool_call["error"] = result_text
                                    except ValueError:
                                        pass

                    # Mark as error if is_error flag set
                    if is_error:
                        has_failures = True
                        tool_call["error"] = result_text

                    break

        # Extract timestamp from first message
        if not started_at or started_at == "unknown":
            timestamp = message.get("timestamp")
            if timestamp:
                import datetime

                started_at = datetime.datetime.fromtimestamp(timestamp).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

    status = "failed" if has_failures else "success"

    return {
        "agent_id": agent_id,
        "agent_type": agent_type,
        "started_at": started_at,
        "status": status,
        "task_description": task_description,
        "tool_calls": tool_calls,
    }


def render_agent_list(agents: list[dict], console: Console) -> None:
    """Render a list of agents with their status.

    Args:
        agents: List of agent info dicts
        console: Rich console for output
    """
    table = Table(title="Failed Agents")
    table.add_column("Agent ID", style="cyan")
    table.add_column("Agent Type", style="yellow")
    table.add_column("Started", style="dim")
    table.add_column("Failures", style="red")

    for agent in agents:
        failures = sum(1 for tc in agent["tool_calls"] if tc.get("error"))
        table.add_row(
            agent["agent_id"][:8], agent["agent_type"], agent["started_at"], str(failures)
        )

    console.print(table)
    console.print("\n[dim]Run with --agent-id <id> to see full transcript[/dim]")


def render_agent_detail(
    agent: dict, console: Console, errors_only: bool = False, full: bool = False
) -> None:
    """Render detailed view of a single agent.

    Args:
        agent: Agent info dict
        console: Rich console for output
        errors_only: Only show failed tool calls
        full: Include full tool outputs
    """
    # Header
    header = Text()
    header.append(f"🔍 Agent: {agent['agent_type']} ", style="bold cyan")
    header.append(f"(agent-{agent['agent_id'][:8]})\n", style="dim")
    header.append(f"Session: {agent.get('session_id', 'unknown')[:16]}...\n", style="dim")
    header.append(f"Started: {agent['started_at']}", style="dim")

    console.print(Panel(header, title="Agent Info"))

    # Task description
    if agent["task_description"]:
        task_text = agent["task_description"][:300]
        if len(agent["task_description"]) > 300:
            task_text += "..."
        console.print(Panel(task_text, title="📋 Task", border_style="yellow"))

    # Tool calls
    tool_calls = agent["tool_calls"]
    if errors_only:
        tool_calls = [tc for tc in tool_calls if tc.get("error")]

    if tool_calls:
        console.print(Panel("", title="🔧 Tool Calls", border_style="blue"))

        for idx, tool_call in enumerate(tool_calls, 1):
            tool_name = tool_call["tool"]
            exit_code = tool_call.get("exit_code")
            error = tool_call.get("error")
            tool_call.get("result", "")

            # Build tool call display
            tool_text = Text()
            tool_text.append(f"[{idx}] {tool_name}: ", style="bold")

            # Show command for Bash tools
            if tool_name == "Bash":
                command = tool_call["input"].get("command", "")
                tool_text.append(command[:100], style="cyan")
                if len(command) > 100:
                    tool_text.append("...", style="dim")

            console.print(tool_text)

            # Show result
            if exit_code is not None:
                if exit_code != 0:
                    console.print(f"    ❌ Exit code: {exit_code}", style="red")
                else:
                    console.print(f"    ✅ Exit code: {exit_code}", style="green")

            if error:
                error_text = error if full else error[:200]
                if not full and len(error) > 200:
                    error_text += "\n    ..."
                console.print(f"    Error: {error_text}", style="red")

            console.print()

    if not full:
        console.print("\n[dim]Run with --full to see complete tool outputs[/dim]")


def export_json(agents: list[dict], session_id: str) -> str:
    """Export agents data as JSON.

    Args:
        agents: List of agent info dicts
        session_id: Session ID

    Returns:
        JSON string
    """
    output = {"session_id": session_id, "agents": agents}
    return json.dumps(output, indent=2)


@click.command(name="debug-agent")
@click.option(
    "--session-id",
    type=str,
    default=None,
    help="Session ID (auto-detects from env if not provided)",
)
@click.option("--agent-id", type=str, default=None, help="Show specific agent by ID")
@click.option("--agent-type", type=str, default=None, help="Filter by agent type (e.g., 'devrun')")
@click.option("--errors-only", is_flag=True, help="Show only failed operations")
@click.option("--all", "show_all", is_flag=True, help="Show all agents (including successful ones)")
@click.option("--tool", type=str, default=None, help="Filter to specific tool (e.g., 'Bash')")
@click.option("--json", "json_output", is_flag=True, help="Output JSON instead of Rich UI")
@click.option("--full", is_flag=True, help="Include full tool outputs (not truncated)")
def debug_agent(
    session_id: str | None,
    agent_id: str | None,
    agent_type: str | None,
    errors_only: bool,
    show_all: bool,
    tool: str | None,
    json_output: bool,
    full: bool,
) -> None:
    """Inspect failed agent runs from a session.

    By default, shows only failed agents. Use --all to see all agents.
    Auto-detects session ID from environment if not provided.

    Examples:
        dot-agent run erk debug-agent
        dot-agent run erk debug-agent --session-id abc123
        dot-agent run erk debug-agent --agent-id def456
        dot-agent run erk debug-agent --all
        dot-agent run erk debug-agent --json
    """
    console = Console()

    # Step 1: Get session ID
    if not session_id:
        session_id = get_session_id_from_env()

    if not session_id:
        click.echo("Error: No session ID provided and could not auto-detect", err=True)
        click.echo("", err=True)
        click.echo("Provide session ID with --session-id flag", err=True)
        click.echo(
            "Or run from within a Claude Code session where SESSION_CONTEXT is set",
            err=True,
        )
        raise SystemExit(1)

    # Step 2: Find project directory
    project_dir = find_project_dir_for_session(session_id)
    if not project_dir:
        click.echo(f"Error: No agent logs found for session {session_id[:8]}...", err=True)
        click.echo("", err=True)
        click.echo("Possible reasons:", err=True)
        click.echo("  - Session ID is incorrect", err=True)
        click.echo("  - Session logs have been cleaned up", err=True)
        click.echo("  - No agents were run in this session", err=True)
        raise SystemExit(1)

    # Step 3: Discover agent logs
    agent_logs = discover_agent_logs(project_dir)
    if not agent_logs:
        click.echo(f"No agent runs found for session {session_id[:8]}...", err=True)
        raise SystemExit(1)

    # Step 4: Parse agent logs
    agents = []
    for log_path in agent_logs:
        agent_info = parse_agent_log(log_path, session_id)
        agent_info["session_id"] = session_id

        # Apply filters
        if not show_all and agent_info["status"] != "failed":
            continue

        if agent_type and agent_info["agent_type"] != agent_type:
            continue

        if agent_id and not agent_info["agent_id"].startswith(agent_id):
            continue

        if tool:
            # Filter tool calls
            agent_info["tool_calls"] = [
                tc for tc in agent_info["tool_calls"] if tc["tool"].lower() == tool.lower()
            ]
            if not agent_info["tool_calls"]:
                continue

        agents.append(agent_info)

    if not agents:
        click.echo("No agents match the specified filters", err=True)
        raise SystemExit(1)

    # Step 5: Output results
    if json_output:
        click.echo(export_json(agents, session_id))
    else:
        console.print(f"\n🔍 Agent Runs for Session: [cyan]{session_id[:16]}...[/cyan]\n")

        if len(agents) == 1 or agent_id:
            # Single agent detail view
            render_agent_detail(agents[0], console, errors_only=errors_only, full=full)
        else:
            # Multiple agents list view
            render_agent_list(agents, console)


if __name__ == "__main__":
    debug_agent()
