# Devrun Kit

Development CLI tool runner agent with two-layer enforcement for consistent usage patterns.

## Overview

The devrun kit provides a specialized agent for executing development tools (pytest, pyright, ruff, prettier, make, gt) with specialized result parsing and error handling. The kit uses two-layer enforcement to ensure consistent usage: passive reminders (UserPromptSubmit hook) and active blocking (PreToolUse hook).

## Hook Architecture

The devrun kit provides two-layer enforcement:

### Layer 1: UserPromptSubmit Reminder (Passive)

- Triggers when user submits prompts
- Displays reminder message to Claude
- Non-blocking, informational only
- Helps Claude remember to use devrun agent

### Layer 2: PreToolUse Validator (Active)

- Triggers before Bash tool execution
- Validates command against dev tool patterns
- **Blocks** execution with exit code 2 if dev tool detected
- Provides actionable error message directing to devrun agent

### Blocked Commands

The following commands require the devrun agent:

- `pytest` (with or without `uv run`)
- `pyright` (with or without `uv run`)
- `ruff` (with or without `uv run`)
- `prettier`
- `make`
- `gt`

Direct Bash usage of these tools will be blocked. Use the devrun agent instead:

```
Task(subagent_type="devrun", description="Run tests", prompt="Run pytest tests/")
```

## Installation

Install the devrun kit to your project or user level:

```bash
dot-agent kit install devrun
```

Kit version 0.2.0 adds PreToolUse hook for active blocking. Updating from 0.1.0 preserves existing UserPromptSubmit hook.

## Override Behavior

If you need to run dev tools directly (e.g., for debugging):

### Temporary Disable

Remove the PreToolUse hook from `.claude/settings.json`:

1. Open `.claude/settings.json`
2. Find the `"PreToolUse"` section
3. Remove or comment out the `bash-validator-hook` entry
4. Save the file

To re-enable, run: `dot-agent kit update devrun`

### Selective Allow

Modify the hook script to whitelist specific patterns:

1. Edit `kit_cli_commands/devrun/bash_validator_hook.py`
2. Add conditional logic before blocking
3. Example: Allow pytest in test directories only

### Permission Override

Claude will request permission when a command is blocked. You can manually approve blocked commands in the permission dialog.

## Version History

### v0.2.0

- Added PreToolUse hook for active command blocking
- Two-layer enforcement (reminder + blocker)
- Improved error messages with actionable guidance

### v0.1.0

- Initial release with devrun agent
- UserPromptSubmit reminder hook
- Tool documentation for pytest, pyright, ruff, prettier, make, gt
