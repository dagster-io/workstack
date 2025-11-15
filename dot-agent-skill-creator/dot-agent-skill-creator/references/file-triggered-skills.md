# File-Type Triggered Skills Pattern

## Overview

Skills that activate automatically when working with specific file types provide seamless assistance without manual loading.

## Implementation Pattern

### 1. Define File Patterns

Identify the file patterns that should trigger the skill:

```toml
# kit.toml
[skills.my-skill]
path = "skills/my-skill"
auto_trigger = [
    "*.py",           # Python files
    "test_*.py",      # Test files
    "*_test.py",      # Alternative test pattern
    "**/*.yaml",      # YAML files in any directory
    ".github/**/*"    # GitHub workflow files
]
```

### 2. Create Activation Hook

```python
# src/my_kit/hooks.py
import click
import os
import sys
from pathlib import Path

@click.command()
def file_trigger_hook():
    """Check file pattern and suggest skill."""
    file_pattern = os.environ.get('DOT_AGENT_FILE_PATTERN', '')

    if not file_pattern:
        sys.exit(0)

    # Get file extension and name
    path = Path(file_pattern)
    ext = path.suffix
    name = path.name

    # Determine if skill applies
    message = get_activation_message(ext, name, path)

    if message:
        click.echo(message, err=True)

    sys.exit(0)

def get_activation_message(ext: str, name: str, path: Path) -> str | None:
    """Generate contextual activation message."""
    # Python files
    if ext == '.py':
        if 'test' in name:
            return "🔴 Load python-testing skill for test file patterns"
        elif path.parts and 'tests' in path.parts:
            return "🔴 Load python-testing skill for test directory"
        else:
            return "🔴 Load python-dev skill for Python development"

    # Configuration files
    elif ext in {'.yaml', '.yml'}:
        if '.github' in str(path):
            return "🔴 Load github-actions skill for workflow files"
        elif 'docker' in name.lower():
            return "🔴 Load docker skill for container configuration"
        else:
            return "🔴 Load yaml-tools skill for YAML operations"

    # Data files
    elif ext in {'.json', '.csv', '.parquet'}:
        return f"🔴 Load data-processor skill for {ext[1:].upper()} files"

    return None
```

### 3. Configure Hook in settings.json

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*.py",
        "hooks": [
          {
            "type": "command",
            "command": "dot-agent run python-kit file-trigger",
            "timeout": 30
          }
        ]
      },
      {
        "matcher": "*.yaml|*.yml",
        "hooks": [
          {
            "type": "command",
            "command": "dot-agent run yaml-kit file-trigger",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

## Common File-Type Patterns

### Programming Languages

```python
LANGUAGE_PATTERNS = {
    '.py': 'python-dev',
    '.js': 'javascript-dev',
    '.ts': 'typescript-dev',
    '.rs': 'rust-dev',
    '.go': 'golang-dev',
    '.java': 'java-dev',
    '.cpp': 'cpp-dev',
    '.c': 'c-dev',
    '.rb': 'ruby-dev',
    '.php': 'php-dev'
}

def get_language_skill(ext: str) -> str | None:
    """Get skill for programming language."""
    skill = LANGUAGE_PATTERNS.get(ext)
    if skill:
        return f"🔴 Load {skill} skill for {ext[1:].upper()} development"
    return None
```

### Configuration Files

```python
CONFIG_PATTERNS = {
    'Dockerfile': 'docker',
    'docker-compose.yml': 'docker-compose',
    'Makefile': 'make-tools',
    'package.json': 'npm-tools',
    'pyproject.toml': 'python-packaging',
    'Cargo.toml': 'rust-cargo',
    'go.mod': 'go-modules',
    '.gitignore': 'git-tools',
    '.env': 'env-config'
}

def get_config_skill(filename: str) -> str | None:
    """Get skill for configuration files."""
    skill = CONFIG_PATTERNS.get(filename)
    if skill:
        return f"🔴 Load {skill} skill for configuration"
    return None
```

### Directory-Based Patterns

```python
def get_directory_skill(path: Path) -> str | None:
    """Get skill based on directory context."""
    parts = path.parts

    if 'tests' in parts or 'test' in parts:
        return "🔴 Load testing skill for test files"

    if '.github' in parts:
        if 'workflows' in parts:
            return "🔴 Load github-actions skill"
        elif 'actions' in parts:
            return "🔴 Load github-actions-dev skill"

    if 'docs' in parts or 'documentation' in parts:
        return "🔴 Load documentation skill"

    if 'scripts' in parts:
        return "🔴 Load scripting skill"

    return None
```

## Advanced Patterns

### Multi-Skill Activation

```python
@click.command()
def multi_skill_hook():
    """Suggest multiple relevant skills."""
    file_pattern = os.environ.get('DOT_AGENT_FILE_PATTERN', '')
    path = Path(file_pattern)

    skills = []

    # Check for Python file
    if path.suffix == '.py':
        skills.append("python-dev")

        # Add test skill if test file
        if 'test' in path.name:
            skills.append("python-testing")

        # Add type checking if typed
        if has_type_hints(path):
            skills.append("python-typing")

    # Output all relevant skills
    for skill in skills:
        click.echo(f"🔴 Load {skill} skill", err=True)

    sys.exit(0)

def has_type_hints(path: Path) -> bool:
    """Check if file uses type hints."""
    try:
        content = path.read_text()
        return '->' in content or ': ' in content
    except:
        return False
```

### Context-Aware Activation

```python
@click.command()
def smart_activation():
    """Activate based on file content and context."""
    file_pattern = os.environ.get('DOT_AGENT_FILE_PATTERN', '')

    if not should_activate(file_pattern):
        sys.exit(0)

    # Analyze file content
    analysis = analyze_file(file_pattern)

    # Generate specific message
    if analysis['has_api_calls']:
        msg = "🔴 Load api-testing skill for API test patterns"
    elif analysis['has_database']:
        msg = "🔴 Load database-testing skill for DB operations"
    elif analysis['has_mocks']:
        msg = "🔴 Load mock-patterns skill for mocking"
    else:
        msg = "🔴 Load testing skill for general test patterns"

    click.echo(msg, err=True)
    sys.exit(0)

def analyze_file(pattern: str) -> dict:
    """Analyze file content for patterns."""
    try:
        content = Path(pattern).read_text()
        return {
            'has_api_calls': 'requests.' in content or 'httpx.' in content,
            'has_database': 'SELECT' in content or 'db.' in content,
            'has_mocks': 'mock.' in content or '@patch' in content
        }
    except:
        return {}
```

### Performance Optimization

```python
# Cache file pattern checks
from functools import lru_cache

@lru_cache(maxsize=100)
def should_process_file(pattern: str) -> bool:
    """Cache decision for repeated files."""
    path = Path(pattern)

    # Quick reject non-relevant files
    if path.suffix in {'.pyc', '.pyo', '.so', '.dll'}:
        return False

    if any(part.startswith('.') for part in path.parts):
        return False  # Hidden directories

    return True

@click.command()
def optimized_hook():
    """Fast hook with caching."""
    pattern = os.environ.get('DOT_AGENT_FILE_PATTERN', '')

    if not should_process_file(pattern):
        sys.exit(0)

    # Process only if relevant
    message = get_skill_message(pattern)
    if message:
        click.echo(message, err=True)

    sys.exit(0)
```

## Testing File-Triggered Skills

### Unit Tests

```python
# tests/test_file_triggers.py
import pytest
from my_kit.hooks import get_activation_message
from pathlib import Path

def test_python_file_trigger():
    """Test Python file detection."""
    msg = get_activation_message('.py', 'main.py', Path('src/main.py'))
    assert msg is not None
    assert 'python' in msg.lower()

def test_test_file_trigger():
    """Test file in test directory."""
    msg = get_activation_message('.py', 'test_foo.py', Path('tests/test_foo.py'))
    assert msg is not None
    assert 'test' in msg.lower()

def test_yaml_file_trigger():
    """Test YAML file detection."""
    msg = get_activation_message('.yaml', 'config.yaml', Path('config.yaml'))
    assert msg is not None
    assert 'yaml' in msg.lower()

def test_no_trigger():
    """Test file that shouldn't trigger."""
    msg = get_activation_message('.txt', 'readme.txt', Path('readme.txt'))
    assert msg is None
```

### Integration Tests

```python
def test_hook_with_python_file():
    """Test hook activation for Python files."""
    env = {
        **os.environ,
        'DOT_AGENT_FILE_PATTERN': 'src/main.py'
    }

    result = subprocess.run(
        ['dot-agent', 'run', 'my-kit', 'file-trigger'],
        env=env,
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    assert 'python' in result.stderr.lower()
```

## Best Practices

1. **Be Specific** - Target exact file patterns
2. **Consider Context** - Use directory structure
3. **Avoid Over-Triggering** - Don't activate for everything
4. **Provide Clear Messages** - Explain why skill is relevant
5. **Test Thoroughly** - Verify patterns match correctly
6. **Cache When Possible** - Optimize for repeated files
7. **Handle Errors Silently** - Don't break user workflow
