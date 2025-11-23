# Pattern Routing Index

**ALWAYS LOADED**: Use this index to determine which additional documentation to load based on task patterns.

---

## How Pattern Routing Works

When you detect specific keywords or patterns in your task, load the corresponding reference documentation. This ensures you only load what's needed, reducing token usage by ~70%.

---

## Pattern Detection Guide

### Dictionary/Key Operations

**Patterns:** `dict`, `key`, `KeyError`, `.get()`, `mapping`, `in operator`

**Load:** @exception-handling.md

**Why:** Dictionary operations are the #1 place where LBYL vs EAFP matters. This file provides complete guidance on checking membership before access, using `.get()` with defaults, and avoiding KeyError as control flow.

**Usage frequency:** ~80% of Python code

---

### File System Operations

**Patterns:** `path`, `file`, `directory`, `.exists()`, `Path()`, `pathlib`, `.resolve()`, `.is_relative_to()`, `read_text`, `write_text`

**Load:** @path-operations.md

**Why:** Path operations have critical safety requirements (.exists() before .resolve()) and encoding specifications. This file covers all pathlib patterns and common pitfalls.

**Usage frequency:** ~60% of Python code

---

### Properties and Magic Methods

**Patterns:** `@property`, `__len__`, `__bool__`, `__str__`, `__repr__`, `cached_property`, performance

**Reference:** `.claude/docs/code-review/performance-patterns.md` (manual reference, not auto-loaded)

**Why:** Performance anti-patterns for properties and magic methods are valuable during code reviews but add ~2.4k tokens if auto-loaded. Reference manually when needed.

**Usage frequency:** During code review and refactoring

---

### Import Organization

**Patterns:** `import`, `from`, `circular`, `inline`, `TYPE_CHECKING`, `__future__`, relative imports

**Load:** @imports.md

**Why:** Import organization has nuanced rules for when inline imports are acceptable (circular dependencies, TYPE_CHECKING, conditional features). This file provides the decision tree and legitimate patterns.

**Usage frequency:** ~40% of Python code

---

### Dependency Injection and Interfaces

**Patterns:** `ABC`, `abstractmethod`, `Protocol`, `interface`, `dependency injection`, `fake`, `mock`

**Load:** @dependency-injection.md

**Why:** Explains why ABC is preferred over Protocol, shows complete DI patterns with testing fakes, and covers interface design.

**Usage frequency:** ~30% of Python code

---

### CLI Development

**Patterns:** `click`, `@command`, `@option`, `@argument`, `CLI`, `command-line`, `print()` in CLI context

**Load:** @cli-patterns.md

**Why:** CLI code has specific requirements: click.echo() not print(), error boundaries at command level, subprocess usage patterns, and output formatting.

**Usage frequency:** When building CLIs

---

### Subprocess Operations

**Patterns:** `subprocess.run`, `subprocess.Popen`, `shell commands`, `CalledProcessError`, `check=True`

**Load:** @subprocess.md

**Why:** Subprocess operations require check=True, proper error handling, and understanding of text vs binary modes. This file covers all subprocess patterns and integration testing.

**Usage frequency:** ~20% of Python code

---

### Code Review and Refactoring

**Patterns:** Code reviews, refactoring, complexity analysis

**Reference:** `.claude/docs/code-review/code-smells-dagster.md` (manual reference, not auto-loaded)

**Why:** Production-tested code smell patterns are valuable during code reviews but add ~14k tokens if auto-loaded. Reference manually when needed.

**Usage frequency:** During refactoring and code review

---

### Type Annotations (Version-Specific)

**Patterns:** `List[`, `Dict[`, `Optional[`, `Union[`, `from __future__ import annotations`, type hints

**Load:** Version-specific type annotation file based on Python version:

- Python 3.10: @version-specific/310/type-annotations.md
- Python 3.11: @version-specific/311/type-annotations.md
- Python 3.12: @version-specific/312/type-annotations.md
- Python 3.13: @version-specific/313/type-annotations.md

**Why:** Type syntax differs across Python versions. Modern versions (3.10+) use `list[str]` and `str | None` instead of `List[str]` and `Optional[str]`.

**Usage frequency:** ~90% of Python code

---

## Loading Strategy

### Core Knowledge (ALWAYS loaded)

These are loaded automatically with the skill:

- @core-essentials.md (fundamental principles)
- @routing-patterns.md (this file)

### Conditional Loading (Load as needed)

Based on patterns detected in your task:

```
Task mentions dictionaries/keys → Load @exception-handling.md
Task involves file operations → Load @path-operations.md
Task organizes imports → Load @imports.md
Task creates interfaces → Load @dependency-injection.md
Task builds CLI → Load @cli-patterns.md
Task uses subprocess → Load @subprocess.md
Task needs type hints → Load version-specific type-annotations.md
```

### Example Pattern Detection

**Task: "Fix the function that reads config files and handles missing keys"**

Detected patterns:

- "reads config files" → Load @path-operations.md
- "handles missing keys" → Load @exception-handling.md

**Task: "Create a repository interface with fake for testing"**

Detected patterns:

- "interface" → Load @dependency-injection.md
- "fake for testing" → Already covered by dependency-injection.md

**Task: "Add a click command that runs git subprocess"**

Detected patterns:

- "click command" → Load @cli-patterns.md
- "subprocess" → Load @subprocess.md

---

## Token Efficiency

**Without routing:**

- Load all documentation: ~2,500 tokens
- Used in 100% of tasks

**With routing:**

- Load core-essentials + routing: ~500 tokens
- Load 1-2 additional files as needed: ~240 tokens average
- **Total average: ~740 tokens (70% reduction)**

---

## Quick Reference Table

| If task mentions...   | Load this file                           |
| --------------------- | ---------------------------------------- |
| dict, key, KeyError   | @exception-handling.md                   |
| path, file, directory | @path-operations.md                      |
| import, circular      | @imports.md                              |
| ABC, interface        | @dependency-injection.md                 |
| click, CLI            | @cli-patterns.md                         |
| subprocess            | @subprocess.md                           |
| type hints            | @version-specific/\*/type-annotations.md |
| code review, refactor | .claude/docs/code-review/ (manual ref)   |

---

## When in Doubt

If you're unsure which file to load:

1. Start with @core-essentials.md (already loaded)
2. Check this routing index for pattern matches
3. Load the most relevant 1-2 files
4. If still unclear, load @core-standards-universal.md for comprehensive overview

**Remember:** Each reference file is self-contained and provides complete guidance for its domain.
