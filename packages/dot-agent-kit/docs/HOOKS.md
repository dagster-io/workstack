# Hook Development Guide

Complete guide for creating, modifying, and managing Claude Code hooks in dot-agent kits.

## Overview

Hooks are automated triggers that run commands at specific lifecycle events in Claude Code. They enable kits to provide contextual reminders, run validations, or perform automated actions based on the user's current context.

## Table of Contents

- [Hook Architecture](#hook-architecture)
- [Creating a New Hook](#creating-a-new-hook)
- [Modifying Existing Hooks](#modifying-existing-hooks)
- [Hook Configuration](#hook-configuration)
- [Testing Hooks](#testing-hooks)
- [Common Patterns](#common-patterns)
- [Troubleshooting](#troubleshooting)

## Hook Architecture

### How Hooks Work

1. **Definition**: Hooks are defined in `kit.yaml` with two required sections
2. **Installation**: `dot-agent kit install` writes hook configuration to:
   - `dot-agent.toml` (kit metadata)
   - `.claude/settings.json` (Claude Code configuration)
3. **Execution**: When lifecycle event fires, Claude Code:
   - Runs the invocation command
   - Captures output
   - Displays output to the assistant

### Hook Flow Diagram

```
kit.yaml                    Installation                Runtime
┌──────────────┐           ┌─────────────┐           ┌──────────────┐
│ kit_cli_     │           │             │           │              │
│ commands:    │ ───────►  │ dot-agent   │ ───────► │ Claude Code  │
│  - script    │           │ kit install │           │ reads        │
│              │           │             │           │ settings.json│
│ hooks:       │           │ Writes to:  │           │              │
│  - id        │           │ • .toml     │           │ Fires on     │
│  - lifecycle │           │ • .json     │           │ event        │
│  - matcher   │           │             │           │              │
└──────────────┘           └─────────────┘           └──────────────┘
```

## Creating a New Hook

### Step 1: Create Directory Structure

```bash
packages/dot-agent-kit/src/dot_agent_kit/data/kits/{kit-name}/
├── kit_cli_commands/
│   ├── __init__.py
│   └── {kit-name}/
│       ├── __init__.py
│       └── {hook_name}.py
└── kit.yaml
```

**Naming Convention**: Use `{kit-name}-reminder-hook` pattern for consistency.

### Step 2: Implement Hook Script

Create `{hook_name}.py`:

```python
#!/usr/bin/env python3
"""
{Kit Name} Reminder Command

Outputs the {kit-name} reminder for UserPromptSubmit hook.
This command is invoked via dot-agent run {kit-name} {hook-name}.
"""

import click


@click.command()
def {function_name}() -> None:
    """Output {kit-name} reminder for UserPromptSubmit hook."""
    click.echo("Your reminder text here")


if __name__ == "__main__":
    {function_name}()
```

**Critical Requirements**:

- Function name MUST match file name (snake_case)
- Use `click.echo()` not `print()`
- Keep logic simple - hooks run on every matching event
- Keep reminder text concise

### Step 3: Configure kit.yaml

Add both sections to `kit.yaml`:

```yaml
name: { kit-name }
version: 0.1.0
description: Your kit description
license: MIT

# Section 1: Define the CLI command
kit_cli_commands:
  - name: { hook-name } # Kebab-case
    path: kit_cli_commands/{kit-name}/{hook_script}.py
    description: Output reminder for UserPromptSubmit hook

# Section 2: Configure the hook
hooks:
  - id: { hook-name } # Must match kit_cli_commands name
    lifecycle: UserPromptSubmit
    matcher: "*" # or "*.py" for Python files only
    invocation: dot-agent run {kit-name} {hook-name}
    description: Hook description
    timeout: 30
```

**Both sections are REQUIRED** - the hook won't work with only one.

### Step 4: Install and Test

```bash
# In development mode (with symlinks)
uv pip install -e packages/dot-agent-kit --force-reinstall --no-deps
uv run dot-agent kit install {kit-name}

# Test the hook directly
uv run dot-agent run {kit-name} {hook-name}

# Verify installation
uv run dot-agent kit show {kit-name}
```

## Modifying Existing Hooks

### Renaming a Hook

When renaming a hook (e.g., `compliance-reminder-hook` → `dignified-python-reminder-hook`):

1. **Rename the script file**:

   ```bash
   mv old_name.py new_name.py
   ```

2. **Update function name in script**:

   ```python
   # Old
   def old_function_name() -> None:

   # New
   def new_function_name() -> None:
   ```

3. **Update kit.yaml** (both sections):

   ```yaml
   kit_cli_commands:
     - name: new-hook-name
       path: kit_cli_commands/{kit}/{new_name}.py

   hooks:
     - id: new-hook-name
       invocation: dot-agent run {kit} new-hook-name
   ```

4. **Reinstall the kit**:
   ```bash
   uv pip install -e packages/dot-agent-kit --force-reinstall --no-deps
   uv run dot-agent kit remove {kit-name}
   uv run dot-agent kit install {kit-name}
   ```

### Common Pitfall: Function Name Mismatch

**Error**: `Warning: Command '{hook}' does not have expected function '{function_name}'`

**Cause**: Function name doesn't match file name

**Fix**: Ensure function name matches file name (with underscores):

- File: `my_reminder_hook.py`
- Function: `def my_reminder_hook()`

## Hook Configuration

### Lifecycle Events

Currently supported:

- `UserPromptSubmit` - Fires when user submits a prompt

### Matcher Patterns

| Pattern      | Behavior                           | Example Use Case           |
| ------------ | ---------------------------------- | -------------------------- |
| `*`          | Fires on every prompt              | General reminders          |
| `*.py`       | Fires when Python files in context | Language-specific guidance |
| `*.{ts,tsx}` | Multiple extensions                | Framework-specific hints   |
| `Makefile`   | Specific file name                 | Build system reminders     |

### Timeout Configuration

- Default: 30 seconds
- Keep hooks fast - they run frequently
- Avoid complex logic or network calls

## Testing Hooks

### Manual Testing

```bash
# Test hook execution directly
uv run dot-agent run {kit-name} {hook-name}

# Should output:
# Your reminder text
```

### Verification Checklist

- [ ] Hook appears in `dot-agent kit show {kit-name}`
- [ ] Hook ID in `dot-agent.toml` matches kit.yaml
- [ ] Hook configuration in `.claude/settings.json`
- [ ] Direct execution produces expected output
- [ ] Function name matches file name

### Testing in Claude Code

After installation, hooks will fire automatically:

- Matcher `*` hooks appear on every prompt
- Matcher `*.py` hooks appear when Python files are in context

## Common Patterns

### Reminder Hooks

Most common pattern - provides contextual reminders:

```python
@click.command()
def devrun_reminder_hook() -> None:
    """Output devrun agent reminder for UserPromptSubmit hook."""
    click.echo("🛠️ Use devrun agent for pytest, pyright, ruff, prettier, make, gt commands")
```

### Conditional Output

For more complex scenarios:

```python
@click.command()
@click.option('--verbose', is_flag=True, help='Show detailed reminder')
def conditional_hook(verbose: bool) -> None:
    """Output conditional reminder based on context."""
    if verbose:
        click.echo("Detailed reminder with multiple lines")
        click.echo("• Point 1")
        click.echo("• Point 2")
    else:
        click.echo("Brief reminder")
```

### Multi-Kit Coordination

Hooks from different kits can work together:

- Use unique IDs following `{kit-name}-reminder-hook` pattern
- Different matchers prevent conflicts
- Order of execution determined by `.claude/settings.json`

## Troubleshooting

### Hook Not Firing

**Check**:

1. Hook appears in `dot-agent kit show {kit-name}`
2. `.claude/settings.json` contains hook configuration
3. Matcher pattern matches current context
4. No syntax errors in hook script

### Installation Issues

**Problem**: Changes not reflected after editing

**Solution**:

```bash
# Force reinstall package and kit
uv pip install -e packages/dot-agent-kit --force-reinstall --no-deps
uv run dot-agent kit remove {kit-name}
uv run dot-agent kit install {kit-name}
```

### Common Errors

| Error                           | Cause                   | Solution                          |
| ------------------------------- | ----------------------- | --------------------------------- |
| `No such command '{hook-name}'` | Function name mismatch  | Ensure function matches file name |
| `Missing artifact`              | kit.yaml path incorrect | Verify path in kit_cli_commands   |
| `Hook not in settings.json`     | Installation failed     | Remove and reinstall kit          |
| `No output from hook`           | Missing echo statements | Add `click.echo()` calls          |

## Best Practices

### DO

- ✅ Use consistent naming: `{kit-name}-reminder-hook`
- ✅ Keep hooks fast and simple
- ✅ Output clear, concise reminder text
- ✅ Test hooks before committing
- ✅ Use appropriate matchers (not everything needs `*`)

### DON'T

- ❌ Use underscores in hook IDs (use kebab-case)
- ❌ Forget either kit_cli_commands or hooks section
- ❌ Include complex logic in hooks
- ❌ Make network calls or slow operations
- ❌ Output verbose or multi-line reminders unnecessarily

## Related Documentation

- [ARTIFACT_LIFECYCLE.md](ARTIFACT_LIFECYCLE.md) - General artifact management
- [KIT_CLI_COMMANDS.md](KIT_CLI_COMMANDS.md) - Kit CLI command patterns
- [DEVELOPING.md](../DEVELOPING.md) - Kit development workflow
- [GLOSSARY.md](GLOSSARY.md) - Terminology and concepts
