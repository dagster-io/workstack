# Workstack Coding Standards

> **Note**: This is unreleased, completely private software. We can break backwards
> compatibility completely at will based on preferences of the engineer developing
> the product.

<!-- AGENT NOTICE: This file is loaded automatically. Read FULLY before writing code. -->
<!-- Priority sections: BEFORE WRITING CODE (line 6), TOP 5 CRITICAL RULES (line 35) -->

## ⚠️ BEFORE WRITING CODE (AI Assistant Checklist)

**This codebase has strong opinions. Check these patterns BEFORE coding:**

| If you're about to write...                 | STOP! Check this instead                                                      |
| ------------------------------------------- | ----------------------------------------------------------------------------- |
| `try:` or `except:`                         | → [Exception Handling](#exception-handling) - Default: let exceptions bubble  |
| `from __future__ import annotations`        | → **FORBIDDEN** - Python 3.13+ doesn't need it                                |
| `List[...]`, `Dict[...]`, `Union[...]`      | → Use `list[...]`, `dict[...]`, `X \| Y`                                      |
| `typing.Protocol`                           | → Use `abc.ABC` instead                                                       |
| `dict[key]` without checking                | → Use `if key in dict:` or `.get()`                                           |
| `path.resolve()` or `path.is_relative_to()` | → Check `path.exists()` first                                                 |
| Function with default argument              | → Make explicit at call sites                                                 |
| `from .module import`                       | → Use absolute imports only                                                   |
| `print(...)` in CLI code                    | → Use `click.echo()`                                                          |
| `subprocess.run(...)`                       | → Add `check=True`                                                            |
| `make ...` or user says "make"              | → Use makefile-runner agent (Task tool) instead of Bash                       |
| `pyright` or `uv run pyright`               | → Use pyright-runner agent (Task tool); target paths directly, never `cd`     |
| `pytest` or `uv run pytest`                 | → Use pytest-runner agent (Task tool) for running tests                       |
| `ruff` or `uv run ruff`                     | → Use ruff-runner agent (Task tool) for linting/formatting                    |
| Prettier formatting issues                  | → Use `make prettier` (via makefile-runner agent)                             |
| Summarizing code changes in a branch        | → Use git-diff-summarizer agent (Task tool) for branch analysis               |
| Updating commit message with code changes   | → Use git-diff-summarizer agent (Task tool) to analyze first                  |
| `gt ...` or user says "gt" or "graphite"    | → Use gt-runner agent (Task tool) for execution, graphite skill for knowledge |
| 4+ levels of indentation                    | → Extract helper functions                                                    |
| Code in `__init__.py`                       | → Keep empty or docstring-only (except package entry points)                  |
| Tests for speculative features              | → **FORBIDDEN** - Only test actively implemented code (TDD is fine)           |

## 📚 Quick Reference

| Need help with...     | See documentation                                                      |
| --------------------- | ---------------------------------------------------------------------- |
| **Code examples**     | [.agent/docs/PATTERNS.md](.agent/docs/PATTERNS.md)                     |
| **Exception details** | [.agent/docs/EXCEPTION_HANDLING.md](.agent/docs/EXCEPTION_HANDLING.md) |
| **Quick lookup**      | [.agent/docs/QUICK_REFERENCE.md](.agent/docs/QUICK_REFERENCE.md)       |
| **Writing tests**     | [.agent/docs/TESTING.md](.agent/docs/TESTING.md)                       |

---

## 🔴 TOP 5 CRITICAL RULES (Most Violated)

### 1. Exception Handling 🔴 MUST

**NEVER use try/except for control flow. Let exceptions bubble up.**

```python
# ❌ WRONG
try:
    value = mapping[key]
except KeyError:
    value = default

# ✅ CORRECT
if key in mapping:
    value = mapping[key]
else:
    value = default
```

**Full guide**: [.agent/docs/EXCEPTION_HANDLING.md](.agent/docs/EXCEPTION_HANDLING.md)

### 2. Type Annotations 🔴 MUST

**Use Python 3.13+ syntax. NO `from __future__ import annotations`**

```python
# ✅ CORRECT: list[str], dict[str, Any], str | None
# ❌ WRONG: List[str], Dict[str, Any], Optional[str]
```

### 3. Path Operations 🔴 MUST

**Check .exists() BEFORE .resolve() or .is_relative_to()**

```python
# ✅ CORRECT
if path.exists():
    resolved = path.resolve()
```

### 4. Dependency Injection 🔴 MUST

**Use ABC for interfaces, never Protocol**

```python
from abc import ABC, abstractmethod

class MyOps(ABC):  # ✅ Not Protocol
    @abstractmethod
    def operation(self) -> None: ...
```

### 5. Imports 🟡 SHOULD

**Top-level absolute imports only**

```python
# ✅ from workstack.config import load_config
# ❌ from .config import load_config
```

---

## Core Standards

### Python Requirements

- **Version**: Python 3.13+ only
- **Type checking**: `uv run pyright` (must pass)
- **Formatting**: `uv run ruff format` (100 char lines)

### Project Structure

- Source: `src/workstack/`
- Tests: `tests/`
- Config: `pyproject.toml`

### Naming Conventions

- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- CLI commands: `kebab-case`
- Brand names: `GitHub` (not Github)

### Design Principles

1. **LBYL over EAFP**: Check conditions before acting
2. **Immutability**: Use frozen dataclasses
3. **Explicit > Implicit**: No unexplained defaults
4. **Fail Fast**: Let exceptions bubble to boundaries
5. **Testability**: In-memory fakes, no I/O in unit tests

### Exception Handling

**This codebase uses LBYL (Look Before You Leap), NOT EAFP.**

🔴 **MUST**: Never use try/except for control flow
🔴 **MUST**: Let exceptions bubble to error boundaries (CLI level)
🟡 **SHOULD**: Check conditions proactively with if statements
🟢 **MAY**: Catch at error boundaries for user-friendly messages

**Acceptable exception uses:**

1. CLI error boundaries for user messages
2. Third-party APIs that force exception handling
3. Adding context before re-raising

**See**: [.agent/docs/EXCEPTION_HANDLING.md](.agent/docs/EXCEPTION_HANDLING.md)

### File Operations

- Always use `pathlib.Path` (never `os.path`)
- Always specify `encoding="utf-8"`
- Check `.exists()` before path operations

### CLI Development (Click)

- Use `click.echo()` for output (not `print()`)
- Use `click.echo(..., err=True)` for errors
- Exit with `raise SystemExit(1)` for CLI errors
- Use `subprocess.run(..., check=True)`

### Code Style

- **Max 4 levels of indentation** - extract helper functions
- Use early returns and guard clauses
- No default arguments without explanatory comments
- Use context managers directly in `with` statements

### Testing

🔴 **MUST**: Only write tests for code being actively implemented
🔴 **FORBIDDEN**: Writing tests for speculative or "maybe later" features

**TDD is explicitly allowed and encouraged:**

- Write test → implement feature → refactor is a valid workflow
- The key is that you're actively working on the feature NOW

**What's forbidden:**

- Test stubs for features planned for future sprints/milestones
- "Let's add placeholder tests for ideas we're considering"
- Tests for hypothetical features not currently being built

**Rationale:**

- Speculative tests create maintenance burden without validation value
- Planned features often change significantly before implementation
- Test code should validate actual behavior, not wishful thinking

```python
# ❌ WRONG - Speculative test for future feature
# def test_feature_we_might_add_next_month():
#     """Placeholder for feature we're considering."""
#     pass

# ✅ CORRECT - TDD for feature being implemented RIGHT NOW
def test_new_feature_im_building_today():
    """Test for feature I'm about to implement."""
    result = feature_function()  # Will implement after this test
    assert result == expected_value
```

**See**: [.agent/docs/TESTING.md](.agent/docs/TESTING.md) for comprehensive testing guidance.

### Planning and Documentation

**NEVER include time-based estimates in planning documents or implementation plans.**

🔴 **FORBIDDEN**: Time estimates (hours, days, weeks)
🔴 **FORBIDDEN**: Velocity predictions or completion dates
🔴 **FORBIDDEN**: Effort quantification

Time-based estimates have no basis in reality for AI-assisted development and should be omitted entirely.

**What to include instead:**

- Implementation sequence (what order to do things)
- Dependencies between tasks (what must happen first)
- Success criteria (how to know when done)
- Risk mitigation strategies

```markdown
# ❌ WRONG

## Estimated Effort

- Phase 1: 12-16 hours
- Phase 2: 8-10 hours
  Total: 36-46 hours (approximately 1 week)

# ✅ CORRECT

## Implementation Sequence

### Phase 1: Foundation (do this first)

1. Create abstraction X
2. Refactor component Y
   [Clear ordering without time claims]
```

---

## Related Documentation

- [.agent/AGENTIC_PROGRAMMING.md](.agent/AGENTIC_PROGRAMMING.md) - Agentic programming patterns and best practices
- [.agent/docs/PATTERNS.md](.agent/docs/PATTERNS.md) - Code examples
- [.agent/docs/EXCEPTION_HANDLING.md](.agent/docs/EXCEPTION_HANDLING.md) - Exception guide
- [.agent/docs/QUICK_REFERENCE.md](.agent/docs/QUICK_REFERENCE.md) - Quick lookup
- [tests/CLAUDE.md](tests/CLAUDE.md) - Testing patterns
- [README.md](README.md) - Project overview

## Skills and Agents

### Graphite Workflow

**For understanding gt concepts:** Use `graphite` skill (Skill tool)

- Mental model, terminology, workflow patterns
- Command reference and examples
- When to use which commands

**For executing gt commands:** Use `gt-runner` agent (Task tool)

- Cost-optimized execution with Haiku model
- Parses command output automatically
- Returns structured results

**Pattern:** Load skill first for understanding, then use agent for execution.

### Other Tools

- **GitHub (gh)**: Use `gh` skill for GitHub CLI operations
- **Workstack**: Use `workstack` skill for worktree management
