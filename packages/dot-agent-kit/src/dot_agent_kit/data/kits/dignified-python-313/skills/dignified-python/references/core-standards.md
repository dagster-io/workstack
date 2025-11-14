# Core Python Standards - Detailed Reference

This document contains the detailed patterns and examples for foundational Python standards. For quick reference and navigation, see the main SKILL.md file.

---

## Exception Handling

### LBYL (Look Before You Leap) vs EAFP

**The fundamental principle: ALWAYS use LBYL, NEVER EAFP for control flow**

LBYL means checking conditions before acting. EAFP (Easier to Ask for Forgiveness than Permission) means trying operations and catching exceptions. In dignified Python, we strongly prefer LBYL.

### Dictionary Access Patterns

```python
# ✅ CORRECT: Membership testing
if key in mapping:
    value = mapping[key]
    process(value)
else:
    handle_missing()

# ✅ ALSO CORRECT: .get() with default
value = mapping.get(key, default_value)
process(value)

# ✅ CORRECT: Check before nested access
if "config" in data and "timeout" in data["config"]:
    timeout = data["config"]["timeout"]

# ❌ WRONG: KeyError as control flow
try:
    value = mapping[key]
except KeyError:
    handle_missing()

# ❌ WRONG: Nested try/except
try:
    timeout = data["config"]["timeout"]
except KeyError:
    timeout = default_timeout
```

### When Exceptions ARE Acceptable

#### 1. Error Boundaries

```python
# ✅ ACCEPTABLE: CLI command error boundary
@click.command("create")
@click.pass_obj
def create(ctx: WorkstackContext, name: str) -> None:
    """Create a worktree."""
    try:
        create_worktree(ctx, name)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Git command failed: {e.stderr}", err=True)
        raise SystemExit(1)
```

#### 2. Third-Party API Compatibility

```python
# ✅ ACCEPTABLE: Third-party API forces exception handling
def _get_bigquery_sample(sql_client, table_name):
    """
    BigQuery's TABLESAMPLE doesn't work on views.
    There's no reliable way to determine a priori whether
    a table supports TABLESAMPLE.
    """
    try:
        return sql_client.run_query(f"SELECT * FROM {table_name} TABLESAMPLE...")
    except Exception:
        return sql_client.run_query(f"SELECT * FROM {table_name} ORDER BY RAND()...")
```

#### 3. Adding Context Before Re-raising

```python
# ✅ ACCEPTABLE: Adding context before re-raising
try:
    process_file(config_file)
except yaml.YAMLError as e:
    raise ValueError(f"Failed to parse config file {config_file}: {e}") from e
```

### Encapsulation Pattern

When you must violate exception norms, encapsulate the violation:

```python
def _get_sample_with_fallback(client, table):
    """Encapsulated exception handling with clear documentation."""
    try:
        return client.sample_method(table)
    except SpecificAPIError:
        # Documented reason for exception handling
        return client.fallback_method(table)

# Caller doesn't see the exception handling
def analyze(table):
    sample = _get_sample_with_fallback(client, table)
    return process(sample)
```

---

## Type Annotations

### Python 3.13+ Syntax

**CRITICAL**: Never use `from __future__ import annotations` - Python 3.13+ doesn't need it.

#### Basic Types

```python
# ✅ CORRECT: Modern syntax
def process_items(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

def find_user(user_id: int) -> User | None:
    return users.get(user_id)

def handle_data(data: str | bytes) -> None:
    if isinstance(data, str):
        data = data.encode()

# ❌ WRONG: Legacy syntax
from typing import List, Dict, Optional, Union
def process_items(items: List[str]) -> Dict[str, int]: ...
def find_user(user_id: int) -> Optional[User]: ...
def handle_data(data: Union[str, bytes]) -> None: ...
```

#### Collections and Generics

```python
# ✅ CORRECT: Built-in generics
def get_mapping() -> dict[str, list[int]]:
    return {"numbers": [1, 2, 3]}

def process_queue(items: list[tuple[str, int]]) -> None:
    for name, value in items:
        process(name, value)

# Type aliases for complex types
UserMap = dict[int, User]
ProcessQueue = list[tuple[str, int]]
```

#### Key Differences from Older Python

| Old (Python 3.8-3.9)                 | New (Python 3.13+) |
| ------------------------------------ | ------------------ |
| `List[str]`                          | `list[str]`        |
| `Dict[str, int]`                     | `dict[str, int]`   |
| `Tuple[str, ...]`                    | `tuple[str, ...]`  |
| `Set[int]`                           | `set[int]`         |
| `Optional[str]`                      | `str \| None`      |
| `Union[str, int]`                    | `str \| int`       |
| `from __future__ import annotations` | Not needed         |

---

## Path Operations

### The Golden Rule

**ALWAYS check `.exists()` BEFORE `.resolve()` or `.is_relative_to()`**

```python
# ✅ CORRECT: Check exists first
for wt_path in worktree_paths:
    if wt_path.exists():
        wt_path_resolved = wt_path.resolve()
        if current_dir.is_relative_to(wt_path_resolved):
            current_worktree = wt_path_resolved
            break

# ❌ WRONG: Using exceptions for path validation
try:
    wt_path_resolved = wt_path.resolve()
    if current_dir.is_relative_to(wt_path_resolved):
        current_worktree = wt_path_resolved
except (OSError, ValueError):
    continue
```

### Why This Matters

- `.resolve()` raises `OSError` for non-existent paths
- `.is_relative_to()` raises `ValueError` for invalid comparisons
- Checking `.exists()` first avoids exceptions entirely

### Pathlib Best Practices

```python
from pathlib import Path

# ✅ CORRECT: pathlib operations
config_path = Path.home() / ".workstack" / "config.toml"
if config_path.exists():
    content = config_path.read_text(encoding="utf-8")
    data = tomllib.loads(content)

# Path operations
absolute_path = config_path.resolve()  # After checking .exists()
expanded_path = Path("~/.config").expanduser()
parent_dir = config_path.parent
file_stem = config_path.stem
file_extension = config_path.suffix

# ❌ WRONG: os.path operations
import os
config_path = os.path.join(os.path.expanduser("~"), ".workstack", "config.toml")
```

### File Operations

**Always specify encoding explicitly:**

```python
# ✅ CORRECT: Explicit encoding
content = path.read_text(encoding="utf-8")
path.write_text(data, encoding="utf-8")

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# ❌ WRONG: Implicit encoding (system-dependent)
content = path.read_text()
with open(path) as f:
    content = f.read()
```

---

## Dependency Injection

### ABC vs Protocol

**Use ABC for interfaces, never Protocol**

```python
# ✅ CORRECT: Use ABC for interfaces
from abc import ABC, abstractmethod

class Repository(ABC):
    @abstractmethod
    def save(self, entity: Entity) -> None:
        """Save entity to storage."""
        ...

    @abstractmethod
    def load(self, id: str) -> Entity:
        """Load entity by ID."""
        ...

class PostgresRepository(Repository):
    def save(self, entity: Entity) -> None:
        # Implementation
        pass

    def load(self, id: str) -> Entity:
        # Implementation
        pass

# ❌ WRONG: Using Protocol
from typing import Protocol

class Repository(Protocol):
    def save(self, entity: Entity) -> None: ...
    def load(self, id: str) -> Entity: ...
```

### Benefits of ABC

1. **Explicit inheritance** - Clear class hierarchy
2. **Runtime validation** - Errors if abstract methods not implemented
3. **Better IDE support** - Autocomplete and refactoring work better
4. **Documentation** - Clear contract definition

### Implementation Pattern

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Define the interface
class DataStore(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None:
        """Retrieve value by key."""
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Store value with key."""
        ...

# Implementation
class RedisStore(DataStore):
    def __init__(self, client):
        self.client = client

    def get(self, key: str) -> str | None:
        return self.client.get(key)

    def set(self, key: str, value: str) -> None:
        self.client.set(key, value)

# Testing with fake
class FakeStore(DataStore):
    def __init__(self):
        self.data = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value
```

---

## Imports

### Module-Level Imports

**ALWAYS place imports at module level, NEVER inline**

```python
# ✅ CORRECT: Module-level imports
import json
import click
from pathlib import Path
from workstack.config import load_config

def my_function() -> None:
    data = json.loads(content)
    click.echo("Processing")
    config = load_config()

# ❌ WRONG: Inline imports
def my_function() -> None:
    import json  # NEVER do this
    import click  # NEVER do this
    data = json.loads(content)
```

### Acceptable Inline Import Exceptions

#### 1. Circular Dependency Resolution

```python
# ✅ ACCEPTABLE: Breaking circular import
def process_user(user_id: int) -> None:
    # Circular import: user.py imports processor.py
    from .user import User
    user = User.get(user_id)
```

#### 2. Performance Optimization

```python
# ✅ ACCEPTABLE: Expensive import deferred
def analyze_data(data: dict) -> Report:
    """Analyze data using heavy ML library."""
    import tensorflow as tf  # 30+ second import time
    model = tf.load_model("model.h5")
    return model.predict(data)
```

### Absolute vs Relative Imports

**ALWAYS use absolute imports**

```python
# ✅ CORRECT: Absolute imports
from workstack.config import load_config
from workstack.core import discover_repo_context
from workstack.utils.git import get_current_branch

# ❌ WRONG: Relative imports
from .config import load_config
from ..core import discover_repo_context
from ...utils.git import get_current_branch
```

### Import Organization

Group imports in three sections:

```python
# Standard library
import os
import sys
from pathlib import Path
from typing import Any

# Third-party
import click
import yaml
from pydantic import BaseModel

# Local application
from workstack.config import Config
from workstack.core import Context
from workstack.utils import helpers
```

---

## Anti-Patterns

### Exception Swallowing

```python
# ❌ NEVER swallow exceptions silently
try:
    risky_operation()
except:
    pass

try:
    risky_operation()
except Exception:
    pass

# ✅ Let exceptions bubble up (default)
risky_operation()
```

### Exception Transformation Without Value

```python
# ❌ BAD: Unnecessary transformation
try:
    croniter(cron_string, now).get_next(datetime)
except Exception as e:
    raise ValueError(f"Invalid cron string: {e}")

# ✅ GOOD: Let original exception bubble
croniter(cron_string, now).get_next(datetime)

# ✅ ACCEPTABLE: Adding meaningful context
try:
    croniter(cron_string, now).get_next(datetime)
except Exception as e:
    raise ValueError(
        f"Cron job '{job_name}' has invalid schedule '{cron_string}': {e}"
    ) from e
```

### Silent Fallback Behavior

**NEVER implement silent fallback when primary approach fails**

```python
# ❌ WRONG: Silent fallback to inferior approach
def process_text(text: str) -> dict[str, Any]:
    try:
        result = llm_client.process(text)
        return result
    except Exception:
        # Untested fallback that masks failure
        return regex_parse_fallback(text)

# ✅ CORRECT: Let error bubble to boundary
def process_text(text: str) -> dict[str, Any]:
    return llm_client.process(text)

@click.command()
def process_command(input_file: Path) -> None:
    try:
        result = process_text(text)
        click.echo(f"Complete: {result}")
    except LLMError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
```

### Preserving Unnecessary Backwards Compatibility

```python
# ❌ WRONG: Keeping old API unnecessarily
def process_data(data: dict, legacy_format: bool = False) -> Result:
    if legacy_format:
        return legacy_process(data)
    return new_process(data)

# ✅ CORRECT: Break and migrate immediately
def process_data(data: dict) -> Result:
    return new_process(data)
```

### Default Arguments Without Documentation

```python
# ❌ BAD: Unclear why None is default
def process_data(data, format=None):
    pass

# ✅ BEST: No defaults - explicit at call sites
def process_data(data, format):
    """Process data in the specified format.

    Args:
        format: Format to use. Use None for auto-detection.
    """
    if format is None:
        format = detect_format(data)
```

### Code in `__init__.py`

```python
# ❌ WRONG: Code in __init__.py
"""Configuration module."""
from workstack.config.loader import load_config
from workstack.config.writer import write_config
__all__ = ["load_config", "write_config"]

# ✅ CORRECT: Empty __init__.py
# (file is completely empty or docstring-only)
```

### Speculative Tests

```python
# ❌ FORBIDDEN: Tests for future features
# def test_feature_we_might_add():
#     """Placeholder for future feature."""
#     pass

# ✅ CORRECT: TDD for current implementation
def test_feature_being_built_now():
    result = new_feature()  # Implementing next
    assert result == expected
```

---

## Backwards Compatibility Philosophy

**Default stance: NO backwards compatibility preservation**

Only preserve backwards compatibility when:

- Code is clearly part of public API
- User explicitly requests it
- Migration cost is prohibitively high (rare)

Benefits:

- Cleaner, maintainable codebase
- Faster iteration
- No legacy code accumulation
- Simpler mental models

---

## Decision Checklist

### Before writing `try/except`:

- [ ] Is this at an error boundary? (CLI/API level)
- [ ] Can I check the condition proactively? (LBYL)
- [ ] Am I adding meaningful context, or just hiding?
- [ ] Is third-party API forcing me to use exceptions?
- [ ] Have I encapsulated the violation?
- [ ] Am I catching specific exceptions, not broad?

**Default: Let exceptions bubble up**

### Before using type hints:

- [ ] Am I using `list[...]`, `dict[...]`, `str | None`?
- [ ] Have I removed `from __future__ import annotations`?
- [ ] Have I removed `List`, `Dict`, `Optional`, `Union` imports?

### Before path operations:

- [ ] Did I check `.exists()` before `.resolve()`?
- [ ] Did I check `.exists()` before `.is_relative_to()`?
- [ ] Am I using `pathlib.Path`, not `os.path`?
- [ ] Did I specify `encoding="utf-8"`?

### Before preserving backwards compatibility:

- [ ] Did the user explicitly request it?
- [ ] Is this a public API with external consumers?
- [ ] Have I documented why it's needed?
- [ ] Is migration cost prohibitively high?

**Default: Break the API and migrate callsites immediately**
