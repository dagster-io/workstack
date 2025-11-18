"""CLI command for executing Claude Code slash commands."""

from pathlib import Path

import anyio
import click
from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, query

from dot_agent_kit.cli.output import machine_output, user_output
from dot_agent_kit.data.kits.command.kit_cli_commands.command.context import (
    gather_context,
)
from dot_agent_kit.data.kits.command.kit_cli_commands.command.models import (
    CommandNotFoundError,
    CommandResult,
)
from dot_agent_kit.data.kits.command.kit_cli_commands.command.output import (
    format_result,
    format_result_json,
    show_progress,
)
from dot_agent_kit.data.kits.command.kit_cli_commands.command.resolution import (
    read_command_markdown,
    resolve_command_file,
)


@click.command()
@click.argument("command_name")
@click.option("--json", is_flag=True, help="Output JSON for scripting")
@click.option("--api-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key")
def execute(command_name: str, json: bool, api_key: str | None) -> None:
    """Execute a Claude Code slash command.

    Examples:
        dot-agent run command execute gt:submit-branch
        dot-agent run command execute ensure-ci --json
    """
    if api_key is None:
        user_output(click.style("Error: ", fg="red") + "ANTHROPIC_API_KEY not set")
        user_output("\nSet your API key:")
        user_output("  export ANTHROPIC_API_KEY='sk-ant-...'")
        raise SystemExit(1)

    try:
        result = anyio.run(execute_command_async, command_name, Path.cwd(), api_key, json)

        if json:
            machine_output(format_result_json(result.sdk_result, result.data))
        else:
            user_output(format_result(result.sdk_result))

        raise SystemExit(0 if not result.sdk_result.is_error else 1)

    except CommandNotFoundError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from None
    except Exception as e:
        user_output(click.style("Unexpected error: ", fg="red") + str(e))
        raise SystemExit(1) from e


async def execute_command_async(
    command_name: str, cwd: Path, api_key: str, json_output: bool
) -> CommandResult:
    """Execute command asynchronously via Claude Agent SDK."""

    # 1. Resolve command file
    command_path = resolve_command_file(command_name, cwd)
    command_prompt = read_command_markdown(command_path)

    # 2. Gather context
    if not json_output:
        user_output(f"⚙️  Executing: {click.style(command_name, fg='yellow')}")
        user_output("📋 Gathering project context...")

    context = gather_context(cwd)
    full_prompt = f"{command_prompt}\n\n## Project Context\n\n{context}"

    # 3. Configure SDK with full tool access
    options = ClaudeAgentOptions(
        allowed_tools=[
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Delete",
            "Bash",
            "Task",
            "Skill",
            "SlashCommand",
            "Glob",
            "Grep",
            "Search",
            "WebFetch",
            "WebSearch",
            "ListDirectory",
            "DeleteDirectory",
        ],
        permission_mode="bypassPermissions",  # Auto-approve all operations
        cwd=str(cwd),
        setting_sources=["project"],  # Enable auto-discovery of project agents
        # No max_budget_usd - user-controlled per user preference
    )

    # 4. Execute via SDK
    if not json_output:
        user_output("🤖 Invoking Claude...\n")

    result_message = None
    collected_data = {}

    async for message in query(prompt=full_prompt, options=options):
        if isinstance(message, AssistantMessage):
            if not json_output:
                show_progress(message)
        elif isinstance(message, ResultMessage):
            result_message = message

    if result_message is None:
        raise RuntimeError("No result message received from SDK")

    return CommandResult(sdk_result=result_message, data=collected_data)
