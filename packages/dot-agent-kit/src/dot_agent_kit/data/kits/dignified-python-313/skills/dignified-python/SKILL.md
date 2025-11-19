---
name: dignified-python-313
description: This skill should be used when editing Python code in the erk codebase. Use when writing, reviewing, or refactoring Python to ensure adherence to LBYL exception handling patterns, Python 3.13+ type syntax (list[str], str | None), pathlib operations, ABC-based interfaces, absolute imports, and explicit error boundaries at CLI level. Also provides production-tested code smell patterns from Dagster Labs for API design, parameter complexity, and code organization. Essential for maintaining erk's dignified Python standards.
---

# Dignified Python - Python 3.13+ Coding Standards

Write explicit, predictable code that fails fast at proper boundaries.

## Core Philosophy

**LBYL (Look Before You Leap) over EAFP**

- Check conditions proactively
- Let exceptions bubble to boundaries
- Never use exceptions for control flow

## Pattern Detection & Reference Loading

When you detect these patterns in code, load the corresponding reference file:

| Pattern Detected                                                       | Load Reference                              |
| ---------------------------------------------------------------------- | ------------------------------------------- |
| `try:`, `except:`, exception handling                                  | → Load `references/exception-handling.md`   |
| Type hints: `List[`, `Dict[`, `Optional[`, `Union[`, `from __future__` | → Load `references/type-annotations.md`     |
| `path.resolve()`, `path.is_relative_to()`, `Path(`, pathlib operations | → Load `references/path-operations.md`      |
| `Protocol`, `ABC`, `abstractmethod`, interfaces                        | → Load `references/dependency-injection.md` |
| Import statements, `from .`, relative imports                          | → Load `references/imports.md`              |
| `click.`, `@click.`, CLI commands, `print()` in CLI                    | → Load `references/cli-patterns.md`         |
| `subprocess.run`, `subprocess.Popen`, shell commands                   | → Load `references/subprocess.md`           |
| 10+ parameters, 50+ methods, context objects, code complexity          | → Load `references/code-smells-dagster.md`  |
| Need implementation examples                                           | → Load `references/patterns-reference.md`   |

## Quick Checklist

Before writing Python code, scan for patterns above and load relevant references.

Key rules to remember:

- **Never** use `from __future__ import annotations` (Python 3.13+)
- **Always** use modern type syntax: `list[str]`, `str | None`
- **Always** check `.exists()` before path operations
- **Always** use absolute imports at module level
- **Always** use `click.echo()` in CLI code, not `print()`
- **Always** add `check=True` to `subprocess.run()`

## Loading Instructions

To load a reference file when a pattern is detected:

1. Use the Read tool to load the specific reference file
2. Apply the guidance from that reference to your code
3. Each reference is self-contained with complete guidance

Example: If you see `try:` in the code, immediately load `references/exception-handling.md` for complete LBYL guidance.

---

_Token-efficient skill: Loads only what you need, when you need it._
