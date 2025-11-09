# workstack-dev CLI Architecture

## Overview

`workstack-dev` is a **general-purpose development CLI** for tools and scripts used during workstack development. Commands are statically registered in `cli.py` to enable shell completion support.

**Key characteristics:**

- **Static imports**: Commands are explicitly imported and registered in `cli.py`
- **Single-file commands**: Each command's logic lives in one `command.py` file
- **Shell completion**: Click's completion requires static imports (not dynamic discovery)
- **Extensibility**: Adding new commands requires updating both the command file and `cli.py`

## Purpose

The `workstack-dev` CLI serves as a centralized home for development-time tools that don't belong in the main `workstack` user-facing CLI. These include:

- Build and release automation (e.g., `publish-to-pypi`)
- Maintenance tasks (e.g., `clean-cache`)
- Development utilities (e.g., `branch-commit-count`)
- Code review tooling (e.g., `codex-review`)
- Project-specific tooling

## Architecture

### Entry Point

Defined in `packages/workstack-dev/pyproject.toml`:

```toml
[project.scripts]
workstack-dev = "workstack_dev.__main__:cli"
```

### Core Components

```
packages/workstack-dev/
├── pyproject.toml
├── src/workstack_dev/
│   ├── __main__.py          # Entry point - imports cli from cli.py
│   ├── cli.py               # Static CLI definition with all command imports
│   ├── AGENTS.md            # Implementation guidelines for AI assistants
│   └── commands/            # Command implementations
│       ├── branch_commit_count/
│       │   ├── __init__.py  # Optional docstring
│       │   └── command.py   # Full Click command implementation
│       ├── clean_cache/
│       │   └── command.py   # Full Click command implementation
│       ├── codex_review/
│       │   ├── command.py   # Full Click command implementation
│       │   └── prompt.txt   # Codex prompt template
│       ├── completion/
│       │   └── command.py   # Command group with subcommands
│       ├── create_agents_symlinks/
│       │   └── command.py   # Full Click command implementation
│       ├── land_branch/
│       │   ├── __init__.py  # Optional docstring
│       │   └── command.py   # Full Click command implementation
│       ├── publish_to_pypi/
│       │   └── command.py   # Full Click command implementation
│       └── reserve_pypi_name/
│           └── command.py   # Full Click command implementation
└── tests/                   # Tests for workstack-dev commands
```

### CLI Initialization

The `cli.py` module uses **static imports** to enable shell completion:

```python
"""Static CLI definition for workstack-dev.

This module uses static imports instead of dynamic command loading to enable
shell completion. Click's completion mechanism requires all commands to be
available at import time for inspection.
"""

import click

from workstack_dev.commands.branch_commit_count.command import branch_commit_count_command
from workstack_dev.commands.clean_cache.command import clean_cache_command
from workstack_dev.commands.codex_review.command import codex_review_command
from workstack_dev.commands.completion.command import completion_command
from workstack_dev.commands.create_agents_symlinks.command import create_agents_symlinks_command
from workstack_dev.commands.land_branch.command import land_branch_command
from workstack_dev.commands.publish_to_pypi.command import publish_to_pypi_command
from workstack_dev.commands.reserve_pypi_name.command import reserve_pypi_name_command


@click.group(name="workstack-dev")
def cli() -> None:
    """Development tools for workstack."""
    pass


# Register all commands
cli.add_command(branch_commit_count_command)
cli.add_command(clean_cache_command)
cli.add_command(codex_review_command)
cli.add_command(completion_command)
cli.add_command(create_agents_symlinks_command)
cli.add_command(land_branch_command)
cli.add_command(publish_to_pypi_command)
cli.add_command(reserve_pypi_name_command)
```

**Why static imports?** Click's shell completion system inspects the CLI at import time to generate completion scripts. Dynamic command loading breaks this inspection mechanism.

### Command Structure Pattern

Each command follows a **single-file pattern** with all logic in `command.py`:

```python
# commands/branch_commit_count/command.py
"""Count commits on current branch since Graphite parent."""

import subprocess

import click


@click.command(name="branch-commit-count")
def branch_commit_count_command() -> None:
    """Count commits on current branch since Graphite parent."""
    # Get parent branch using gt parent
    result = subprocess.run(
        ["gt", "parent"],
        capture_output=True,
        text=True,
        check=False,
    )

    # Check for errors (LBYL pattern)
    if result.returncode != 0 or not result.stdout.strip():
        click.echo(
            "Error: No Graphite parent found. "
            "Use 'gt parent' to verify branch is tracked by Graphite.",
            err=True,
        )
        raise SystemExit(1)

    # Get merge base
    parent_branch = result.stdout.strip()
    merge_base = subprocess.run(
        ["git", "merge-base", "HEAD", parent_branch],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # Count commits
    count = subprocess.run(
        ["git", "rev-list", "--count", "HEAD", f"^{merge_base}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    # Output result
    click.echo(count)
```

**Critical naming convention:** The function MUST be named `{command_name}_command` (e.g., `my_command_command`) to match the import in `cli.py`.

### Command Types

#### Standard Commands

Most commands use `@click.command()`:

```python
@click.command(name="branch-commit-count")
def branch_commit_count_command() -> None:
    """Count commits on current branch since Graphite parent."""
    # Implementation
```

#### Command Groups (Subcommands)

Commands with subcommands use `@click.group()`:

```python
# commands/completion/command.py
"""Shell completion command for workstack-dev."""

import click


@click.group(name="completion")
def completion_command() -> None:
    """Generate shell completion scripts for workstack-dev."""


@completion_command.command(name="bash")
def bash() -> None:
    r"""Generate bash completion script.

    \b
    Temporary (current session only):
        source <(workstack-dev completion bash)

    Permanent installation:
        echo 'source <(workstack-dev completion bash)' >> ~/.bashrc
        source ~/.bashrc
    """
    # Implementation here
    click.echo("Completion script content...")


@completion_command.command(name="zsh")
def zsh() -> None:
    """Generate zsh completion script."""
    # Implementation here
    click.echo("Completion script content...")
```

## Adding a New Command

To add a new command to `workstack-dev`:

1. **Create command directory:**

   ```bash
   mkdir -p packages/workstack-dev/src/workstack_dev/commands/my_command
   ```

2. **Create `command.py`:**

   ```python
   """My command that does something useful."""

   import click


   @click.command(name="my-command")
   @click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
   def my_command_command(verbose: bool) -> None:
       """Command help text shown in --help."""
       if verbose:
           click.echo("Running my-command in verbose mode...")
       click.echo("Hello from my-command!")
   ```

3. **Update `cli.py`:**

   Add the import at the top (maintaining alphabetical order recommended):

   ```python
   from workstack_dev.commands.my_command.command import my_command_command
   ```

   Add the registration in the commands section:

   ```python
   cli.add_command(my_command_command)
   ```

4. **Optionally add `__init__.py`:**

   ```python
   """My command that does something useful."""
   ```

   Or leave it empty/omit it entirely - it's not required.

## Implementation Guidelines

See `packages/workstack-dev/src/workstack_dev/AGENTS.md` for detailed implementation guidelines including:

- Function naming conventions (`{command_name}_command`)
- Static import architecture requirements
- Click usage patterns
- Command group patterns
- Examples of existing commands

## Testing

Tests for workstack-dev commands follow standard pytest patterns and are located in the `tests/` directory.
