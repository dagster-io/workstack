# Workstack Coding Standards

> **Note**: This is unreleased, completely private software. We can break backwards
> compatibility completely at will based on preferences of the engineer developing
> the product.

<!-- AGENT NOTICE: This file is loaded automatically. Read FULLY before writing code. -->
<!-- Priority sections: BEFORE WRITING CODE (line 10), TOP 5 CRITICAL RULES (line 114), GRAPHITE STACK TERMINOLOGY (line 178) -->

## ⚠️ BEFORE WRITING CODE (AI Assistant Checklist)

**This codebase has strong opinions. Check these patterns BEFORE coding:**

**CRITICAL: NEVER search, read, or access `/Users/schrockn/.claude` directory**

| If you're about to write...                 | STOP! Check this instead                                                                    |
| ------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `try:` or `except:`                         | → [Exception Handling](#exception-handling) - Default: let exceptions bubble                |
| `from __future__ import annotations`        | → **FORBIDDEN** - Python 3.13+ doesn't need it                                              |
| `List[...]`, `Dict[...]`, `Union[...]`      | → Use `list[...]`, `dict[...]`, `X \| Y`                                                    |
| `typing.Protocol`                           | → Use `abc.ABC` instead                                                                     |
| `dict[key]` without checking                | → Use `if key in dict:` or `.get()`                                                         |
| `path.resolve()` or `path.is_relative_to()` | → Check `path.exists()` first                                                               |
| Function with default argument              | → Make explicit at call sites                                                               |
| `from .module import`                       | → Use absolute imports only                                                                 |
| `print(...)` in CLI code                    | → Use `click.echo()`                                                                        |
| `subprocess.run(...)`                       | → Add `check=True`                                                                          |
| `make ...` or user says "make"              | → Use runner agent (Task tool) instead of Bash; loads devrun/make skill                     |
| `pyright` or `uv run pyright`               | → Use runner agent (Task tool); target paths directly, never `cd`                           |
| `pytest` or `uv run pytest`                 | → Use runner agent (Task tool) for running tests                                            |
| `ruff` or `uv run ruff`                     | → Use runner agent (Task tool) for linting/formatting                                       |
| Prettier formatting issues                  | → Use `make prettier` (via runner agent with Task tool)                                     |
| Submitting a branch with Graphite           | → Use /gt:submit-branch command (delegates to gt-branch-submitter agent)                    |
| `gt ...` or user says "gt" or "graphite"    | → Use runner agent (Task tool, devrun subagent) for execution, graphite skill for knowledge |
| Stack traversal or "upstack"/"downstack"    | → [Graphite Stack Terminology](#-graphite-stack-terminology-critical) - main is at BOTTOM   |
| 4+ levels of indentation                    | → Extract helper functions                                                                  |
| Code in `__init__.py`                       | → Keep empty or docstring-only (except package entry points)                                |
| Tests for speculative features              | → **FORBIDDEN** - Only test actively implemented code (TDD is fine)                         |
| Creating `.claude/` artifacts               | → Use `kebab-case` (hyphens) NOT `snake_case` (underscores)                                 |

## 📚 Quick Reference

| Need help with...     | See documentation                                        |
| --------------------- | -------------------------------------------------------- |
| **Code examples**     | [docs/PATTERNS.md](docs/PATTERNS.md)                     |
| **Exception details** | [docs/EXCEPTION_HANDLING.md](docs/EXCEPTION_HANDLING.md) |
| **Quick lookup**      | [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)       |
| **Writing tests**     | [docs/TESTING.md](docs/TESTING.md)                       |

---

## 🟢 AGENT EXECUTION (Cost & Context Optimization)

**This codebase uses specialized agents for CLI tool execution and code analysis. These agents are cost-optimized and preserve context better than direct execution.**

### Why Use Agents?

- **Token Efficiency**: Subagent contexts don't pollute parent agent's context
- **Cost Optimization**: Uses Haiku model for command execution (cheaper than Sonnet)
- **Output Parsing**: Automatically parses tool output into structured format
- **Context Isolation**: Large command outputs stay in subagent, not main conversation
- **Skill Loading**: Automatically loads tool-specific skills for better results

### When to Use Agents

**ALWAYS use the Task tool with appropriate agent for:**

| Tool Type                                       | Agent                 | Example                                                                            |
| ----------------------------------------------- | --------------------- | ---------------------------------------------------------------------------------- |
| `make`, `pytest`, `pyright`, `ruff`, `prettier` | `runner`              | Task(subagent_type="runner", prompt="Execute: make all-ci")                        |
| `gt` commands (Graphite)                        | `runner`              | Task(subagent_type="runner", prompt="Execute: gt submit")                          |
| Graphite branch submission workflow             | `gt-branch-submitter` | Task(subagent_type="gt-branch-submitter", prompt="Execute submit-branch workflow") |

### Agent Invocation Pattern

```python
Task(
    subagent_type="runner",  # or "gt-branch-submitter", etc.
    description="Brief description of task",
    prompt="Execute: <command>"
)
```

### Common Mistakes

```python
# ❌ WRONG: Direct Bash for CLI tools
Bash("make all-ci")
Bash("uv run pytest tests/")
Bash("gt submit --publish")

# ✅ CORRECT: Use runner agent
Task(subagent_type="runner", description="Run CI checks", prompt="Execute: make all-ci")
Task(subagent_type="runner", description="Run tests", prompt="Execute: uv run pytest tests/")
Task(subagent_type="runner", description="Submit branch", prompt="Execute: gt submit --publish")

# ❌ WRONG: Manual branch submission
result = Bash("gt submit --publish")
# ...manually handle commit messages and PR metadata...

# ✅ CORRECT: Use gt-branch-submitter agent via /gt:submit-branch command
# The command delegates to the agent automatically
```

### What Can Use Bash Directly?

Git operations (read-only): `git status`, `git log`, `git diff`, `git branch`, etc.
File system operations: `ls`, `cat`, `find`, etc.
Simple shell commands: `echo`, `pwd`, etc.

🔴 **CRITICAL**: Using Bash directly for CLI tools (`make`, `pytest`, `ruff`, `gt`) wastes tokens, pollutes context, and bypasses cost optimization. This is expensive and inefficient.

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

**Full guide**: [docs/EXCEPTION_HANDLING.md](docs/EXCEPTION_HANDLING.md)

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

## 🔴 GRAPHITE STACK TERMINOLOGY (CRITICAL)

**When working with Graphite stacks, always visualize trunk at the BOTTOM:**

### Stack Visualization

```
TOP ↑    feat-3  ← upstack (leaf)
         feat-2
         feat-1
BOTTOM ↓ main    ← downstack (trunk)
```

### Directional Terminology 🔴 MUST UNDERSTAND

- **UPSTACK / UP** = away from trunk = toward TOP = toward leaves
- **DOWNSTACK / DOWN** = toward trunk = toward BOTTOM = toward main

### Examples

Given stack: `main → feat-1 → feat-2 → feat-3`

**If current branch is `feat-1`:**

- Upstack: `feat-2`, `feat-3` (children, toward top)
- Downstack: `main` (parent, toward bottom)

**If current branch is `feat-3` (at top):**

- Upstack: _(nothing, already at top/leaf)_
- Downstack: `feat-2`, `feat-1`, `main` (ancestors, toward bottom)

### Why This Is Critical

🔴 **Commands depend on this mental model:**

- `gt up` / `gt down` navigate the stack
- `land-stack` traverses branches in specific direction
- Stack traversal logic (parent/child relationships)

🔴 **Common mistake:** Thinking "upstack" means "toward trunk"

- **WRONG**: upstack = toward main ❌
- **CORRECT**: upstack = away from main ✅

🔴 **PR landing order:** Always bottom→top (main first, then each layer up)

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
- Claude artifacts: `kebab-case` (commands, skills, agents in `.claude/`)
- Brand names: `GitHub` (not Github)

**Claude Artifacts:** All files in `.claude/` (commands, skills, agents, hooks) MUST use `kebab-case`. Use hyphens, NOT underscores. Example: `/my-command` not `/my_command`. Python scripts within artifacts may use `snake_case` (they're code, not artifacts).

**Worktree Terminology:** Use "root worktree" (not "main worktree") to refer to the primary git worktree created with `git init`. This ensures "main" unambiguously refers to the branch name, since trunk branches can be named either "main" or "master". In code, use the `is_root` field to identify the root worktree.

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

**See**: [docs/EXCEPTION_HANDLING.md](docs/EXCEPTION_HANDLING.md)

### File Operations

- Always use `pathlib.Path` (never `os.path`)
- Always specify `encoding="utf-8"`
- Check `.exists()` before path operations

### CLI Development (Click)

- Use `click.echo()` for output (not `print()`)
- Use `click.echo(..., err=True)` for errors
- Exit with `raise SystemExit(1)` for CLI errors
- Use `subprocess.run(..., check=True)`

#### CLI Output Styling

**Use consistent colors and styling for CLI output via `click.style()`:**

| Element                  | Color            | Bold | Example                                             |
| ------------------------ | ---------------- | ---- | --------------------------------------------------- |
| Branch names             | `yellow`         | No   | `click.style(branch, fg="yellow")`                  |
| PR numbers               | `cyan`           | No   | `click.style(f"PR #{pr}", fg="cyan")`               |
| PR titles                | `bright_magenta` | No   | `click.style(title, fg="bright_magenta")`           |
| Success messages (✓)     | `green`          | No   | `click.style("✓ Done", fg="green")`                 |
| Section headers          | -                | Yes  | `click.style(header, bold=True)`                    |
| Current/active branches  | `bright_green`   | Yes  | `click.style(branch, fg="bright_green", bold=True)` |
| Paths (after completion) | `green`          | No   | `click.style(str(path), fg="green")`                |
| Paths (metadata)         | `white`          | Dim  | `click.style(str(path), fg="white", dim=True)`      |
| Error states             | `red`            | No   | `click.style("Error", fg="red")`                    |
| Dry run markers          | `bright_black`   | No   | `click.style("(dry run)", fg="bright_black")`       |
| Worktree/stack names     | `cyan`           | Yes  | `click.style(name, fg="cyan", bold=True)`           |

**Emoji conventions:**

- `✓` - Success indicators
- `✅` - Major success/completion
- `❌` - Errors/failures
- `📋` - Lists/plans
- `🗑️` - Deletion operations
- `⭕` - Aborted/cancelled
- `ℹ️` - Info notes

**Spacing:**

- Use empty `click.echo()` for vertical spacing between sections
- Use `\n` prefix in strings for section breaks
- Indent list items with `  ` (2 spaces)

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

**See**: [docs/TESTING.md](docs/TESTING.md) for comprehensive testing guidance.

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
- [docs/PATTERNS.md](docs/PATTERNS.md) - Code examples
- [docs/EXCEPTION_HANDLING.md](docs/EXCEPTION_HANDLING.md) - Exception guide
- [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Quick lookup
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
