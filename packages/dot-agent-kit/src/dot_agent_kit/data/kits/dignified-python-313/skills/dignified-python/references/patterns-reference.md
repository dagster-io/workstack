# Common Implementation Patterns

This document contains common patterns for CLI development, file I/O, dataclasses, and code organization. For quick reference, see the main SKILL.md file.

---

## CLI Development with Click

### Basic Patterns

```python
import click
from pathlib import Path

# ✅ CORRECT: Use click.echo() for output
@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def process(path: Path, verbose: bool) -> None:
    """Process the specified file or directory."""
    click.echo(f"Processing: {path}")

    if verbose:
        click.echo("Verbose mode enabled", err=True)

    try:
        result = do_processing(path)
        click.echo(f"✓ Success: {result}")
    except ProcessingError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

# ❌ WRONG: Using print()
def process(path):
    print(f"Processing: {path}")  # Don't use print
```

### Error Handling in CLI

```python
# ✅ CORRECT: Error boundary at CLI level
@click.command()
@click.pass_obj
def create(ctx: Context, name: str) -> None:
    """Create a new resource."""
    try:
        resource = create_resource(ctx, name)
        click.echo(f"✓ Created {resource.name}")
    except ValidationError as e:
        click.echo(f"Validation error: {e}", err=True)
        raise SystemExit(1)
    except subprocess.CalledProcessError as e:
        click.echo(f"Command failed: {e.stderr}", err=True)
        raise SystemExit(1)

# ✅ CORRECT: SystemExit for clean termination
if not valid_input:
    click.echo("Error: Invalid input provided", err=True)
    raise SystemExit(1)  # Clean exit with error code
```

### Output Abstraction Pattern

```python
from workstack.cli.output import user_output, machine_output

# User-facing messages go to stderr
user_output("✓ Operation complete")
user_output(click.style("Error", fg="red"))

# Machine-readable data goes to stdout
machine_output(json.dumps({"status": "success"}))
machine_output(str(activation_path))
```

### Subprocess Management

```python
import subprocess
from pathlib import Path

# ✅ CORRECT: subprocess with check=True
def run_git_command(repo_path: Path, args: list[str]) -> str:
    """Run git command and return output."""
    result = subprocess.run(
        ["git"] + args,
        cwd=repo_path,
        check=True,  # Raises CalledProcessError on failure
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    return result.stdout.strip()

# ✅ CORRECT: Handle specific subprocess errors
try:
    output = run_git_command(repo_path, ["status", "--short"])
except subprocess.CalledProcessError as e:
    # Handle at error boundary
    click.echo(f"Git command failed: {e.stderr}", err=True)
    raise SystemExit(1)
```

---

## File I/O Patterns

### Reading Files

```python
from pathlib import Path
import json
import tomllib

# ✅ CORRECT: Explicit encoding, path validation
def read_config(config_path: Path) -> dict:
    """Read configuration from TOML file."""
    if not config_path.exists():
        return {}

    content = config_path.read_text(encoding="utf-8")
    return tomllib.loads(content)

# ✅ CORRECT: JSON with error handling
def load_json_data(path: Path) -> dict:
    """Load JSON data from file."""
    if not path.exists():
        return {}

    content = path.read_text(encoding="utf-8")
    return json.loads(content)

# ❌ WRONG: No encoding, no validation
def bad_read(path):
    return path.read_text()  # System-dependent encoding
```

### Writing Files

```python
# ✅ CORRECT: Atomic writes with temporary file
def write_config_atomic(config_path: Path, data: dict) -> None:
    """Write config atomically using temporary file."""
    import tempfile
    import os

    # Write to temporary file first
    fd, temp_path = tempfile.mkstemp(
        dir=config_path.parent,
        prefix=".tmp-",
        suffix=config_path.suffix
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # Atomic rename
        Path(temp_path).replace(config_path)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise

# ✅ CORRECT: Simple write with encoding
def write_data(path: Path, content: str) -> None:
    """Write content to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
```

### Directory Operations

```python
# ✅ CORRECT: Safe directory creation
def ensure_directory(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)

# ✅ CORRECT: Directory traversal
def find_config_files(root: Path) -> list[Path]:
    """Find all config files recursively."""
    if not root.exists():
        return []

    return list(root.rglob("*.toml"))

# ✅ CORRECT: Safe cleanup
def cleanup_temp_dir(temp_dir: Path) -> None:
    """Remove temporary directory if it exists."""
    if temp_dir.exists() and temp_dir.is_dir():
        import shutil
        shutil.rmtree(temp_dir)
```

---

## Dataclasses and Immutability

### Frozen Dataclasses

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass(frozen=True)
class Config:
    """Immutable configuration."""
    root_path: Path
    use_cache: bool = True
    max_workers: int = 4
    tags: tuple[str, ...] = field(default_factory=tuple)

    def with_root(self, new_root: Path) -> "Config":
        """Create new config with different root."""
        return Config(
            root_path=new_root,
            use_cache=self.use_cache,
            max_workers=self.max_workers,
            tags=self.tags
        )

# Usage
config = Config(root_path=Path("/app"))
# config.root_path = Path("/other")  # Error! Frozen
new_config = config.with_root(Path("/other"))  # Create new instance
```

### Dataclass Validation

```python
@dataclass(frozen=True)
class Repository:
    """Repository with validation."""
    name: str
    url: str
    branch: str = "main"

    def __post_init__(self):
        """Validate after initialization."""
        if not self.name:
            raise ValueError("Repository name cannot be empty")

        if not self.url.startswith(("http://", "https://", "git@")):
            raise ValueError(f"Invalid repository URL: {self.url}")

        if "/" in self.branch or "\\" in self.branch:
            raise ValueError(f"Invalid branch name: {self.branch}")
```

### Cached Properties on Immutable Classes

```python
from functools import cached_property

@dataclass(frozen=True)
class DataSet:
    """Immutable dataset with cached computations."""
    values: tuple[int, ...]

    @cached_property
    def mean(self) -> float:
        """Compute mean (cached)."""
        return sum(self.values) / len(self.values)

    @cached_property
    def sorted_values(self) -> tuple[int, ...]:
        """Get sorted values (cached)."""
        return tuple(sorted(self.values))
```

---

## Code Style and Organization

### Reducing Nesting with Early Returns

```python
# ✅ CORRECT: Early returns (max 2 levels)
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

# ❌ WRONG: Excessive nesting (5 levels)
def process_data(data):
    if data:
        if validate(data):
            result = transform(data)
            if result:
                if result.is_valid:
                    if save(result):  # 5 levels - TOO DEEP
                        return True
    return False
```

### Extracting Helper Functions

```python
# ✅ CORRECT: Helper functions reduce complexity
def process_items(items: list[Item]) -> list[Result]:
    """Process list of items."""
    validated_items = _validate_items(items)
    transformed = _transform_batch(validated_items)
    return _filter_valid_results(transformed)

def _validate_items(items: list[Item]) -> list[Item]:
    """Validate and filter items."""
    return [item for item in items if _is_valid_item(item)]

def _is_valid_item(item: Item) -> bool:
    """Check if single item is valid."""
    return (
        item.value > 0
        and item.status == "active"
        and item.category in ALLOWED_CATEGORIES
    )

def _transform_batch(items: list[Item]) -> list[Result]:
    """Transform validated items to results."""
    return [_transform_item(item) for item in items]

def _filter_valid_results(results: list[Result]) -> list[Result]:
    """Keep only valid results."""
    return [r for r in results if r.is_valid]
```

### Context Managers

```python
from contextlib import contextmanager
import tempfile
from pathlib import Path

# ✅ CORRECT: Custom context manager
@contextmanager
def temporary_directory(prefix: str = "tmp"):
    """Create and cleanup temporary directory."""
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield temp_dir
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

# Usage
with temporary_directory(prefix="test-") as temp_dir:
    temp_file = temp_dir / "data.txt"
    temp_file.write_text("test data", encoding="utf-8")
    # temp_dir cleaned up automatically

# ✅ CORRECT: Direct use in with statement
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# ❌ WRONG: Assigning before using
f = open(path, "r", encoding="utf-8")
with f:
    content = f.read()
```

### Global State Avoidance

```python
# ❌ WRONG: Global mutable state
_cache = {}

def get_value(key):
    global _cache
    if key not in _cache:
        _cache[key] = expensive_computation(key)
    return _cache[key]

# ✅ CORRECT: Class encapsulation
class ValueCache:
    """Cache for expensive computations."""
    def __init__(self):
        self._cache = {}

    def get(self, key):
        if key not in self._cache:
            self._cache[key] = expensive_computation(key)
        return self._cache[key]

# ✅ CORRECT: Dependency injection
def process_with_cache(data, cache: ValueCache):
    """Process data using provided cache."""
    return cache.get(data.key)
```

---

## Testing Patterns

### Using Fakes Over Mocks

```python
from abc import ABC, abstractmethod

# Define interface
class EmailService(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None:
        """Send email."""
        ...

# Production implementation
class SMTPEmailService(EmailService):
    def send(self, to: str, subject: str, body: str) -> None:
        # Real SMTP implementation
        pass

# Test fake
class FakeEmailService(EmailService):
    """Fake for testing."""
    def __init__(self):
        self.sent_emails = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent_emails.append({
            "to": to,
            "subject": subject,
            "body": body
        })

# In tests
def test_notification():
    email_service = FakeEmailService()
    notifier = Notifier(email_service)

    notifier.notify_user("user@example.com", "Alert")

    assert len(email_service.sent_emails) == 1
    assert email_service.sent_emails[0]["subject"] == "Alert"
```

### Test Isolation with Fixtures

```python
import pytest
from pathlib import Path

@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Create temporary config file."""
    config_path = tmp_path / "config.toml"
    config_path.write_text("""
    [app]
    name = "test"
    debug = true
    """, encoding="utf-8")
    return config_path

def test_config_loading(temp_config: Path):
    """Test config loads correctly."""
    config = load_config(temp_config)
    assert config["app"]["name"] == "test"
    assert config["app"]["debug"] is True
```

---

## Performance Considerations

### String Building

```python
# ❌ WRONG: String concatenation in loop
result = ""
for item in items:
    result += f"{item}\n"  # O(n²) complexity

# ✅ CORRECT: Join list
lines = [str(item) for item in items]
result = "\n".join(lines)  # O(n) complexity

# ✅ CORRECT: StringIO for complex building
from io import StringIO

buffer = StringIO()
for item in items:
    buffer.write(f"{item}\n")
result = buffer.getvalue()
```

### Collection Operations

```python
# ✅ CORRECT: Set for membership testing
valid_ids = {1, 2, 3, 4, 5}  # O(1) lookup
if user_id in valid_ids:
    process_user(user_id)

# ❌ WRONG: List for membership testing
valid_ids = [1, 2, 3, 4, 5]  # O(n) lookup
if user_id in valid_ids:
    process_user(user_id)

# ✅ CORRECT: Generator for memory efficiency
def process_large_file(path: Path):
    """Process file line by line without loading all."""
    with open(path, encoding="utf-8") as f:
        for line in f:  # Generator, not list
            yield process_line(line.strip())
```

---

## Common Gotchas

### Mutable Default Arguments

```python
# ❌ WRONG: Mutable default
def add_item(item, items=[]):  # Shared across calls!
    items.append(item)
    return items

# ✅ CORRECT: None default with check
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items

# ✅ BETTER: Immutable approach
def add_item(item, items=None):
    """Return new list with item added."""
    existing = items or []
    return [*existing, item]
```

### Boolean Comparisons

```python
# ❌ WRONG: Comparing to True/False
if value == True:
    do_something()

if result == None:
    handle_none()

# ✅ CORRECT: Direct boolean test
if value:
    do_something()

if result is None:
    handle_none()

# ✅ CORRECT: Explicit type checking when needed
if value is True:  # Explicitly want True, not truthy
    do_something()
```

---

## References

- Click documentation: https://click.palletsprojects.com/
- Pathlib documentation: https://docs.python.org/3.13/library/pathlib.html
- Dataclasses: https://docs.python.org/3.13/library/dataclasses.html
- Context managers: https://docs.python.org/3.13/library/contextlib.html
