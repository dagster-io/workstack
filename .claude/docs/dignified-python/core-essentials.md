# Core Python Essentials

**ALWAYS LOADED**: These patterns appear in >80% of Python code.

---

## LBYL - The Cornerstone Principle

**Look Before You Leap: Check conditions proactively, NEVER use exceptions for control flow.**

This is the single most important rule in dignified Python. Every check below flows from this principle.

```python
# ✅ CORRECT: Check first
if key in mapping:
    value = mapping[key]
    process(value)

# ❌ WRONG: Exception as control flow
try:
    value = mapping[key]
    process(value)
except KeyError:
    pass
```

### Exception Handling Boundaries

Exceptions are ONLY acceptable at:

1. **Error boundaries** (CLI/API level)
2. **Third-party API compatibility** (when no alternative exists)
3. **Adding context before re-raising**

```python
# ✅ ACCEPTABLE: CLI error boundary
@click.command()
def my_command():
    try:
        do_work()
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: {e.stderr}", err=True)
        raise SystemExit(1)
```

**For complete exception guidance:** Load @exception-handling.md

---

## Pathlib Over os.path

**ALWAYS use `pathlib.Path`, NEVER use `os.path`**

```python
# ✅ CORRECT: pathlib
from pathlib import Path

config_path = Path.home() / ".erk" / "config.toml"
if config_path.exists():
    content = config_path.read_text(encoding="utf-8")

# ❌ WRONG: os.path
import os
config_path = os.path.join(os.path.expanduser("~"), ".erk", "config.toml")
```

### Critical Path Safety Rule

**ALWAYS check `.exists()` BEFORE `.resolve()` or `.is_relative_to()`**

```python
# ✅ CORRECT: Check exists first
if path.exists():
    resolved = path.resolve()

# ❌ WRONG: Will raise OSError if path doesn't exist
resolved = path.resolve()
```

**For complete path guidance:** Load @path-operations.md

---

## ABC Over Protocol

**Use `abc.ABC` for interfaces, NEVER use `typing.Protocol`**

```python
# ✅ CORRECT: ABC for interfaces
from abc import ABC, abstractmethod

class Repository(ABC):
    @abstractmethod
    def save(self, entity: Entity) -> None:
        ...

class PostgresRepository(Repository):
    def save(self, entity: Entity) -> None:
        # Implementation
        pass

# ❌ WRONG: Protocol
from typing import Protocol

class Repository(Protocol):
    def save(self, entity: Entity) -> None: ...
```

**Why ABC:**

- Explicit inheritance (clear hierarchy)
- Runtime validation (errors if methods not implemented)
- Better IDE support
- Clear contract definition

**For complete DI guidance:** Load @dependency-injection.md

---

## Module-Level Imports (Default Stance)

**Default: ALWAYS place imports at module level**

```python
# ✅ CORRECT: Module-level imports
import json
from pathlib import Path
from erk.config import load_config

def my_function():
    data = json.loads(content)
    config = load_config()

# ❌ WRONG: Inline imports without justification
def my_function():
    import json  # NEVER do this
    data = json.loads(content)
```

**Inline imports are ONLY acceptable for:**

- Circular import prevention (with comment)
- TYPE_CHECKING imports
- Conditional features (dry-run mode, debug mode)
- Expensive imports (>5s load time, documented)

**For complete import guidance:** Load @imports.md

---

## Absolute Imports Only

**ALWAYS use absolute imports, NEVER relative imports**

```python
# ✅ CORRECT: Absolute imports
from erk.config import load_config
from erk.core import discover_context
from erk.utils.git import get_branch

# ❌ WRONG: Relative imports
from .config import load_config
from ..core import discover_context
from ...utils.git import get_branch
```

**Why absolute:**

- Clear source location
- Better grepability
- No ambiguity about module paths
- Refactoring tools work correctly

---

## CLI Output: click.echo() Not print()

**In CLI code, ALWAYS use `click.echo()`, NEVER use `print()`**

```python
# ✅ CORRECT: click.echo()
import click

@click.command()
def my_command():
    click.echo("Processing...")
    click.echo(f"Error: {msg}", err=True)

# ❌ WRONG: print()
def my_command():
    print("Processing...")
    print(f"Error: {msg}")
```

**Why click.echo:**

- Handles unicode correctly across platforms
- Supports stderr with `err=True`
- Testing-friendly (Click's test runner captures it)
- Consistent CLI experience

**For complete CLI guidance:** Load @cli-patterns.md

---

## Subprocess Safety: check=True

**ALWAYS add `check=True` to `subprocess.run()`**

```python
# ✅ CORRECT: check=True raises on non-zero exit
result = subprocess.run(
    ["git", "status"],
    check=True,
    capture_output=True,
    text=True
)

# ❌ WRONG: Silent failures possible
result = subprocess.run(["git", "status"])
if result.returncode != 0:
    # Manual error handling (easy to forget)
    pass
```

**Why check=True:**

- Fails fast on command errors
- No need for manual returncode checking
- Consistent with LBYL (error bubbles to boundary)
- Prevents silent failures

**For complete subprocess guidance:** Load @subprocess.md

---

## Key Anti-Patterns Overview

### Never Swallow Exceptions

```python
# ❌ NEVER do this
try:
    risky_operation()
except:
    pass

# ✅ Let exceptions bubble
risky_operation()
```

### Never Use Silent Fallbacks

```python
# ❌ WRONG: Masks failure
try:
    return primary_method()
except:
    return fallback_method()

# ✅ CORRECT: Let error reach boundary
return primary_method()
```

### Never Preserve Backwards Compatibility by Default

```python
# ❌ WRONG: Unnecessary legacy support
def process(data, legacy: bool = False):
    if legacy:
        return old_way(data)
    return new_way(data)

# ✅ CORRECT: Break and migrate
def process(data):
    return new_way(data)
```

### Never Put Code in `__init__.py`

```python
# ❌ WRONG: Creates multiple import paths
# myapp/__init__.py
from myapp.core import Process
__all__ = ["Process"]

# ✅ CORRECT: Empty __init__.py, direct imports
# from myapp.core import Process
```

---

## Quick Decision Framework

**Before writing `try/except`:**

1. Is this at an error boundary? (CLI/API)
2. Can I check the condition first? (LBYL)
3. Is third-party API forcing me?

**Default: Let exceptions bubble**

**Before path operations:**

1. Did I check `.exists()` first?
2. Am I using pathlib, not os.path?
3. Did I specify `encoding="utf-8"`?

**Before adding inline imports:**

1. Is this breaking a circular dependency?
2. Is this TYPE_CHECKING only?
3. Is this conditional (dry-run, debug)?

**Default: Module-level imports**

---

## Loading Additional Guidance

For task-specific patterns, load the appropriate reference:

| Task Pattern               | Load Reference           |
| -------------------------- | ------------------------ |
| Exception handling details | @exception-handling.md   |
| Path operations            | @path-operations.md      |
| Dependency injection       | @dependency-injection.md |
| Import organization        | @imports.md              |
| CLI development            | @cli-patterns.md         |
| Subprocess usage           | @subprocess.md           |

**See @routing-patterns.md for automatic pattern detection.**
