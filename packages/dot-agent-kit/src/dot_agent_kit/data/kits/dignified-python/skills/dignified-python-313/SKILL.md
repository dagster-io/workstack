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

Use the routing index in routing-patterns.md (already loaded above) to determine which additional files to load.

**IMPORTANT:** Only load files when you detect specific patterns in the task. Do NOT load all files preemptively.

Pattern detection examples:

- If task mentions "dict", "key", or "KeyError" → Load exception-handling.md
- If task mentions "path", "file", or "directory" → Load path-operations.md
- If task mentions "import" or "circular" → Load imports.md
- If task mentions "ABC" or "interface" → Load dependency-injection.md
- If task mentions "click" or "CLI" → Load cli-patterns.md
- If task mentions "subprocess" → Load subprocess.md
- If task mentions type hints → Load type-annotations.md

## Comprehensive Reference (If Needed)

If unsure which specific file to load, or need full overview:
.claude/docs/dignified-python/core-standards-universal.md

**For code reviews:** See `.claude/docs/code-review/` for code smell patterns and refactoring guidance (not auto-loaded).

## How to Use This Skill

1. **Core essentials** are loaded automatically (LBYL, pathlib, ABC, imports)
2. **Scan your task** for patterns (see routing-patterns.md)
3. **Load relevant files** based on detected patterns
4. **Each file is self-contained** with complete guidance for its domain

**Token efficiency:** Loads ~740 tokens average (70% reduction from previous approach)
