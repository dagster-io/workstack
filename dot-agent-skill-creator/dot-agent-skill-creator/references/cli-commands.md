# Creating CLI Commands for dot-agent Skills

## Overview

dot-agent CLI commands provide testable, discoverable functionality that can be used both within skills and standalone. They're superior to bundled scripts because they:

- Support external dependencies via Python packaging
- Are testable with proper unit tests
- Discoverable via `dot-agent run` CLI
- Can be versioned and distributed properly
- Work outside the skill context

## Kit Structure with CLI Commands

```
my-kit/
├── kit.toml                    # Kit configuration
├── pyproject.toml               # Python package config
├── skills/
│   └── my-skill/
│       ├── SKILL.md
│       └── references/
│           └── patterns.md
├── src/
│   └── my_kit/                 # Python package
│       ├── __init__.py
│       ├── commands.py         # CLI command implementations
│       └── utils.py            # Shared utilities
└── tests/
    └── test_commands.py        # Unit tests
```

## Creating a Basic Command

### 1. Define the Command Function

```python
# src/my_kit/commands.py
import click
import json
from pathlib import Path

@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--format', default='json', type=click.Choice(['json', 'yaml']))
def process_file(input_file: str, format: str) -> None:
    """Process a file and output in specified format."""
    path = Path(input_file)
    data = json.loads(path.read_text())

    if format == 'json':
        output = json.dumps(data, indent=2)
    else:
        import yaml
        output = yaml.dump(data)

    click.echo(output)
```

### 2. Register in kit.toml

```toml
[kit]
id = "my-kit"
name = "My Kit"
version = "0.1.0"
description = "Kit with CLI commands and skill"

[commands.process-file]
type = "python"
module = "my_kit.commands"
function = "process_file"
description = "Process files and convert formats"

[skills.my-skill]
path = "skills/my-skill"
```

### 3. Use in Skills

Reference the command in SKILL.md:

````markdown
## CLI Commands

Process data files using:

```bash
dot-agent run my-kit process-file input.json --format yaml
```
````

````

## Advanced Command Patterns

### Command with Subcommands

```python
# src/my_kit/commands.py
@click.group()
def data_cli():
    """Data processing commands."""
    pass

@data_cli.command()
@click.argument('input_file')
def validate(input_file: str):
    """Validate data file."""
    # Implementation
    click.echo(f"Validating {input_file}")

@data_cli.command()
@click.argument('input_file')
@click.argument('output_file')
def transform(input_file: str, output_file: str):
    """Transform data between formats."""
    # Implementation
    click.echo(f"Transforming {input_file} to {output_file}")

# Register group in kit.toml
# [commands.data]
# type = "python"
# module = "my_kit.commands"
# function = "data_cli"
````

### Command with External Dependencies

```python
# pyproject.toml
[project]
name = "my-kit"
dependencies = [
    "pandas>=2.0.0",
    "requests>=2.31.0",
    "pydantic>=2.0.0"
]

# src/my_kit/commands.py
import pandas as pd
import requests
from pydantic import BaseModel

class DataSchema(BaseModel):
    name: str
    value: float

@click.command()
@click.argument('csv_file')
def analyze_csv(csv_file: str):
    """Analyze CSV using pandas."""
    df = pd.read_csv(csv_file)

    # Use external libraries
    summary = df.describe()
    click.echo(summary.to_string())
```

### Reminder Hook Commands

Create hooks that inject reminders into context:

```python
# src/my_kit/hooks.py
import click
import sys

@click.command()
def reminder_hook():
    """Output reminder to use skill."""
    # Check if we should activate
    if should_activate():
        click.echo("🔴 Load my-skill when working with data files", err=True)
        sys.exit(0)
    else:
        # Silent exit if not relevant
        sys.exit(0)

def should_activate() -> bool:
    """Determine if skill should be suggested."""
    # Check environment variables, file patterns, etc.
    import os
    return os.environ.get('DOT_AGENT_FILE_PATTERN', '').endswith('.data')
```

Register in kit.toml:

```toml
[commands.reminder-hook]
type = "python"
module = "my_kit.hooks"
function = "reminder_hook"
```

## Testing CLI Commands

### Unit Tests

```python
# tests/test_commands.py
import pytest
from click.testing import CliRunner
from my_kit.commands import process_file

def test_process_file_json():
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create test file
        with open('test.json', 'w') as f:
            f.write('{"key": "value"}')

        # Run command
        result = runner.invoke(process_file, ['test.json', '--format', 'json'])

        assert result.exit_code == 0
        assert '"key": "value"' in result.output

def test_process_file_yaml():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('test.json', 'w') as f:
            f.write('{"key": "value"}')

        result = runner.invoke(process_file, ['test.json', '--format', 'yaml'])

        assert result.exit_code == 0
        assert 'key: value' in result.output
```

### Integration Tests

```python
def test_command_via_dot_agent():
    """Test command works through dot-agent CLI."""
    import subprocess

    result = subprocess.run(
        ['dot-agent', 'run', 'my-kit', 'process-file', 'test.json'],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
```

## Command Best Practices

### 1. Output Formatting

```python
@click.command()
@click.option('--json', is_flag=True, help='Output as JSON')
def list_items(json: bool):
    items = get_items()

    if json:
        # Machine-readable output
        click.echo(json.dumps(items))
    else:
        # Human-readable output
        for item in items:
            click.echo(f"- {item['name']}: {item['status']}")
```

### 2. Error Handling

```python
@click.command()
def risky_operation():
    try:
        perform_operation()
    except SpecificError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(2)
```

### 3. Progress Feedback

```python
@click.command()
def long_operation():
    items = get_many_items()

    with click.progressbar(items, label='Processing') as bar:
        for item in bar:
            process_item(item)
```

### 4. Configuration

```python
@click.command()
@click.option('--config', type=click.Path(exists=True),
              envvar='MY_KIT_CONFIG',
              help='Config file path')
def configured_command(config: str | None):
    if config:
        settings = load_config(config)
    else:
        settings = get_default_config()
```

## Common Command Types

### Data Processing

```python
@click.command()
@click.argument('input_file')
@click.argument('output_file')
@click.option('--format', type=click.Choice(['json', 'yaml', 'toml']))
def convert(input_file: str, output_file: str, format: str):
    """Convert between data formats."""
    # Implementation
```

### API Integration

```python
@click.command()
@click.option('--api-key', envvar='API_KEY', required=True)
@click.argument('endpoint')
def api_call(api_key: str, endpoint: str):
    """Make API call with authentication."""
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(f"https://api.example.com/{endpoint}", headers=headers)
    click.echo(response.json())
```

### File Generation

```python
@click.command()
@click.argument('name')
@click.option('--template', default='default')
def generate(name: str, template: str):
    """Generate file from template."""
    template_content = get_template(template)
    output = template_content.format(name=name)

    output_path = Path(f"{name}.generated")
    output_path.write_text(output)
    click.echo(f"Generated {output_path}")
```

## Integration with Skills

### Documenting Commands in SKILL.md

````markdown
## CLI Commands

The following commands are available via this kit:

### Data Operations

```bash
# Validate data file
dot-agent run my-kit validate data.json

# Transform between formats
dot-agent run my-kit transform input.json output.yaml

# Analyze CSV files
dot-agent run my-kit analyze-csv data.csv
```
````

### Schema Generation

```bash
# Generate schema from sample data
dot-agent run my-kit generate-schema sample.json > schema.json
```

For implementation details, see the kit repository.

````

### Using Commands in Skill Workflows

```markdown
## Workflow

### Step 1: Validate Input

First, validate the data structure:

```bash
dot-agent run my-kit validate input.json
````

### Step 2: Transform Data

Convert to required format:

```bash
dot-agent run my-kit transform input.json processed.yaml
```

### Step 3: Generate Report

Create analysis report:

```bash
dot-agent run my-kit analyze processed.yaml > report.md
```

```

## Advantages Over Bundled Scripts

| Aspect | Bundled Scripts | CLI Commands |
|--------|-----------------|--------------|
| Dependencies | Manual management | pip/pyproject.toml |
| Testing | Difficult | Standard pytest |
| Discovery | Hidden in skill | `dot-agent run` |
| Versioning | With skill only | Semantic versioning |
| Reusability | Skill context only | Standalone usage |
| Documentation | In skill only | CLI help + skill |
| Distribution | Skill package | PyPI/Git |
```
