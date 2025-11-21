# Type Annotations - Universal Philosophy

This document contains the universal philosophy for type annotations in dignified Python code, applicable across all Python versions.

## Why Types Matter

**Code Clarity:**

- Types serve as inline documentation
- Make function contracts explicit
- Reduce cognitive load when reading code
- Help understand data flow without tracing through implementation

**IDE Support:**

- Enable autocomplete and intelligent suggestions
- Catch typos and attribute errors before runtime
- Support refactoring tools (rename, move, extract)
- Provide jump-to-definition for typed objects

**Bug Prevention:**

- Catch type mismatches during static analysis
- Prevent None-related errors with explicit optional types
- Document expected input/output without running code
- Enable early detection of API contract violations

## Consistency Rules

**All public APIs:**

- 🔴 MUST: Type all function parameters (except `self` and `cls`)
- 🔴 MUST: Type all function return values
- 🔴 MUST: Type all class attributes
- 🟡 SHOULD: Type module-level constants

**Internal code:**

- 🟡 SHOULD: Type function signatures where helpful for clarity
- 🟢 MAY: Type complex local variables where type isn't obvious
- 🟢 MAY: Omit types for obvious cases (e.g., `count = 0`)

## General Best Practices

**Prefer specificity:**

```python
# ✅ GOOD - Specific
def get_config() -> dict[str, str | int]:
    ...

# ❌ WRONG - Too vague
def get_config() -> dict:
    ...
```

**Use Union sparingly:**

```python
# ✅ GOOD - Union only when necessary
def process(value: str | int) -> str:
    ...

# ❌ WRONG - Too permissive
def process(value: str | int | list | dict) -> str | None | list:
    ...
```

**Be explicit with None:**

```python
# ✅ GOOD - Explicit optional
def find_user(id: str) -> User | None:
    ...

# ❌ WRONG - Implicit None return
def find_user(id: str) -> User:
    return None  # Type checker error!
```

**Avoid Any when possible:**

```python
# ✅ GOOD - Specific type
def serialize(obj: User | Config) -> str:
    ...

# ❌ WRONG - Defeats purpose of types
from typing import Any
def serialize(obj: Any) -> str:
    ...
```

## When to Use Types

**Always type:**

- Public function signatures (parameters + return)
- Class attributes (including private ones)
- Function parameters that cross module boundaries
- Return types when not immediately obvious

**Type when helpful:**

- Complex data structures (nested dicts, lists)
- Variables with non-obvious types from function calls
- Loop variables when type isn't clear from iterable

**Can skip:**

- Simple local variables where type is obvious
- Lambda parameters in short inline lambdas
- Temporary variables in short functions

## Type Checking

**Run type checker regularly:**

```bash
# Example with pyright
uv run pyright

# All type errors should be addressed
# No "# type: ignore" without clear justification
```

**Type checker configuration:**

- Use strict mode where feasible
- Enable all safety checks
- Treat type errors as build failures in CI

## Progressive Typing

**For existing codebases:**

- Type new code fully from the start
- Add types to modified functions/classes
- Don't require retroactive typing of untouched code
- Use type: ignore sparingly with clear comments

**For new projects:**

- Type everything from day one
- Establish typing as a standard practice
- Make type checking part of CI pipeline
- No untyped code should pass review

## Common Patterns

**Container types:**

```python
# Lists
names: list[str] = []
pairs: list[tuple[str, int]] = []

# Dicts
mapping: dict[str, int] = {}
config: dict[str, str | int | bool] = {}

# Sets
unique_ids: set[str] = set()
```

**Optional values:**

```python
# Use X | None for optional
def get_user(id: str) -> User | None:
    if id in users:
        return users[id]
    return None
```

**Callable types:**

```python
from collections.abc import Callable

# Function that takes int, returns str
processor: Callable[[int], str] = str

# Function with no args, returns None
callback: Callable[[], None] = lambda: None
```

**Protocol for structural typing:**

```python
from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> None: ...

# Any object with draw() method matches
def render(obj: Drawable) -> None:
    obj.draw()
```

Note: While Protocol is shown here for completeness, dignified-python style prefers ABC for interfaces. Use Protocol only when structural typing is specifically needed.

## References

Version-specific type annotation features and syntax differences are covered in separate version-specific files. This base document focuses on universal philosophy and practices applicable across all Python versions.
