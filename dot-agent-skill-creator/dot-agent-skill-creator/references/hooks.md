# Hook Configuration for Deterministic Skill Discovery

## Overview

Hooks ensure skills are discovered and loaded when needed. They solve the problem of skills not being triggered despite having appropriate descriptions in frontmatter.

## How Hooks Work

1. **User action triggers hook** (e.g., editing a file)
2. **Hook runs CLI command** (usually a reminder)
3. **Command output appears in context** (brief message)
4. **Agent sees reminder and loads skill**

## Hook Configuration in settings.json

### Basic Structure

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*.py",
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

### Multiple Matchers

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*.py",
        "hooks": [
          {
            "type": "command",
            "command": "DOT_AGENT_KIT_ID=python-kit DOT_AGENT_HOOK_ID=python-reminder dot-agent run python-kit reminder",
            "timeout": 30
          }
        ]
      },
      {
        "matcher": "*.js|*.ts|*.tsx",
        "hooks": [
          {
            "type": "command",
            "command": "DOT_AGENT_KIT_ID=javascript-kit dot-agent run javascript-kit reminder",
            "timeout": 30
          }
        ]
      },
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "dot-agent run general-kit context-check",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

## Creating Reminder Hooks

### Simple Reminder Hook

```python
# src/my_kit/hooks.py
import click
import sys

@click.command()
def reminder_hook():
    """Output reminder to load skill."""
    click.echo("🔴 Load my-skill when working with data files", err=True)
    sys.exit(0)
```

### Conditional Reminder Hook

```python
import click
import os
import sys
from pathlib import Path

@click.command()
def smart_reminder():
    """Conditionally suggest skill based on context."""
    # Check environment variables set by dot-agent
    file_pattern = os.environ.get('DOT_AGENT_FILE_PATTERN', '')
    kit_id = os.environ.get('DOT_AGENT_KIT_ID', '')

    # Determine if we should activate
    if should_activate(file_pattern):
        message = get_context_message(file_pattern)
        click.echo(message, err=True)

    sys.exit(0)

def should_activate(pattern: str) -> bool:
    """Determine if skill is relevant."""
    relevant_extensions = {'.data', '.csv', '.json', '.yaml'}
    return any(pattern.endswith(ext) for ext in relevant_extensions)

def get_context_message(pattern: str) -> str:
    """Generate appropriate reminder message."""
    if pattern.endswith('.csv'):
        return "🔴 Load data-processor skill for CSV operations"
    elif pattern.endswith('.json'):
        return "🔴 Load data-processor skill for JSON validation and transformation"
    else:
        return "🔴 Load data-processor skill for data file operations"
```

### Advanced Context-Aware Hook

```python
@click.command()
@click.option('--verbose', is_flag=True, envvar='DOT_AGENT_VERBOSE')
def context_aware_hook(verbose: bool):
    """Sophisticated hook with multiple checks."""
    reminders = []

    # Check for Python files
    if check_python_context():
        reminders.append("🔴 Load dignified-python for Python 3.13+ standards")

    # Check for test files
    if check_test_context():
        reminders.append("🔴 Load fake-based-testing for test patterns")

    # Check for git operations
    if check_git_context():
        reminders.append("🔴 Load gt-graphite for stacked PRs")

    # Output all relevant reminders
    for reminder in reminders:
        click.echo(reminder, err=True)

    if verbose and reminders:
        click.echo(f"ℹ️ {len(reminders)} skills suggested", err=True)

    sys.exit(0)

def check_python_context() -> bool:
    """Check if working with Python files."""
    pattern = os.environ.get('DOT_AGENT_FILE_PATTERN', '')
    return pattern.endswith('.py')

def check_test_context() -> bool:
    """Check if working with test files."""
    pattern = os.environ.get('DOT_AGENT_FILE_PATTERN', '')
    return 'test_' in pattern or '_test.py' in pattern

def check_git_context() -> bool:
    """Check if in git repository with branches."""
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            timeout=1
        )
        return result.returncode == 0 and result.stdout.strip() != 'main'
    except:
        return False
```

## Hook Patterns

### Pattern 1: File Extension Triggers

```json
{
  "matcher": "*.py",
  "hooks": [
    {
      "type": "command",
      "command": "dot-agent run python-kit python-reminder",
      "timeout": 30
    }
  ]
}
```

Use for:

- Language-specific skills
- File format handlers
- Domain-specific tools

### Pattern 2: Directory Pattern Triggers

```json
{
  "matcher": "tests/**/*.py",
  "hooks": [
    {
      "type": "command",
      "command": "dot-agent run testing-kit test-reminder",
      "timeout": 30
    }
  ]
}
```

Use for:

- Test-specific skills
- Build system skills
- Project structure dependent skills

### Pattern 3: Universal Triggers

```json
{
  "matcher": "*",
  "hooks": [
    {
      "type": "command",
      "command": "dot-agent run context-kit analyze-context",
      "timeout": 30
    }
  ]
}
```

Use for:

- General productivity skills
- Context analysis
- Cross-cutting concerns

## Environment Variables

Hooks receive these environment variables:

| Variable                 | Description               | Example              |
| ------------------------ | ------------------------- | -------------------- |
| `DOT_AGENT_FILE_PATTERN` | Current file pattern      | `src/main.py`        |
| `DOT_AGENT_KIT_ID`       | Kit identifier            | `my-kit`             |
| `DOT_AGENT_HOOK_ID`      | Hook identifier           | `reminder-hook`      |
| `DOT_AGENT_WORKING_DIR`  | Current working directory | `/home/user/project` |

## Hook Best Practices

### 1. Keep Messages Brief

```python
# ✅ Good - concise and actionable
click.echo("🔴 Load data-validator for schema validation", err=True)

# ❌ Bad - too verbose
click.echo("You should consider loading the data-validator skill because you're working with JSON files and this skill provides comprehensive validation capabilities including schema validation, format conversion, and data transformation utilities", err=True)
```

### 2. Use Consistent Markers

```python
# Use consistent emoji/markers across hooks
"🔴 Load skill-name for [reason]"  # Critical/required
"🟡 Consider skill-name for [reason]"  # Suggested
"ℹ️ skill-name available for [reason]"  # Informational
```

### 3. Exit Codes

```python
# Always exit 0 for success
sys.exit(0)

# Never exit with error codes (blocks execution)
sys.exit(1)  # ❌ Don't do this
```

### 4. Error Handling

```python
@click.command()
def safe_reminder():
    """Hook with error handling."""
    try:
        # Check context
        if should_activate():
            click.echo("🔴 Load my-skill", err=True)
    except Exception:
        # Silently fail - don't break user workflow
        pass

    sys.exit(0)  # Always exit cleanly
```

### 5. Performance

```python
@click.command()
def fast_reminder():
    """Optimized for speed."""
    # Quick checks only - hooks run on every prompt
    import os

    # Fast: environment variable check
    if os.environ.get('QUICK_CHECK') == 'true':
        click.echo("🔴 Load my-skill", err=True)

    # Slow: avoid file I/O, network calls, heavy computation
    # ❌ data = Path('large-file.json').read_text()
    # ❌ response = requests.get('https://api.example.com')

    sys.exit(0)
```

## Testing Hooks

### Unit Test

```python
# tests/test_hooks.py
from click.testing import CliRunner
from my_kit.hooks import reminder_hook

def test_reminder_hook():
    runner = CliRunner()
    result = runner.invoke(reminder_hook)

    assert result.exit_code == 0
    assert "Load my-skill" in result.output
```

### Integration Test

```python
def test_hook_via_dot_agent():
    """Test hook works through dot-agent."""
    import subprocess

    env = {
        'DOT_AGENT_FILE_PATTERN': 'test.py',
        'DOT_AGENT_KIT_ID': 'my-kit'
    }

    result = subprocess.run(
        ['dot-agent', 'run', 'my-kit', 'reminder-hook'],
        env={**os.environ, **env},
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert "Load my-skill" in result.stderr
```

## Installation and Configuration

### During Kit Installation

Kits can automatically configure hooks:

```python
# src/my_kit/install.py
def install_hooks(settings_path: Path):
    """Add hooks to settings.json during kit installation."""
    settings = json.loads(settings_path.read_text())

    if 'hooks' not in settings:
        settings['hooks'] = {}

    if 'UserPromptSubmit' not in settings['hooks']:
        settings['hooks']['UserPromptSubmit'] = []

    # Add our hook
    hook_config = {
        "matcher": "*.data",
        "hooks": [{
            "type": "command",
            "command": "dot-agent run my-kit reminder-hook",
            "timeout": 30
        }]
    }

    settings['hooks']['UserPromptSubmit'].append(hook_config)
    settings_path.write_text(json.dumps(settings, indent=2))
```

### Manual Configuration

Users can manually add to `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*.py",
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

## Examples from Real Kits

### dignified-python Hook

```json
{
  "matcher": "*.py",
  "hooks": [
    {
      "type": "command",
      "command": "DOT_AGENT_KIT_ID=dignified-python-313 DOT_AGENT_HOOK_ID=dignified-python-reminder-hook dot-agent run dignified-python-313 dignified-python-reminder-hook",
      "timeout": 30
    }
  ]
}
```

Output:

```
🔴 Load dignified-python-313 skill when editing Python (LBYL: check conditions first, never try/except for control flow)
```

### devrun Hook

```json
{
  "matcher": "*",
  "hooks": [
    {
      "type": "command",
      "command": "DOT_AGENT_KIT_ID=devrun DOT_AGENT_HOOK_ID=devrun-reminder-hook dot-agent run devrun devrun-reminder-hook",
      "timeout": 30
    }
  ]
}
```

Output:

```
🛠️ Use devrun agent for: pytest, pyright, ruff, prettier, make, gt (with or without uv run)
```
