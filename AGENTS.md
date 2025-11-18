# Erk Coding Standards

> **Note**: This is unreleased, completely private software. We can break backwards
> compatibility completely at will based on preferences of the engineer developing
> the product.

<!-- AGENT NOTICE: This file is loaded automatically. Read FULLY before writing code. -->
<!-- Priority sections: BEFORE WRITING CODE (line 10), TOP 6 CRITICAL RULES (line 139), GRAPHITE STACK TERMINOLOGY (line 231) -->

## ⚠️ BEFORE WRITING CODE (AI Assistant Checklist)

**This codebase has strong opinions. Check these patterns BEFORE coding:**

**CRITICAL: NEVER search, read, or access `/Users/schrockn/.claude` directory**

**NOTE: `.plan/` folders are NOT tracked in git and should never be committed**

| If you're about to write...                                      | STOP! Check this instead                                                                             |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Writing or editing Python code                                   | → **🔴 LOAD dignified-python skill FIRST** - Complete LBYL philosophy (checklist rules are excerpts) |
| `try:` or `except:`                                              | → [Exception Handling](#exception-handling) - Default: let exceptions bubble                         |
| `from __future__ import annotations`                             | → **FORBIDDEN** - Python 3.13+ doesn't need it                                                       |
| `List[...]`, `Dict[...]`, `Union[...]`                           | → Use `list[...]`, `dict[...]`, `X \| Y`                                                             |
| `typing.Protocol`                                                | → Use `abc.ABC` instead                                                                              |
| `dict[key]` without checking                                     | → Use `if key in dict:` or `.get()`                                                                  |
| `path.resolve()` or `path.is_relative_to()`                      | → Check `path.exists()` first                                                                        |
| Function with default argument                                   | → Make explicit at call sites                                                                        |
| `from .module import`                                            | → Use absolute imports only                                                                          |
| `print(...)` in CLI code                                         | → Use `click.echo()`                                                                                 |
| `subprocess.run(...)`                                            | → Add `check=True`                                                                                   |
| Submitting a branch with Graphite                                | → Use /gt:submit-branch command (delegates to gt-branch-submitter agent)                             |
| Systematic Python changes (migrate calls, rename, batch updates) | → Use libcst-refactor agent (Task tool); for multi-file transformations                              |
| `pytest`, `pyright`, `ruff`, `prettier`, `make`, `gt` commands   | → Use devrun agent (Task tool) - specialized parsing, cost efficiency                                |
| Stack traversal or "upstack"/"downstack"                         | → [Graphite Stack Terminology](#-graphite-stack-terminology-critical) - main is at BOTTOM            |
| 4+ levels of indentation                                         | → Extract helper functions                                                                           |
| Code in `__init__.py`                                            | → Keep empty or docstring-only (except top-level public API exports)                                 |
| Tests for speculative features                                   | → **FORBIDDEN** - Only test actively implemented code (TDD is fine)                                  |
| Creating `.claude/` artifacts                                    | → Use `kebab-case` (hyphens) NOT `snake_case` (underscores)                                          |
| `Path("/test/...")` or hardcoded paths                           | → **CATASTROPHIC** - Use `pure_erk_env` fixture - [Test Isolation](#6-test-isolation--must)          |
| ⚠️ Python patterns above                                         | → These are EXCERPTS ONLY - Load dignified-python skill for complete guidance                        |

## 📚 Quick Reference

| Need help with...     | See documentation                                                            |
| --------------------- | ---------------------------------------------------------------------------- |
| **Python standards**  | **🔴 LOAD dignified-python skill FIRST** - Checklist rules are excerpts only |
| **Project terms**     | [docs/agent/glossary.md](docs/agent/glossary.md)                             |
| **Documentation nav** | [docs/agent/guide.md](docs/agent/guide.md)                                   |
| **Testing patterns**  | [docs/agent/testing.md](docs/agent/testing.md)                               |

## Documentation Structure

The `docs/` folder is organized by audience:

- **docs/agent/**: Agent-focused navigation and coding standards (quick references, patterns, rules)
- **docs/writing/**: Human-readable guides (agentic programming, writing style guides)
- Package-specific documentation lives in each package's README (e.g., `packages/erk-dev/README.md`)

## Python Coding Standards

🔴 **CRITICAL: Load dignified-python skill BEFORE writing Python code.**

**The checklist below contains quick references, but you MUST load the skill for:**

- Complete LBYL philosophy and rationale
- WHY behind each rule (not just WHAT)
- Anti-patterns and code smells from production use
- Progressive disclosure with detailed references

**The rules in this document are NOT sufficient on their own.**

To load: Use Skill tool with command "dignified-python"

---

**All Python coding standards are maintained in the `dignified-python` skill.**

To access Python coding standards, load the skill:

- Exception handling (LBYL vs EAFP)
- Type annotations (list[str], str | None)
- Dependency injection (ABC patterns)
- Import organization
- File operations
- CLI development
- Code style patterns

The `docs/agent/` folder contains only erk-specific documentation (terminology, testing, navigation).

---

## 🔴 TOP 8 CRITICAL RULES (Most Violated)

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

**Full guide**: [docs/agent/exception-handling.md](docs/agent/exception-handling.md)

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
# ✅ from erk.config import load_config
# ❌ from .config import load_config
```

### 6. Test Isolation 🔴 MUST

**NEVER use hardcoded paths in tests. ALWAYS use proper fixtures.**

```python
# ❌ WRONG - CATASTROPHICALLY DANGEROUS
cwd=Path("/test/default/cwd")
cwd=Path("/some/hardcoded/path")

# ✅ CORRECT - Use pure environment (PREFERRED)
with pure_erk_env(runner) as env:
    ctx = ErkContext(..., cwd=env.cwd)

# ✅ CORRECT - Use simulated environment (when filesystem I/O needed)
with simulated_erk_env(runner) as env:
    ctx = ErkContext(..., cwd=env.cwd)

# ✅ CORRECT - Use tmp_path fixture
def test_something(tmp_path: Path) -> None:
    ctx = ErkContext(..., cwd=tmp_path)
```

**Test Fixture Preference:**

🟢 **PREFER `pure_erk_env`** - Completely in-memory, zero filesystem I/O

- Uses sentinel paths that throw errors on filesystem operations
- Faster and enforces complete test isolation
- Use for tests verifying command logic and output

🟡 **USE `simulated_erk_env`** - When real directories needed

- Creates actual temp directories with `isolated_filesystem()`
- Use for testing filesystem-dependent features

**Why hardcoded paths are catastrophic:**

- **Global config mutation**: Code may write `.erk` files at hardcoded paths, polluting real filesystem
- **False isolation**: Tests appear isolated but share state through hardcoded paths
- **Security risk**: Creating files at system paths can be exploited

**If you see `Path("/` in test code, STOP and use fixtures.**

**Full guide**: [docs/agent/testing.md#critical-never-use-hardcoded-paths-in-tests](docs/agent/testing.md#critical-never-use-hardcoded-paths-in-tests)

### 7. dignified-python Skill Loading 🔴 MUST

**ALWAYS load dignified-python skill BEFORE editing Python code**

The checklist above contains quick-reference excerpts of Python rules. **This is NOT sufficient on their own.**

**The dignified-python skill contains:**

- Complete LBYL philosophy and rationale (WHY, not just WHAT)
- Anti-patterns and code smells from production systems (Dagster Labs)
- Progressive disclosure with detailed references
- Unified philosophy connecting all the rules

```python
# ❌ WRONG: Following checklist rules without loading skill
# You implement code based only on checklist excerpts
# Missing: WHY behind rules, anti-patterns, unified philosophy

# ✅ CORRECT: Load skill first
# Use Skill tool with command: "dignified-python"
# Then implement code with complete understanding
```

**WHY this matters:**

- Individual rules without context lead to cargo-cult programming
- The checklist shows WHAT to do, the skill explains WHY
- Anti-patterns and code smells prevent specific production bugs
- Progressive disclosure provides references when you need deeper guidance

**Note**: The rules in this document are NOT sufficient on their own. Always load the skill.

### 8. Development Tool Execution 🔴 MUST

**NEVER execute dev tools directly via Bash. ALWAYS use devrun agent.**

```python
# ❌ WRONG: Direct Bash execution
Bash("pytest tests/")
Bash("uv run pyright")
Bash("make test-unit")

# ✅ CORRECT: Use devrun agent with Task tool
Task(
    subagent_type="devrun",
    description="Run unit tests",
    prompt="Run pytest tests/"
)
```

**WHY this matters:**

- **Specialized output parsing**: devrun understands tool-specific output formats
- **Cost efficiency**: Optimized token usage for test results and linter output
- **Consistent error handling**: Unified interface across all dev tools

**Covered tools:**

- `pytest` - Python test runner
- `pyright` - Python type checker
- `ruff` - Python linter and formatter
- `prettier` - Code formatter (markdown, JSON, etc.)
- `make` - Build automation
- `gt` - Graphite CLI for stacked PRs

**When to use devrun:**

- ANY time you need to run one of these tools
- With or without `uv run` prefix
- For single commands or CI workflows (like `/ensure-ci`)

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

- Source: `src/erk/`
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
6. **Dry-Run via Dependency Injection**: Never pass dry_run flags through business logic

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

**See**: [docs/agent/exception-handling.md](docs/agent/exception-handling.md)

### Dry-Run Pattern

**This codebase uses dependency injection for dry-run mode, NOT boolean flags.**

🔴 **MUST**: Use NoopGitOps wrapper for dry-run mode
🔴 **MUST NOT**: Pass dry_run flags through business logic functions
🟡 **SHOULD**: Keep dry-run UI logic at the CLI layer only

**Wrong Pattern:**

```python
# ❌ WRONG: Passing dry_run flag through business logic
def execute_plan(plan, git_ops, dry_run=False):
    if not dry_run:
        git_ops.add_worktree(...)
```

**Correct Pattern:**

```python
# ✅ CORRECT: Rely on injected ops implementation
def execute_plan(plan, git_ops):
    # Always execute - behavior depends on git_ops implementation
    git_ops.add_worktree(...)  # NoopGitOps does nothing, RealGitOps executes

# At the context creation level:
if dry_run:
    git_ops = NoopGitOps(real_ops)  # or PrintingGitOps(NoopGitOps(...))
else:
    git_ops = real_ops  # or PrintingGitOps(real_ops)
```

**Rationale:**

- Keeps business logic pure and testable
- Dry-run behavior is determined by dependency injection
- No conditional logic scattered throughout the codebase
- Single responsibility: business logic doesn't know about UI modes

### File Operations

- Always use `pathlib.Path` (never `os.path`)
- Always specify `encoding="utf-8"`
- Check `.exists()` before path operations

### Context Regeneration

**When to regenerate context:**

After filesystem mutations that invalidate `ctx.cwd`:

- After `os.chdir()` calls
- After worktree removal (if removed current directory)
- After switching repositories

**How to regenerate:**

Use `regenerate_context()` from `erk.core.context`:

```python
from erk.core.context import regenerate_context

# After os.chdir()
os.chdir(new_directory)
ctx = regenerate_context(ctx, repo_root=repo.root)

# After worktree removal
if removed_current_worktree:
    os.chdir(safe_directory)
    ctx = regenerate_context(ctx, repo_root=repo.root)
```

**Why regenerate:**

- `ctx.cwd` is captured once at CLI entry point
- After `os.chdir()`, `ctx.cwd` becomes stale
- Stale `ctx.cwd` causes `FileNotFoundError` in operations that use it
- Regeneration creates NEW context with fresh `cwd` and `trunk_branch`

### CLI Development (Click)

- Use `click.echo()` for output (not `print()`)
- Use `click.echo(..., err=True)` for errors
- Exit with `raise SystemExit(1)` for CLI errors
- Use `subprocess.run(..., check=True)`

For comprehensive guidance on adding CLI commands, including JSON output support, see:

**[docs/agent/erk/cli-commands.md](docs/agent/erk/cli-commands.md)** - Complete CLI command development guide

Quick reference:

- Output abstraction: `user_output()` (stderr) for users, `machine_output()` (stdout) for scripts
- JSON support: Three patterns (simple, complex, renderer-based)
- Testing: Minimum 3 tests per JSON feature
- See full guide for flag naming, Pydantic schemas, and examples

### Code Style

- **Max 4 levels of indentation** - extract helper functions
- Use early returns and guard clauses
- No default arguments without explanatory comments
- Use context managers directly in `with` statements

### Testing

🔴 **MUST**: Only write tests for code being actively implemented
🔴 **FORBIDDEN**: Writing tests for speculative or "maybe later" features

**When Tests Are Required:**

🔴 **MUST write tests for:**

- **Adding a feature** → Test over fake layer
- **Fixing a bug** → Test over fake layer (reproduce bug, then fix)
- **Changing business logic** → Test over fake layer

**Default testing position:** Any change to business logic, features, or bug fixes MUST include tests written over the fake layer.

🔴 **MUST add coverage for ops implementations:**

- **New ops interface method** → Test the real implementation with mocked stateful interactions
- **Example:** Adding `GitOps.new_method()` → Mock subprocess calls, test error paths
- **Goal:** Ensure code coverage even when underlying systems (git, filesystem, network) are mocked

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

**CLI Testing Performance:**

- Use Click's `CliRunner` for command tests (NOT subprocess)
- Only use subprocess for true end-to-end tests
- See [docs/agent/testing.md#cli-testing-patterns](docs/agent/testing.md#cli-testing-patterns) for detailed patterns and performance comparison

**See**: [docs/agent/testing.md](docs/agent/testing.md) for comprehensive testing guidance.

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

- Load `dignified-python` skill for Python coding standards
- [docs/agent/glossary.md](docs/agent/glossary.md) - Project terminology
- [docs/agent/guide.md](docs/agent/guide.md) - Documentation navigation
- [docs/agent/testing.md](docs/agent/testing.md) - Testing architecture
- [docs/writing/agentic-programming/agentic-programming.md](docs/writing/agentic-programming/agentic-programming.md) - Agentic programming patterns
- [README.md](README.md) - Project overview

## Installed Kit Documentation

🔴 **CRITICAL: ALWAYS load this registry before working with kits, agents, commands, or skills.**

The kit documentation registry contains the complete index of ALL installed kit documentation in this project. This includes:

- Agent definitions and capabilities
- Available slash commands
- Skills and their purposes
- Reference documentation

**MUST LOAD:** Before answering questions about available kits, agents, commands, or skills, ALWAYS reference:

@.claude/docs/kit-registry.md

This registry is automatically maintained and updated when kits are installed, updated, or removed. It is the single source of truth for what kit functionality is available in this project.

## Skills and Agents

See the kit registry for complete documentation on available agents, commands, and skills. The registry is loaded automatically and provides usage guidance for all installed kits.
