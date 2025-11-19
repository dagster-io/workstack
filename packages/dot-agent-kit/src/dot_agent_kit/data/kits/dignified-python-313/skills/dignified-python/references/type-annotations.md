# Type Annotations - Python 3.13+ Syntax

## Core Rule

**CRITICAL**: Never use `from __future__ import annotations` - Python 3.13+ doesn't need it.

## Modern Type Syntax

### Basic Types

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

### Collections and Generics

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

## Migration Reference

| Old (Python 3.8-3.9)                 | New (Python 3.13+) |
| ------------------------------------ | ------------------ |
| `List[str]`                          | `list[str]`        |
| `Dict[str, int]`                     | `dict[str, int]`   |
| `Tuple[str, ...]`                    | `tuple[str, ...]`  |
| `Set[int]`                           | `set[int]`         |
| `Optional[str]`                      | `str \| None`      |
| `Union[str, int]`                    | `str \| int`       |
| `from __future__ import annotations` | Not needed         |

## Advanced Patterns

### Callable Types

```python
# ✅ CORRECT: Modern callable syntax
from collections.abc import Callable

Handler = Callable[[str, int], None]
Processor = Callable[..., dict[str, Any]]

# Function taking a callback
def register(callback: Callable[[Event], None]) -> None: ...
```

### Type Variables

```python
from typing import TypeVar

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")

def first(items: list[T]) -> T | None:
    return items[0] if items else None

def merge(d1: dict[K, V], d2: dict[K, V]) -> dict[K, V]:
    return {**d1, **d2}
```

## Key Takeaways

1. **Use built-in types**: `list`, `dict`, `tuple`, `set` directly
2. **Union with |**: Replace `Union[A, B]` with `A | B`
3. **Optional with |**: Replace `Optional[T]` with `T | None`
4. **No future import**: Python 3.13+ has native support
5. **Clean imports**: Minimize imports from `typing` module
