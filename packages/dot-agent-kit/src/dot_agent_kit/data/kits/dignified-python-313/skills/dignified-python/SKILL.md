---
name: dignified-python
description: This skill should be used when editing Python code in the workstack codebase. Use when writing, reviewing, or refactoring Python to ensure adherence to LBYL exception handling patterns, Python 3.13+ type syntax (list[str], str | None), pathlib operations, ABC-based interfaces, absolute imports, and explicit error boundaries at CLI level. Essential for maintaining workstack's dignified Python standards.
---

# Dignified Python - Python 3.13+ Coding Standards

> **See [UNIVERSAL.md](./UNIVERSAL.md) for standards that apply to ALL Python versions.**

This file contains Python 3.13+ **specific** standards. For universal patterns (exception handling, path operations, CLI development, etc.), refer to UNIVERSAL.md.

---

## Python 3.13+ SPECIFIC RULES

### Type Annotations - Python 3.13+ Syntax Only 🔴

**FORBIDDEN**: `from __future__ import annotations`

```python
# ✅ CORRECT: Modern Python 3.13+ syntax
def process_items(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

def find_user(user_id: int) -> User | None:
    ...

# ❌ WRONG: Legacy syntax
from typing import List, Dict, Optional
def process_items(items: List[str]) -> Dict[str, int]:
    ...
```

**Key differences from older Python:**

- Use `list[str]` instead of `List[str]`
- Use `dict[str, Any]` instead of `Dict[str, Any]`
- Use `str | None` instead of `Optional[str]`
- Use `X | Y` instead of `Union[X, Y]`
- **NEVER** use `from __future__ import annotations` (Python 3.13+ doesn't need it)

### Checklist Before Writing Code

Before using type hints:

- [ ] Am I using `list[...]`, `dict[...]`, `str | None`?
- [ ] Have I removed `from __future__ import annotations`?
- [ ] Have I removed `List`, `Dict`, `Optional`, `Union` imports?

---

## QUICK REFERENCE

For Python 3.13+ projects, follow these rules:

1. **Type annotations**: Use `list[str]`, `dict[str, Any]`, `str | None`
2. **No future imports**: NEVER use `from __future__ import annotations`
3. **All other standards**: See [UNIVERSAL.md](./UNIVERSAL.md)

---

## REFERENCES

- [UNIVERSAL.md](./UNIVERSAL.md) - Standards for ALL Python versions
- Python 3.13 documentation: https://docs.python.org/3.13/
