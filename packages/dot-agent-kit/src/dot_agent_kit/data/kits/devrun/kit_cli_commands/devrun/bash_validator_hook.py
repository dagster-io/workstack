#!/usr/bin/env python3
"""PreToolUse hook that blocks direct Bash usage of dev tools.

This hook intercepts Bash tool calls and validates the command against a list
of development tools (pytest, pyright, ruff, prettier, make, gt) that should
only be run through the devrun agent for specialized result parsing.

Invoked via: dot-agent run devrun bash-validator-hook
Input: JSON on stdin with structure {"tool_name": "...", "tool_input": {...}}
Exit codes:
  0 = Allow execution (command passed validation or not a Bash tool)
  2 = Block execution (dev tool detected, feed stderr to Claude)
"""

import json
import sys

import click


@click.command()
def bash_validator_hook() -> None:
    """Validate Bash commands and block direct dev tool usage."""
    # Parse JSON input from stdin
    hook_data = json.load(sys.stdin)

    # Extract tool information
    tool_name = hook_data.get("tool_name")
    tool_input = hook_data.get("tool_input", {})
    command = tool_input.get("command", "").strip()

    # Early exit for non-Bash tools - allow all other tools
    if tool_name != "Bash":
        sys.exit(0)

    # Define dev tools that require devrun agent
    dev_tools = ["pytest", "pyright", "ruff", "prettier", "make", "gt"]

    # Check if command uses any dev tool
    for tool in dev_tools:
        # Split command to get first word (handles path-prefixed commands)
        command_parts = command.split()
        if not command_parts:
            # Empty command - allow
            sys.exit(0)

        first_word = command_parts[0]

        # Check various patterns:
        # 1. Direct tool usage: "pytest tests/"
        # 2. Tool with args: "pytest -v"
        # 3. uv run prefix: "uv run pytest"
        # 4. Path-prefixed: "./bin/pytest" or "/usr/bin/pytest"

        is_match = False

        # Pattern 1 & 2: Direct tool usage
        if first_word == tool or first_word.endswith(f"/{tool}"):
            is_match = True

        # Pattern 3: uv run prefix
        if command.startswith(f"uv run {tool}"):
            is_match = True

        if is_match:
            # Block execution with actionable error message
            error_msg = (
                f"❌ Direct Bash usage blocked for '{tool}' command.\n\n"
                f"🛠️  Use the devrun agent instead:\n"
                f'   Task(subagent_type="devrun", '
                f'description="Run {tool}", '
                f'prompt="Run {command}")\n\n'
                f"Why: The devrun agent provides specialized parsing for "
                f"test failures, type errors,\nlinting issues, and build "
                f"output with better error handling and workflow optimization."
            )
            click.echo(error_msg, err=True)
            sys.exit(2)

    # No dev tool detected - allow execution
    sys.exit(0)


if __name__ == "__main__":
    bash_validator_hook()
