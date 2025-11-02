# Code Patterns and Examples

**📍 You are here**: [CLAUDE.md](../CLAUDE.md) → docs/PATTERNS.md

**Purpose**: Detailed examples for patterns referenced in CLAUDE.md coding standards.

**Related docs**:

- [CLAUDE.md](../CLAUDE.md) - Core coding rules
- [EXCEPTION_HANDLING.md](EXCEPTION_HANDLING.md) - Exception handling guide
- [GUIDE.md](GUIDE.md) - Documentation index

---

## Table of Contents

- [Type Annotations](#type-annotations)
- [Dependency Injection](#dependency-injection)
- [Import Organization](#import-organization)
- [Module Structure](#module-structure)
- [Exception Handling](#exception-handling)
- [Code Style](#code-style)
- [File Operations](#file-operations)
- [CLI Development](#cli-development)
- [Function Arguments](#function-arguments)
- [Context Managers](#context-managers)
- [Resource Management](#resource-management)

---

## Type Annotations

### Built-in Generic Types

Use lowercase built-in types instead of capitalized `typing` imports:

```python
# ✅ GOOD: Modern Python 3.13+ syntax
def process_items(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

def get_config(name: str | None = None) -> dict[str, Any]:
    ...

# ❌ BAD: Legacy Python <3.9 syntax
from typing import List, Dict, Optional, Union

def process_items(items: List[str]) -> Dict[str, int]:
    return {item: len(item) for item in items}

def get_config(name: Optional[str] = None) -> Dict[str, Any]:
    ...
```

### Union and Optional Types

```python
# ✅ GOOD: Modern union syntax
def find_user(user_id: int) -> User | None:
    ...

def process(data: str | bytes | Path) -> bool:
    ...

# ❌ BAD: Old Union/Optional syntax
from typing import Optional, Union

def find_user(user_id: int) -> Optional[User]:
    ...

def process(data: Union[str, bytes, Path]) -> bool:
    ...
```

### No String Quotes in Type Hints

```python
# ✅ GOOD: Direct type references
def foo(x: str | None) -> list[str]:
    ...

# ❌ BAD: Quoted type hints (unnecessary in Python 3.13+)
def foo(x: "str | None") -> "list[str]":
    ...
```

### Immutable Data Structures

Use `dataclass` with `frozen=True` for immutable data:

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class GlobalConfig:
    workstacks_root: Path
    use_graphite: bool
    show_pr_info: bool

# Usage - cannot be modified after creation
config = GlobalConfig(
    workstacks_root=Path("/home/user/workstacks"),
    use_graphite=True,
    show_pr_info=False,
)

# This would raise FrozenInstanceError:
# config.use_graphite = False
```

---

## Dependency Injection

### ABC Interface Pattern

**Always use ABC for interfaces, never Protocol:**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

class MyOps(ABC):
    """Abstract interface for my operations.

    All implementations (real and fake) must implement this interface.
    """

    @abstractmethod
    def do_something(self, arg: str) -> bool:
        """Perform operation."""
        ...

    @abstractmethod
    def get_status(self, path: Path) -> str:
        """Get status of resource."""
        ...


class RealMyOps(MyOps):
    """Production implementation."""

    def do_something(self, arg: str) -> bool:
        # Real implementation using subprocess, filesystem, etc.
        return True

    def get_status(self, path: Path) -> str:
        # Real status check
        return "active"


@dataclass(frozen=True)
class AppContext:
    """Application context with injected dependencies."""
    my_ops: MyOps
    other_ops: OtherOps
```

### Test Implementations (In-Memory Fakes)

Fakes must be in-memory only with state provided via constructor:

```python
# tests/fakes/my_ops.py
from pathlib import Path
from workstack.my_ops import MyOps

class FakeMyOps(MyOps):
    """In-memory fake - no filesystem access.

    State is held in memory. Constructor accepts initial state.
    """

    def __init__(
        self,
        *,
        results: dict[str, bool] | None = None,
        statuses: dict[Path, str] | None = None,
    ) -> None:
        """Create FakeMyOps with pre-configured state.

        Args:
            results: Mapping of arg -> return value for do_something()
            statuses: Mapping of path -> status for get_status()
        """
        self._results = results or {}
        self._statuses = statuses or {}

    def do_something(self, arg: str) -> bool:
        """Return pre-configured result."""
        return self._results.get(arg, True)

    def get_status(self, path: Path) -> str:
        """Return pre-configured status."""
        return self._statuses.get(path, "unknown")
```

### Why ABC Over Protocol

**Benefits of ABC:**

- **Explicit inheritance** makes interfaces discoverable through IDE navigation
- **Runtime validation** that implementations are complete (missing methods caught immediately)
- **Better IDE support** and error messages when implementing interfaces
- **More explicit about design intent** - signals this is a formal interface contract
- **Matches existing codebase patterns** - consistency with GitOps and other abstractions

**Why in-memory fakes:**

- **Faster tests** - no filesystem I/O overhead
- **No cleanup needed** - state automatically discarded
- **Explicit state** - test setup shows all configuration clearly
- **Parallel test execution** - no shared filesystem state

See also:

- [../CLAUDE.md](../CLAUDE.md) - Core rules for dependency injection

---

## Import Organization

### Three-Group Organization

Imports must be organized in three groups (enforced by isort/ruff):

1. Standard library imports
2. Third-party imports
3. Local imports

Within each group, imports should be alphabetically sorted.

```python
# ✅ GOOD: Three groups, alphabetically sorted
import os
import shlex
import subprocess
from pathlib import Path

import click

from workstack.activation import render_activation_script
from workstack.config import load_config
from workstack.core import discover_repo_context
```

### Top-Level vs Function-Scoped Imports

**ALWAYS use top-level (module-scoped) imports:**

```python
# ✅ GOOD: Top-level imports
from contextlib import contextmanager
from pathlib import Path

from workstack.config import load_config
from workstack.core import discover_repo_context

@contextmanager
def my_function(path: Path):
    config = load_config(path)
    repo = discover_repo_context(path)
    yield config, repo
```

```python
# ❌ BAD: Function-scoped imports without justification
@contextmanager
def my_function(path: Path):
    from workstack.config import load_config
    from workstack.core import discover_repo_context

    config = load_config(path)
    repo = discover_repo_context(path)
    yield config, repo
```

### Acceptable Function-Scoped Imports

**Only acceptable in these cases:**

1. **TYPE_CHECKING blocks** - Imports only needed for type annotations:

```python
# ✅ ACCEPTABLE: TYPE_CHECKING imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anthropic import Anthropic
    from workstack.gitops import GitOps
```

2. **Circular import resolution** - When imports would create circular dependencies:

```python
# ✅ ACCEPTABLE: Avoiding circular imports
def create_context_engine():
    # Import here to avoid circular dependency:
    # context_engine.py -> github_working_dir.py -> context_engine.py
    from workstack.context import WorkstackContext
    return WorkstackContext(...)
```

3. **Optional dependencies** - When import failure should be handled gracefully:

```python
# ✅ ACCEPTABLE: Optional dependency
def get_graphite_url():
    try:
        import graphite_client
        return graphite_client.get_url()
    except ImportError:
        return None
```

### Absolute Imports Only

```python
# ✅ GOOD: Absolute imports
from workstack.config import load_config
from workstack.core import discover_repo_context

# ❌ BAD: Relative imports
from .config import load_config
from .core import discover_repo_context
```

### No Import Aliasing

```python
# ✅ GOOD: Direct imports
from pathlib import Path
from workstack.gitops import RealGitOps

# ❌ BAD: Aliasing without reason
from pathlib import Path as P
from workstack.gitops import RealGitOps as GitOps
```

Exception: Aliasing is acceptable to resolve naming collisions with third-party packages.

---

## Module Structure

### Keep **init**.py Files Empty

**STRONGLY PREFER: Empty or docstring-only `__init__.py` files:**

```python
# ✅ GOOD: Empty __init__.py
# (file is completely empty)

# ✅ ACCEPTABLE: Docstring-only __init__.py
"""Module for configuration management."""

# ❌ BAD: Code in __init__.py
"""Configuration module."""

from workstack.config.loader import load_config
from workstack.config.writer import write_config

__all__ = ["load_config", "write_config"]
```

**Why keep `__init__.py` empty:**

- **Avoids circular imports** - Empty files can't create import cycles
- **Faster imports** - No code execution when package is imported
- **Clear dependencies** - Explicit imports show exactly where code comes from
- **Easier refactoring** - Moving modules doesn't require updating `__init__.py`
- **Better IDE support** - Direct imports work better with autocomplete and navigation

**Use absolute imports instead:**

```python
# ✅ GOOD: Direct, explicit imports
from workstack.config import load_config
from workstack.core import discover_repo_context

# ❌ BAD: Relying on __init__.py re-exports
from workstack import load_config, discover_repo_context
```

### Exception: Package Entry Points

Entry point modules may contain minimal initialization code:

```python
# ✅ ACCEPTABLE: src/workstack/__init__.py (package entry point)
"""workstack CLI entry point.

This package provides a Click-based CLI for managing git worktrees.
"""

from workstack.cli import cli


def main() -> None:
    """CLI entry point used by the `workstack` console script."""
    cli()
```

**When entry point code is acceptable:**

- Main package `__init__.py` that defines `main()` for console scripts
- Must be documented why the code is necessary
- Keep to absolute minimum (typically just entry point function)

**Examples in this codebase:**

- `src/workstack/__init__.py` - Defines `main()` entry point ✅
- `src/workstack/cli/commands/__init__.py` - Empty ✅
- `tests/__init__.py` - Docstring only ✅

### Rationale

Empty `__init__.py` files follow the principle of **explicit over implicit**. When imports are explicit (e.g., `from workstack.config import load_config`), it's immediately clear where the code comes from. Re-exporting through `__init__.py` creates indirection and hides the true source.

This pattern also prevents common issues:

1. **Circular imports** - Empty files can't participate in import cycles
2. **Import-time side effects** - No unexpected code execution when importing
3. **Namespace pollution** - Each module's exports are contained to that module

---

## Exception Handling

### LBYL vs EAFP

**This codebase uses LBYL (Look Before You Leap), NOT EAFP (Easier to Ask Forgiveness than Permission).**

Always check conditions before performing operations rather than catching exceptions:

```python
# ✅ CORRECT: Check before acting (LBYL)
if condition_is_valid(obj):
    result = perform_operation(obj)
else:
    result = handle_invalid_case()

# ❌ WRONG: Try and catch (EAFP)
try:
    result = perform_operation(obj)
except SomeError:
    result = handle_invalid_case()
```

### Dictionary Access

**ALWAYS check `in` before accessing dictionary keys:**

```python
# ✅ CORRECT: Check membership first
if key in mapping:
    value = mapping[key]
    process(value)
else:
    handle_missing_key()

# ❌ WRONG: Using KeyError as control flow
try:
    value = mapping[key]
    process(value)
except KeyError:
    handle_missing_key()

# ✅ ALSO CORRECT: Use .get() with default for simple cases
value = mapping.get(key, default_value)
process(value)
```

### Path Operations

**ALWAYS check `.exists()` before `.resolve()` or `.is_relative_to()`:**

```python
# ✅ CORRECT: Check exists first
for wt_path in worktree_paths:
    if wt_path.exists():
        wt_path_resolved = wt_path.resolve()
        if current_dir.is_relative_to(wt_path_resolved):
            current_worktree = wt_path_resolved
            break

# ❌ WRONG: Using exceptions for path validation
for wt_path in worktree_paths:
    try:
        wt_path_resolved = wt_path.resolve()
        if current_dir.is_relative_to(wt_path_resolved):
            current_worktree = wt_path_resolved
            break
    except (OSError, ValueError):
        continue
```

**Why**: `.resolve()` can raise `OSError` for invalid paths, permission issues, or symlink loops. `.is_relative_to()` can raise `ValueError` in edge cases. Checking `.exists()` makes your intent explicit and avoids exception overhead.

### When Exceptions Are Acceptable

**Only handle exceptions at error boundaries:**

```python
# ✅ ACCEPTABLE: Error boundary at CLI level
@click.command("process")
@click.argument("config_file")
def process_cmd(config_file: str) -> None:
    """Process data according to config file."""
    try:
        config = load_config(config_file)
        process_data(config)
    except FileNotFoundError:
        click.echo(f"Error: Config file not found: {config_file}", err=True)
        raise SystemExit(1)
    except yaml.YAMLError as e:
        click.echo(f"Error: Invalid YAML in {config_file}: {e}", err=True)
        raise SystemExit(1)
```

**See also**:

- [EXCEPTION_HANDLING.md](EXCEPTION_HANDLING.md) - Complete exception handling guide
- [CLAUDE.md](../CLAUDE.md#exception-handling--critical) - Core exception handling rules

---

## Code Style

### Reducing Nesting with Early Returns

**NEVER exceed 4 levels of indentation.** Use early returns and guard clauses:

```python
# ❌ BAD: Excessive nesting (5 levels)
def process_data(data):
    if data:                           # Level 1
        if validate(data):             # Level 2
            result = transform(data)
            if result:                 # Level 3
                if result.is_valid:    # Level 4
                    if save(result):   # Level 5 - TOO DEEP!
                        return True
    return False
```

```python
# ✅ GOOD: Early returns (max 2 levels)
def process_data(data):
    if not data:
        return False

    if not validate(data):
        return False

    result = transform(data)
    if not result:
        return False

    if not result.is_valid:
        return False

    return save(result)
```

### Extracting Functions to Reduce Nesting

```python
# ✅ GOOD: Extract helper function
def _validate_and_transform(data):
    """Validate and transform data, returning None on failure."""
    if not validate(data):
        return None

    result = transform(data)
    if not result or not result.is_valid:
        return None

    return result


def process_data(data):
    if not data:
        return False

    result = _validate_and_transform(data)
    if result is None:
        return False

    return save(result)
```

**When extracting functions:**

- Name with descriptive verbs (e.g., `_validate_input`, `_load_configuration`)
- Keep close to usage (typically just above calling function)
- Document what None/empty returns mean
- Prefix internal helpers with `_`

---

## File Operations

### Using pathlib.Path

**Always use `pathlib.Path` (never `os.path`):**

```python
from pathlib import Path

# ✅ GOOD: pathlib operations
config_path = Path.home() / ".workstack" / "config.toml"
content = config_path.read_text(encoding="utf-8")

if config_path.exists():
    data = tomllib.loads(content)

absolute_path = config_path.resolve()
expanded_path = Path("~/.config").expanduser()
```

```python
# ❌ BAD: os.path operations
import os

config_path = os.path.join(os.path.expanduser("~"), ".workstack", "config.toml")
with open(config_path, "r", encoding="utf-8") as f:
    content = f.read()

if os.path.exists(config_path):
    data = tomllib.loads(content)
```

### Common Path Operations

```python
from pathlib import Path

# Check existence
if config_path.exists():
    ...

# Check type
if data_path.is_file():
    ...
if output_dir.is_dir():
    ...

# Resolve paths
absolute_path = relative_path.resolve()

# Expand user home directory
home_config = Path("~/.config").expanduser()

# Read/write with encoding
content = path.read_text(encoding="utf-8")
path.write_text(content, encoding="utf-8")

# Join paths
project_dir = Path.cwd() / "src" / "workstack"
```

---

## CLI Development

### Command Definition Pattern

```python
import click
from pathlib import Path

from workstack.context import WorkstackContext
from workstack.core import discover_repo_context

@click.command("create")
@click.argument("name", metavar="NAME", required=False)
@click.option("--branch", type=str, help="Branch name to create")
@click.option("--no-post", is_flag=True, help="Skip post-create commands")
@click.pass_obj
def create(ctx: WorkstackContext, name: str | None, branch: str | None, no_post: bool) -> None:
    """Create a worktree and write a .env file."""
    # 1. Discover repo context
    repo = discover_repo_context(ctx, Path.cwd())

    # 2. Validate inputs
    if not name:
        click.echo("Error: NAME is required", err=True)
        raise SystemExit(1)

    # 3. Use ops via context
    worktrees = ctx.git_ops.list_worktrees(repo.root)

    # 4. Perform operations
    ctx.git_ops.add_worktree(repo.root, name, branch)

    # 5. Output results
    click.echo(f"Created worktree: {name}")
```

### Error Handling in CLI

```python
import click
import subprocess

# Error messages with err=True
if not wt_path.exists():
    click.echo(f"Worktree not found: {wt_path}", err=True)
    raise SystemExit(1)

# Clear, actionable messages
if branch_exists:
    click.echo(
        f"Error: Branch '{branch}' already exists. "
        f"Use --force to overwrite or choose a different name.",
        err=True,
    )
    raise SystemExit(1)

# Subprocess with check=True
result = subprocess.run(
    ["git", "status"],
    cwd=repo_root,
    check=True,  # Raises CalledProcessError on failure
    capture_output=True,
    text=True,
)
```

### Shell Completion

```python
from pathlib import Path
import click

from workstack.core import discover_repo_context, worktree_path_for

def _complete_worktree_name(ctx, param, incomplete):
    """Shell completion for worktree names."""
    try:
        context = ctx.obj
        repo = discover_repo_context(context, Path.cwd())
        worktrees = context.git_ops.list_worktrees(repo.root)
        names = [wt.name for wt in worktrees if wt.name.startswith(incomplete)]
        return names
    except Exception:
        return []

@click.command("switch")
@click.argument("name", metavar="NAME", shell_complete=_complete_worktree_name)
@click.pass_obj
def switch(ctx: WorkstackContext, name: str) -> None:
    """Switch to a worktree."""
    ...
```

See also:

- [../CLAUDE.md](../CLAUDE.md) - CLI development rules

---

## Function Arguments

### Avoiding Default Arguments

**STRONGLY PREFER: No default arguments - force explicit values at call sites:**

```python
# ✅ BEST: No defaults - explicit at every call site
def process_data(data, format):
    """Process data in the specified format.

    Args:
        data: The data to process
        format: Format to use (e.g., "json", "xml"). Use None for auto-detection.
    """
    if format is None:
        format = detect_format(data)
    ...

# All call sites are explicit
process_data(data, format="json")
process_data(data, format="xml")
process_data(data, format=None)  # Explicitly choosing auto-detection
```

**Why avoid defaults:**

- Prevents entire class of errors from implicit behavior
- Makes intent clear at every call site
- No ambiguity about what value is being used
- Easier to refactor - all call sites are explicit

**ACCEPTABLE: Default arguments with explanatory comments:**

Only use default arguments when they significantly improve API ergonomics, and always document why:

```python
# ❌ BAD: Unclear why None is the default
def process_data(data, format=None):
    pass

# ✅ ACCEPTABLE: Comment explains why the default is appropriate
def process_data(data, format=None):
    # format=None defaults to auto-detection based on file extension
    # This is the most common use case (80% of calls) and reduces boilerplate
    if format is None:
        format = detect_format(data)
    ...
```

---

## Context Managers

### Using Context Managers Directly

**DO NOT assign unentered context managers to variables:**

```python
# ❌ BAD: Assigning context manager to variable before entering
pr = self.backend.github_working_dir.pull_request(
    f"CRONJOB UPDATE: {existing_cron_job.thread}",
    body,
    False,
)
with pr:
    # work with pr
    pass

# ✅ GOOD: Use context manager directly in with statement
with self.backend.github_working_dir.pull_request(
    f"CRONJOB UPDATE: {existing_cron_job.thread}",
    body,
    False,
) as pr:
    # work with pr
    pass
```

**Rationale**: Assigning an unentered context manager to a variable can lead to resource leaks if the variable is accidentally used outside the context manager, and makes the code less clear about when resources are acquired and released.

### Exception: Post-Exit Access

When you need to access properties set during `__exit__`:

```python
# ✅ ACCEPTABLE: When you need post-exit access to context manager properties
pr = self.backend.github_working_dir.pull_request(title, body, False)
with pr:
    # do work within context
    pass
# Access properties set during __exit__
return SomeResult(url=pr.pr_url)
```

---

## Resource Management

### Avoiding **del**

**DO NOT use `__del__` for resource cleanup:**

```python
# ❌ BAD: Using __del__ for cleanup
class DatabaseConnection:
    def __init__(self, connection_string):
        self.conn = create_connection(connection_string)

    def __del__(self):
        # This may never be called or called at unpredictable times
        if hasattr(self, 'conn'):
            self.conn.close()
```

Python's garbage collection is not deterministic, making `__del__` unreliable.

### Avoiding Direct Context Manager Protocol

**DO NOT implement context manager protocol directly on objects:**

```python
# ❌ BAD: Context manager protocol on the object itself
class DatabaseConnection:
    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.conn = None

    def __enter__(self):
        self.conn = create_connection(self.connection_string)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
```

This tightly couples resource lifecycle to object lifecycle.

### Preferred: Classmethod Factories

**Use classmethod factories that return context managers:**

```python
# ✅ GOOD: Classmethod factory that returns a context manager
from contextlib import contextmanager

class DatabaseConnection:
    @classmethod
    @contextmanager
    def connect(cls, connection_string):
        """Create and manage a database connection."""
        conn = create_connection(connection_string)
        try:
            yield conn
        finally:
            conn.close()

# Usage
with DatabaseConnection.connect("postgresql://...") as conn:
    # Use conn here
    conn.execute("SELECT * FROM users")
# Connection automatically closed
```

### Alternative: Standalone Factory Functions

```python
# ✅ GOOD: Standalone context manager factory
from contextlib import contextmanager

@contextmanager
def database_connection(connection_string):
    """Create and manage a database connection."""
    conn = create_connection(connection_string)
    try:
        yield conn
    finally:
        conn.close()

# Usage
with database_connection("postgresql://...") as conn:
    conn.execute("SELECT * FROM users")
```

### Rationale

- **Deterministic cleanup**: Context managers guarantee cleanup happens when the `with` block exits
- **Clear resource boundaries**: Resource acquisition and release are explicit and scoped
- **Separation of concerns**: Object lifecycle is separate from resource lifecycle
- **Testing friendly**: Easy to test resource management independently

---

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Core coding standards
- [EXCEPTION_HANDLING.md](EXCEPTION_HANDLING.md) - Complete exception handling guide
- [GUIDE.md](GUIDE.md) - Documentation index
- [../tests/CLAUDE.md](../tests/CLAUDE.md) - Testing patterns and practices
