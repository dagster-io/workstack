# Code Review Guidance

This directory contains resources for code reviews.

## Available Resources

- **code-smells-dagster.md** - Production-tested Python code smells from Dagster Labs
  - Parameter design anti-patterns
  - God classes and complexity management
  - Context coupling issues
  - Real production bugs and fixes

- **performance-patterns.md** - Performance expectations for properties and magic methods
  - Property performance (O(1) expectations)
  - Magic method performance (`__len__`, `__bool__`)
  - Real production bugs from Dagster
  - Guidelines for making cost explicit

- **patterns-reference-universal.md** - Common implementation patterns and refactoring guidance
  - File I/O patterns with extensive examples
  - Dataclass patterns and validation
  - Code organization (nesting reduction, helper extraction)
  - Testing patterns (fakes vs mocks)
  - Performance considerations
  - Common gotchas

## When to Reference

Load these files manually during code reviews or when refactoring complex code. These patterns are NOT auto-loaded with dignified-python skills to reduce token overhead.

## Usage

To reference during code review:

```
Read .claude/docs/code-review/code-smells-dagster.md
Read .claude/docs/code-review/performance-patterns.md
Read .claude/docs/code-review/patterns-reference-universal.md
```

Or mention specific patterns you're looking for and reference the relevant sections.
