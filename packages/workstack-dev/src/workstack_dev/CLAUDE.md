# Dev CLI Implementation Guidelines

## Command Structure

All workstack-dev commands follow this structure:

```
commands/
├── my-command/
│   ├── __init__.py   # Optional - may contain docstring or be omitted
│   └── command.py    # Click command with all logic
```

## Critical: Function Naming Convention

**The Click command function MUST be named `{command_name}_command`** to match the import in `cli.py`.

```python
# ✅ CORRECT - Function name matches import expectation
@click.command(name="land-branch")
def land_branch_command() -> None:
    """Command implementation."""
    pass

# ❌ WRONG - Generic name 'command' won't be found by cli.py
@click.command(name="land-branch")
def command() -> None:  # pyright will report: "land_branch_command" is unknown import symbol
    """Command implementation."""
    pass
```

**Naming pattern:**

- Command name: `my-command` (kebab-case in CLI)
- Function name: `my_command_command` (snake_case with `_command` suffix)
- File location: `commands/my_command/command.py`

## Static Import Architecture

The `cli.py` module uses **static imports** (not dynamic command discovery) to enable shell completion:

```python
# cli.py
from workstack_dev.commands.land_branch.command import land_branch_command
from workstack_dev.commands.clean_cache.command import clean_cache_command

cli.add_command(land_branch_command)
cli.add_command(clean_cache_command)
```

Click's completion mechanism requires all commands to be available at import time for inspection.

## Implementation Guidelines

- **All logic goes in `command.py`**: No business logic in `__init__.py`
- **Use Click for CLI**: Command definition, argument parsing, and output
- **Existing dependencies only**: Use workstack-dev's dependencies (no external packages)
- **`__init__.py` is optional**: May contain docstring, be empty, or be omitted entirely

## Command Types

### Standard Commands

Most commands use `@click.command()`:

```python
@click.command(name="branch-commit-count")
def branch_commit_count_command() -> None:
    """Count commits on current branch since Graphite parent."""
    # Implementation
```

### Command Groups (Subcommands)

Commands with subcommands use `@click.group()`:

```python
@click.group(name="completion")
def completion_command() -> None:
    """Generate shell completion scripts."""
    pass

@completion_command.command(name="bash")
def bash() -> None:
    """Generate bash completion script."""
    # Implementation
```

## Examples

Existing commands that demonstrate these patterns:

- `land-branch` - Graphite stack landing workflow with dataclasses and JSON output
- `branch-commit-count` - Simple command with git subprocess calls
- `clean-cache` - Command with options (--dry-run, --verbose)
- `codex-review` - Complex command with file I/O and template processing
- `completion` - Command group with bash/zsh/fish subcommands
- `publish-to-pypi` - Multi-step workflow with validation and error handling

## Documentation Maintenance

**IMPORTANT**: When making meaningful changes to workstack-dev's structure or architecture:

- Update `/.agent/WORKSTACK_DEV.md` to reflect the changes
- This file provides architectural overview for the broader project documentation
- Keep both files in sync to prevent documentation drift
