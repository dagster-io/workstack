# Core Python Standards - Universal Reference

This document contains foundational Python standards that apply across Python 3.10, 3.11, 3.12, and 3.13.

For detailed guidance, see the specialized reference files:

- Exception handling → @exception-handling.md
- Path operations → @path-operations.md
- Dependency injection → @dependency-injection.md
- Import organization → @imports.md
- CLI patterns → @cli-patterns.md
- Subprocess usage → @subprocess.md

For version-specific type annotation guidance, see the type-annotations files in the type-annotations/ directory.

---

## Quick Reference

### Exception Handling (LBYL)

**Always check conditions proactively, never use exceptions for control flow.**

```python
# ✅ CORRECT: Check first
if key in mapping:
    value = mapping[key]

# ❌ WRONG: Exception as control flow
try:
    value = mapping[key]
except KeyError:
    pass
```

**See @exception-handling.md for complete guidance.**

### Path Operations

**Always check `.exists()` before `.resolve()` or `.is_relative_to()`**

```python
# ✅ CORRECT
if path.exists():
    resolved = path.resolve()

# ❌ WRONG: Will raise OSError if path doesn't exist
resolved = path.resolve()
```

**See @path-operations.md for complete guidance.**

### Dependency Injection

**Use ABC for interfaces, never Protocol**

```python
# ✅ CORRECT
from abc import ABC, abstractmethod

class Repository(ABC):
    @abstractmethod
    def save(self, entity: Entity) -> None:
        ...
```

**See @dependency-injection.md for complete guidance.**

### Imports

**Module-level and absolute imports only**

```python
# ✅ CORRECT: Module-level, absolute
from erk.config import load_config

# ❌ WRONG: Relative import
from .config import load_config

# ❌ WRONG: Inline without justification
def my_func():
    import json  # Move to module level
```

**See @imports.md for legitimate inline import exceptions.**

### Performance

**Properties and magic methods must be O(1)**

```python
# ❌ WRONG: Property doing I/O
@property
def size(self) -> int:
    return self._fetch_from_db()

# ✅ CORRECT: Explicit method name
def fetch_size_from_db(self) -> int:
    return self._fetch_from_db()
```

**For performance guidance:** See `.claude/docs/code-review/performance-patterns.md` for complete guidance (manual reference, not auto-loaded).

---

## Anti-Patterns

### Exception Swallowing

```python
# ❌ NEVER swallow exceptions silently
try:
    risky_operation()
except:
    pass

# ✅ Let exceptions bubble up (default)
risky_operation()
```

### Silent Fallback Behavior

**NEVER implement silent fallback when primary approach fails**

```python
# ❌ WRONG: Silent fallback masks failure
def process_text(text: str) -> dict[str, Any]:
    try:
        return llm_client.process(text)
    except Exception:
        return regex_parse_fallback(text)

# ✅ CORRECT: Let error bubble to boundary
def process_text(text: str) -> dict[str, Any]:
    return llm_client.process(text)
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

### Code in `__init__.py` and `__all__` Exports

**Core Principle:** One canonical location for every import.

```python
# ❌ WRONG: __all__ exports create duplicate import paths
# myapp/__init__.py
from myapp.core import Process
__all__ = ["Process"]

# Now Process can be imported two ways - breaks grepability

# ✅ CORRECT: Empty __init__.py, import directly
# from myapp.core import Process
```

**Why prohibited:**

1. Breaks grepability - hard to find all usages
2. Confuses static analysis tools
3. Impairs refactoring safety
4. Violates explicit > implicit

### Speculative Tests

```python
# ❌ FORBIDDEN: Tests for future features
# def test_feature_we_might_add():
#     pass

# ✅ CORRECT: TDD for current implementation
def test_feature_being_built_now():
    result = new_feature()
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
