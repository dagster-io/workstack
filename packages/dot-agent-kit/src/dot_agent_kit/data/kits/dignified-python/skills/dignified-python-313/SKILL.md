---
name: dignified-python-313
description: This skill should be used when editing Python code in the erk codebase. Use when writing, reviewing, or refactoring Python to ensure adherence to LBYL exception handling patterns, modern type syntax (list[str], str | None), pathlib operations, ABC-based interfaces, absolute imports, and explicit error boundaries at CLI level. Also provides production-tested code smell patterns from Dagster Labs for API design, parameter complexity, and code organization. Essential for maintaining erk's dignified Python standards.
---

# Dignified Python - Python 3.13 Coding Standards

## Core Knowledge (ALWAYS Loaded)

@.claude/docs/dignified-python/core-essentials.md
@.claude/docs/dignified-python/routing-patterns.md

## Version-Specific Checklist

@.claude/docs/dignified-python/version-specific/313/checklist.md

## Conditional Loading (Load Based on Task Patterns)

Use the routing index in @routing-patterns.md to determine which additional files to load:

- **Dictionary/key operations** → @.claude/docs/dignified-python/exception-handling.md
- **File system operations** → @.claude/docs/dignified-python/path-operations.md
- **Properties/magic methods** → @.claude/docs/dignified-python/performance-patterns.md
- **Import organization** → @.claude/docs/dignified-python/imports.md
- **Dependency injection** → @.claude/docs/dignified-python/dependency-injection.md
- **CLI development** → @.claude/docs/dignified-python/cli-patterns.md
- **Subprocess operations** → @.claude/docs/dignified-python/subprocess.md
- **Type annotations** → @.claude/docs/dignified-python/version-specific/313/type-annotations.md
- **Code smells/refactoring** → @.claude/docs/dignified-python/code-smells-dagster.md

## Comprehensive Reference (If Needed)

If unsure which specific file to load, or need full overview:
@.claude/docs/dignified-python/core-standards-universal.md

## How to Use This Skill

1. **Core essentials** are loaded automatically (LBYL, pathlib, ABC, imports)
2. **Scan your task** for patterns (see routing-patterns.md)
3. **Load relevant files** based on detected patterns
4. **Each file is self-contained** with complete guidance for its domain

**Token efficiency:** Loads ~740 tokens average (70% reduction from previous approach)
