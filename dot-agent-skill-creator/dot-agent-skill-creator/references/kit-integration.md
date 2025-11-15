# Building Skills as Part of Kits

## Overview

Kits bundle skills with CLI commands, hooks, and Python packages for complete functionality. This provides better organization, distribution, and testing compared to standalone skills.

## Kit Structure

```
my-kit/
├── kit.toml                     # Kit manifest
├── pyproject.toml                # Python package configuration
├── README.md                     # Kit documentation
├── skills/                       # Skills bundled with kit
│   └── my-skill/
│       ├── SKILL.md
│       └── references/
│           ├── patterns.md
│           └── examples.md
├── src/                          # Python source code
│   └── my_kit/
│       ├── __init__.py
│       ├── commands.py          # CLI commands
│       ├── hooks.py             # Hook implementations
│       └── utils.py             # Shared utilities
├── tests/                        # Test suite
│   ├── test_commands.py
│   └── test_hooks.py
└── .agent/                       # dot-agent metadata (generated)
    └── kits/
        └── my-kit/
            └── registry-entry.md
```

## Creating a Kit

### 1. Initialize Kit Structure

```bash
# Create kit directory
mkdir my-kit
cd my-kit

# Initialize Python package
cat > pyproject.toml << EOF
[project]
name = "my-kit"
version = "0.1.0"
description = "My dot-agent kit with skills and commands"
dependencies = [
    "click>=8.0.0",
    "pydantic>=2.0.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "mypy>=1.0.0"
]
EOF

# Create source structure
mkdir -p src/my_kit
mkdir -p skills/my-skill/references
mkdir tests
```

### 2. Create kit.toml

```toml
[kit]
id = "my-kit"
name = "My Kit"
version = "0.1.0"
description = "Comprehensive kit for X functionality"
author = "Your Name"
repo_url = "https://github.com/yourusername/my-kit"

# CLI Commands
[commands.process]
type = "python"
module = "my_kit.commands"
function = "process_command"
description = "Process data files"

[commands.validate]
type = "python"
module = "my_kit.commands"
function = "validate_command"
description = "Validate against schema"

[commands.reminder-hook]
type = "python"
module = "my_kit.hooks"
function = "reminder_hook"
description = "Skill activation reminder"

# Bundled Skills
[skills.my-skill]
path = "skills/my-skill"
auto_trigger = ["*.data", "*.json"]
```

### 3. Implement Commands

```python
# src/my_kit/commands.py
import click
import json
from pathlib import Path
from typing import Any

@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file path')
def process_command(input_file: str, output: str | None) -> None:
    """Process data file with transformations."""
    data = load_data(input_file)
    processed = transform_data(data)

    if output:
        save_data(processed, output)
        click.echo(f"✅ Processed data saved to {output}")
    else:
        click.echo(json.dumps(processed, indent=2))

def load_data(path: str) -> dict[str, Any]:
    """Load data from file."""
    file_path = Path(path)
    if file_path.suffix == '.json':
        return json.loads(file_path.read_text())
    else:
        raise ValueError(f"Unsupported format: {file_path.suffix}")

def transform_data(data: dict[str, Any]) -> dict[str, Any]:
    """Apply transformations to data."""
    # Implementation
    return data

def save_data(data: dict[str, Any], path: str) -> None:
    """Save data to file."""
    Path(path).write_text(json.dumps(data, indent=2))
```

### 4. Implement Hooks

```python
# src/my_kit/hooks.py
import click
import os
import sys

@click.command()
def reminder_hook() -> None:
    """Remind to load skill based on context."""
    file_pattern = os.environ.get('DOT_AGENT_FILE_PATTERN', '')

    if should_trigger(file_pattern):
        click.echo(
            f"🔴 Load my-skill for {get_file_type(file_pattern)} operations",
            err=True
        )

    sys.exit(0)

def should_trigger(pattern: str) -> bool:
    """Check if skill should be suggested."""
    triggers = {'.data', '.json', '.yaml', '.csv'}
    return any(pattern.endswith(ext) for ext in triggers)

def get_file_type(pattern: str) -> str:
    """Get human-readable file type."""
    ext = Path(pattern).suffix
    types = {
        '.json': 'JSON',
        '.yaml': 'YAML',
        '.csv': 'CSV',
        '.data': 'data file'
    }
    return types.get(ext, 'file')
```

### 5. Create the Skill

````markdown
# skills/my-skill/SKILL.md

---

name: my-skill
description: This skill should be used when working with data files that need validation, transformation, or analysis. It provides CLI commands for common operations and patterns for handling various data formats.

---

# My Skill

Process and validate data files efficiently.

## Overview

This skill provides tools for working with structured data files including JSON, YAML, and CSV formats.

## Quick Start

```bash
# Validate a data file
dot-agent run my-kit validate data.json

# Process and transform
dot-agent run my-kit process input.json -o output.json
```
````

## CLI Commands

Available commands via `dot-agent run my-kit`:

- **validate <file>** - Validate file structure and content
- **process <file>** - Apply transformations
- **analyze <file>** - Generate analysis report

## Patterns

For implementation patterns, see:

- `references/patterns.md` - Common data processing patterns
- `references/examples.md` - Complete examples

````

## Testing the Kit

### Unit Tests for Commands

```python
# tests/test_commands.py
import pytest
from click.testing import CliRunner
from my_kit.commands import process_command

def test_process_command_json_output():
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create test file
        with open('test.json', 'w') as f:
            f.write('{"key": "value"}')

        result = runner.invoke(process_command, ['test.json'])

        assert result.exit_code == 0
        assert '"key"' in result.output

def test_process_command_file_output():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('test.json', 'w') as f:
            f.write('{"key": "value"}')

        result = runner.invoke(
            process_command,
            ['test.json', '--output', 'output.json']
        )

        assert result.exit_code == 0
        assert Path('output.json').exists()
````

### Integration Tests

```python
# tests/test_integration.py
import subprocess

def test_kit_commands_via_dot_agent():
    """Test commands work through dot-agent CLI."""
    # Test validation command
    result = subprocess.run(
        ['dot-agent', 'run', 'my-kit', 'validate', 'test.json'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0 or "not found" in result.stderr

def test_hook_activation():
    """Test hook produces expected output."""
    env = {
        **os.environ,
        'DOT_AGENT_FILE_PATTERN': 'test.json'
    }

    result = subprocess.run(
        ['dot-agent', 'run', 'my-kit', 'reminder-hook'],
        env=env,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "Load my-skill" in result.stderr
```

## Installing the Kit

### Local Development

```bash
# Install Python package in editable mode
pip install -e .

# Register kit with dot-agent
dot-agent kit install .
```

### From Repository

```bash
# Install directly from git
dot-agent kit install https://github.com/username/my-kit

# Or with specific version
dot-agent kit install https://github.com/username/my-kit@v1.0.0
```

### Configuration Update

The kit installation automatically updates `.claude/settings.json`:

```json
{
  "kits": {
    "my-kit": {
      "version": "0.1.0",
      "path": "/path/to/my-kit",
      "enabled": true
    }
  },
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*.json",
        "hooks": [
          {
            "type": "command",
            "command": "dot-agent run my-kit reminder-hook",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

## Kit Development Workflow

### 1. Develop Incrementally

Start with minimal functionality and expand:

```bash
# Start with one command
my-kit/
├── kit.toml          # Single command
├── src/
│   └── my_kit/
│       └── commands.py  # One function
└── skills/
    └── my-skill/
        └── SKILL.md  # Basic skill
```

### 2. Test Locally

```bash
# Install in development mode
pip install -e .

# Test commands directly
python -m my_kit.commands process test.json

# Test via dot-agent
dot-agent run my-kit process test.json
```

### 3. Add Features

Gradually add:

- More commands
- Hook functionality
- Reference documentation
- Additional skills

### 4. Version and Release

```bash
# Update version in kit.toml and pyproject.toml
# Tag release
git tag v0.1.0
git push --tags

# Users can install specific version
dot-agent kit install github.com/user/kit@v0.1.0
```

## Best Practices

### 1. Namespace Commands

Group related commands:

```toml
[commands."data:validate"]
# Instead of just "validate"

[commands."data:process"]
# Instead of just "process"
```

### 2. Provide Help Text

```python
@click.command()
@click.option('--format', help='Output format (json|yaml|csv)')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def command(format: str, verbose: bool):
    """Process data files with optional format conversion.

    Examples:
        dot-agent run my-kit process data.json --format yaml
        dot-agent run my-kit process data.csv --verbose
    """
    pass
```

### 3. Handle Errors Gracefully

```python
@click.command()
def safe_command():
    try:
        risky_operation()
    except FileNotFoundError as e:
        click.echo(f"Error: File not found - {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(2)
```

### 4. Document in Multiple Places

- **kit.toml** - Command descriptions
- **SKILL.md** - User-facing documentation
- **README.md** - Developer documentation
- **Command help** - CLI --help text

### 5. Version Compatibility

```python
# src/my_kit/__init__.py
__version__ = "0.1.0"

def check_compatibility():
    """Verify kit works with current environment."""
    import sys
    if sys.version_info < (3, 10):
        raise RuntimeError("Kit requires Python 3.10+")
```

## Examples of Successful Kits

### dignified-python-313

- Skill with coding standards
- Hook for automatic activation
- No CLI commands (skill-focused)

### gt (Graphite)

- Multiple CLI commands for git operations
- Skill with workflow documentation
- Complex command interactions

### devrun

- Auto-detection of test tools
- Multiple runner commands
- Smart hook that suggests appropriate tool

Each demonstrates different aspects of kit development.
