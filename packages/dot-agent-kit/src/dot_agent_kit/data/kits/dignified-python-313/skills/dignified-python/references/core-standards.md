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
def create(ctx: ErkContext, name: str) -> None:
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
config_path = Path.home() / ".erk" / "config.toml"
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
config_path = os.path.join(os.path.expanduser("~"), ".erk", "config.toml")
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

**Default: ALWAYS place imports at module level**

Inline imports (imports inside functions or methods) should only be used in specific exceptional cases (see "Legitimate Inline Import Patterns" below for when exceptions apply).

```python
# ✅ CORRECT: Module-level imports
import json
import click
from pathlib import Path
from erk.config import load_config

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

### Legitimate Inline Import Patterns

While imports should generally be at module level, inline imports ARE acceptable in these specific cases:

#### 1. Circular Import Prevention

When module A imports module B and module B imports module A, inline imports break the cycle.

**Pattern:**

```python
# commands/sync.py
def register_commands(cli_group):
    """Register commands with CLI group (avoids circular import with main CLI entry)."""
    from myapp.cli import sync_command
    cli_group.add_command(sync_command)
```

**When to use:**

- CLI command registration to avoid circular dependencies
- Plugin systems with bidirectional dependencies
- Lazy loading of modules that would create import cycles

**Documentation guideline:** SHOULD include comment explaining the circular dependency

#### 2. Conditional Feature Imports

When code is only needed for specific runtime conditions (flags, modes, features).

**Pattern:**

```python
def process_data(data: dict, dry_run: bool = False) -> None:
    if dry_run:
        # Inline import: Only needed for dry-run mode, avoids loading in normal mode
        from myapp.dry_run import NoopProcessor
        processor = NoopProcessor()
    else:
        processor = RealProcessor()
    processor.execute(data)
```

**When to use:**

- Debug/verbose mode utilities
- Dry-run mode wrappers
- Optional feature modules
- Platform-specific implementations

**Documentation guideline:** SHOULD include comment explaining when import is needed

#### 3. TYPE_CHECKING Imports

For forward references and type annotations that would create circular imports.

**Pattern:**

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from myapp.models import User

def process_user(user: "User") -> None:
    ...
```

**When to use:**

- Type annotations that would create circular imports
- Expensive modules only needed for type checking
- Forward references to not-yet-defined types

**Documentation guideline:** No comment needed (standard Python pattern)

#### 4. Performance Optimization (Use Sparingly)

For truly expensive imports that would slow down application startup.

**Pattern:**

```python
def analyze_data(data: dict) -> Report:
    # Inline import: tensorflow takes 30+ seconds to load, only used for ML analysis
    import tensorflow as tf
    model = tf.load_model("model.h5")
    return model.predict(data)
```

**When to use:**

- ML libraries with 10+ second import times
- Large data processing modules
- Module initialization triggers expensive operations

**Documentation guideline:** MUST include comment with measured import time

#### 5. Test-Only Utilities

Test-specific imports inside test functions.

**Pattern:**

```python
def test_api_endpoint():
    # Test infrastructure import
    from myapp.testing import create_mock_client
    client = create_mock_client()
    assert client.get("/health") == 200
```

**When to use:**

- Test fixtures and helpers
- Mocking utilities
- Test data generators

**Documentation guideline:** Optional (common test pattern)

### Documentation Guideline for Inline Imports

**Recommendation (SHOULD):** Add explanatory comment for inline imports

While not strictly required, comments help maintain code clarity and prevent confusion about whether an inline import is intentional or poor organization.

**Comment format:**

```python
if feature_enabled:
    # Inline import: Only needed for optional feature, avoids loading in normal mode
    from myapp.features import advanced_processor
```

**What to include:**

1. **WHY** the import is inline (circular dependency? performance? conditional?)
2. **WHEN** the code path is executed (what triggers this import?)

**Examples:**

✅ **Good documentation:**

```python
def analyze_data(data: dict) -> Report:
    # Inline import: tensorflow takes 30+ seconds to load, only used for ML analysis
    import tensorflow as tf
    return tf.process(data)
```

❌ **Poor documentation:**

```python
def analyze_data(data: dict) -> Report:
    import tensorflow  # ML stuff
    return tensorflow.process(data)
```

⚠️ **No documentation (acceptable for obvious cases):**

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from myapp.models import User  # Standard pattern, self-explanatory
```

### Decision Tree: Should This Be an Inline Import?

Use this quick flowchart to determine if inline import is justified:

```
Is the import...

1. Using TYPE_CHECKING for type annotations?
   YES → ✅ Inline OK (standard Python pattern)
   NO → Continue to question 2

2. Causing a circular import if moved to module level?
   YES → ✅ Inline OK (document why)
   NO → Continue to question 3

3. Only needed when specific flag/condition is true?
   YES → ✅ Inline OK (document when used)
   NO → Continue to question 4

4. Expensive (>5 seconds) and rarely used?
   YES → ✅ Inline OK (document measured time)
   NO → Continue to question 5

5. Inside a test function?
   YES → ✅ Inline OK (test infrastructure)
   NO → ❌ Move to module level
```

**Default stance:** If none of the above apply, the import should be at module level.

### Anti-Patterns: When Inline Imports Are Wrong

#### 1. Hiding Import Costs Without Benefit

❌ **WRONG - Inline import of fast-loading standard library:**

```python
def format_date(dt):
    import datetime  # Why? datetime loads in milliseconds
    return datetime.strftime(dt, "%Y-%m-%d")
```

✅ **CORRECT - Module-level import:**

```python
import datetime

def format_date(dt):
    return datetime.strftime(dt, "%Y-%m-%d")
```

#### 2. Patching Poor Module Organization

❌ **WRONG - Using inline import to avoid refactoring circular dependency:**

```python
# models.py imports utils.py imports models.py
def helper_function():
    from .models import User  # Band-aid for circular import
    return User.query.all()
```

✅ **CORRECT - Refactor to break circular dependency:**

```python
# Extract shared code to separate module
# Or use dependency injection
# Or restructure module boundaries
```

#### 3. Conditional Import Without Clear Condition

❌ **WRONG - Inline import without runtime condition:**

```python
def process_data(data):
    from myapp.processor import DataProcessor  # Why inline?
    return DataProcessor().process(data)
```

✅ **CORRECT - Module-level import when always needed:**

```python
from myapp.processor import DataProcessor

def process_data(data):
    return DataProcessor().process(data)
```

### Absolute vs Relative Imports

**ALWAYS use absolute imports**

```python
# ✅ CORRECT: Absolute imports
from erk.config import load_config
from erk.core import discover_repo_context
from erk.utils.git import get_current_branch

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
from erk.config import Config
from erk.core import Context
from erk.utils import helpers
```

---

## Performance Expectations (`@property`, `__len__`)

### The Problem

Python's `@property` decorator and dunder methods like `__len__` create strong expectations about performance. Engineers reasonably assume these are cheap operations (modest assembly instructions, maybe a cached value lookup). Using them for expensive operations violates this expectation and causes performance issues.

### Property Access

**DON'T** hide expensive operations behind properties:

```python
# ❌ WRONG - Property doing I/O
class DataSet:
    @property
    def size(self) -> int:
        # Fetches from database!
        return self._fetch_count_from_db()

# ❌ WRONG - Property doing expensive computation
class PartitionSubset:
    @property
    def size(self) -> int:
        # Materializes ALL partition keys!
        return len(list(self._generate_all_partitions()))
```

**DO** make cost explicit or cache results:

```python
# ✅ CORRECT - Method name indicates cost
class DataSet:
    def fetch_size_from_db(self) -> int:
        return self._fetch_count_from_db()

# ✅ CORRECT - Cached for immutable objects
from functools import cached_property

@frozen
class PartitionSubset:
    @cached_property
    def size(self) -> int:
        # Computed once, cached forever (immutable)
        return len(list(self._generate_all_partitions()))
```

### Magic Methods (`__len__`, `__bool__`, etc.)

**DON'T** make magic methods expensive:

```python
# ❌ WRONG - __len__ doing expensive computation
class PartitionSubset:
    def __len__(self) -> int:
        # Materializes ALL partition keys!
        return len(list(self._generate_all_partitions()))

# ❌ WRONG - __bool__ doing I/O
class RemoteResource:
    def __bool__(self) -> bool:
        # Network call!
        return self._check_exists_on_server()
```

**DO** precompute or use explicit methods:

```python
# ✅ CORRECT - Precomputed
class EfficientSubset:
    def __init__(self, partitions: Sequence[str]):
        self._partitions = partitions
        self._count = len(partitions)  # Precompute

    def __len__(self) -> int:
        return self._count  # O(1)

# ✅ CORRECT - Explicit method for expensive operation
class RemoteResource:
    def exists_on_server(self) -> bool:
        """Check if resource exists (network call)."""
        return self._check_exists_on_server()
```

### Guidelines

1. **Properties should be O(1)** - Simple attribute access or cached value
2. **Use `@cached_property` for moderately expensive operations** - Only on immutable classes
3. **Use explicit methods for expensive operations** - Name should indicate cost
4. **Document performance characteristics** - If not obvious
5. **Never do I/O in properties or magic methods** - No file reads, network calls, or database queries

### Real Production Bug

**Customer on Discord**: `AssetSubset.size` property triggered 10,000+ partition key materializations via expensive cron parsing. What looked like a simple property access was actually:

- Parsing cron strings
- Generating all time-based partitions
- Materializing thousands of partition keys
- All from what appeared to be a cheap property access

**Rationale**: Engineers won't think twice about accessing properties in loops or using them multiple times. They assume it's cheap because the syntax makes it look cheap.

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

### Code in `__init__.py` and `__all__` Exports

**Core Principle:** One canonical location for every import.

Module code and `__all__` exports in `__init__.py` files violate this principle by creating multiple import paths for the same symbol. This anti-pattern damages codebase maintainability through reduced grepability, broken refactoring tools, and confused import analysis.

```python
# ❌ WRONG: Code in __init__.py
"""Configuration module."""
from erk.config.loader import load_config
from erk.config.writer import write_config

# ❌ WRONG: __all__ exports create duplicate import paths
__all__ = ["load_config", "write_config"]

# Now these symbols can be imported two ways:
# from erk.config import load_config  # Via __init__.py
# from erk.config.loader import load_config  # Direct import
# This duplication breaks the "one canonical location" principle

# ✅ CORRECT: Empty __init__.py
# (file is completely empty or docstring-only)
```

#### Why `__all__` Exports Are Prohibited

**1. Breaks Grepability**
When searching for where `load_config` is defined:

- `grep -r "def load_config"` finds the real definition
- But imports can come from multiple locations
- Refactoring tools can't reliably find all usage sites
- IDE "Find Usages" misses indirect imports through `__all__`

**2. Confuses Static Analysis**

- Type checkers may resolve imports differently
- Import cycles become harder to detect
- Dependency graphs show false relationships
- Tool confusion leads to missed errors

**3. Impairs Refactoring Safety**
When renaming or moving a function:

- Direct imports are easy to find and update
- `__all__` exports create hidden dependencies
- Automated refactoring tools miss re-export sites
- Manual refactoring becomes error-prone

**4. Violates Explicit > Implicit**

- Import source should be immediately clear
- `from erk.config import load_config` hides the real location
- `from erk.config.loader import load_config` shows exactly where it lives
- Explicit imports improve code navigation and understanding

#### The Right Way: Direct Imports Only

```python
# ✅ CORRECT: Import directly from the module that defines it
from erk.config.loader import load_config
from erk.config.writer import write_config

# Each symbol has ONE canonical import path
# Grep finds all usages reliably
# Refactoring tools work correctly
# Code navigation is predictable
```

#### Exception: Top-Level Public API Exports

For library packages that need to provide a clean public API to external consumers, controlled exports at the package's top level may be appropriate. This exception applies only when:

- The package is designed for external consumption
- API stability is a primary concern
- The exports define the public contract

This exception does not apply to internal application code or most project modules.

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
