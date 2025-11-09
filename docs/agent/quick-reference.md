# Quick Reference

One-line rules with one-line examples. No explanations. For details, see patterns.md.

## Exception Handling

```python
if key in dict: value = dict[key]              # ✅ NOT try: dict[key]
if path.exists(): path.resolve()               # ✅ NOT try: path.resolve()
value = dict.get(key, default)                 # ✅ NOT try: dict[key] except: default
```

## Type Annotations

```python
def foo(items: list[str]) -> dict[str, int]    # ✅ NOT List[str], Dict[str, int]
def bar(x: str | None) -> None                 # ✅ NOT Optional[str]
@dataclass(frozen=True) class Config: ...      # ✅ Immutable dataclass
```

## Imports

```python
from workstack.cli.config import load_config   # ✅ NOT from .config import
import click                                   # ✅ NOT import click as c
# Standard library → Third-party → Local      # ✅ Three groups, alphabetical
# Empty __init__.py files                     # ✅ NOT code in __init__.py
```

## Dependency Injection

```python
class MyOps(ABC): @abstractmethod ...          # ✅ NOT class MyOps(Protocol)
@dataclass(frozen=True) class Context: ops: MyOps  # ✅ Inject via dataclass
class FakeMyOps(MyOps): def __init__(self, state) # ✅ In-memory fake
```

## File Operations

```python
Path.home() / ".config" / "app.toml"          # ✅ NOT os.path.join()
content = path.read_text(encoding="utf-8")    # ✅ Always specify encoding
if path.exists(): ...                         # ✅ Check before operations
```

## CLI Development

```python
click.echo("Message")                         # ✅ NOT print("Message")
click.echo("Error", err=True)                 # ✅ Error to stderr
raise SystemExit(1)                           # ✅ Exit on error
subprocess.run(cmd, check=True)               # ✅ Always check=True
```

## Code Style

```python
if not valid: return False                    # ✅ Early return (max 4 indents)
def process(data, format): ...                # ✅ NO defaults without comment
with self.get_context() as ctx: ...           # ✅ Direct in with statement
```

## Resource Management

```python
@contextmanager def connect(): ...            # ✅ NOT __del__ for cleanup
with DatabaseConnection.connect() as conn:    # ✅ Classmethod factory
```

## Common Patterns

| Check       | Do                     | Don't             |
| ----------- | ---------------------- | ----------------- |
| Dictionary  | `if key in d:`         | `try: d[key]`     |
| File exists | `if p.exists():`       | `try: open(p)`    |
| Type check  | `if isinstance(x, T):` | `try: x.method()` |
| Has feature | `if hasattr(x, 'f'):`  | `try: x.f`        |
