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

**NOTE: `.submission/` folders ARE tracked in git as signals for remote AI implementation**

## .submission/ Folder Protocol

**Purpose:** Signal for remote AI implementation via GitHub Actions

**Workflow:**

1. Create worktree with `/erk:create-planned-wt` (creates .plan/)
2. Run `erk submit` to copy .plan/ to .submission/
3. GitHub Actions detects .submission/ and runs implementation
4. .submission/ is auto-deleted after completion

**Key differences from .plan/:**

- `.plan/` = Local implementation tracking (NOT git-tracked)
- `.submission/` = Remote submission signal (git-tracked, ephemeral)

**Important:** `.submission/` folders should NOT be added to .gitignore. They are meant to be committed as a signal to GitHub Actions.

---

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
| `subprocess.run(..., check=True)`                                | → Use `run_subprocess_with_context()` from erk.core.subprocess for rich errors                       |
| Creating or executing implementation plans                       | → Use /erk:persist-plan, /erk:create-planned-wt, /erk:implement-plan, erk submit                     |
| Submitting a branch with Graphite                                | → Use /gt:submit-branch command (delegates to gt-branch-submitter agent)                             |
| Updating an existing PR                                          | → Use /gt:update-pr command                                                                          |
| Systematic Python changes (migrate calls, rename, batch updates) | → Use libcst-refactor agent (Task tool); for multi-file transformations                              |
| `pytest`, `pyright`, `ruff`, `prettier`, `make`, `gt` commands   | → Use devrun agent (Task tool) - specialized parsing, cost efficiency                                |
| Stack traversal or "upstack"/"downstack"                         | → [Graphite Stack Terminology](#-graphite-stack-terminology-critical) - main is at BOTTOM            |
| 4+ levels of indentation                                         | → Extract helper functions                                                                           |
| Code in `__init__.py`                                            | → Keep empty or docstring-only (except top-level public API exports)                                 |
| Tests for speculative features                                   | → **FORBIDDEN** - Only test actively implemented code (TDD is fine)                                  |
| Creating `.claude/` artifacts                                    | → Use `kebab-case` (hyphens) NOT `snake_case` (underscores)                                          |
| `Path("/test/...")` or hardcoded paths                           | → **CATASTROPHIC** - Use `pure_erk_env` fixture - [Test Isolation](#6-test-isolation--must)          |
| Writing or modifying tests                                       | → **🔴 LOAD fake-driven-testing skill FIRST** - Test patterns, architecture, anti-patterns           |
| Test that invokes subprocess or uses `time.sleep()`              | → **MUST** be integration test - [Test Categorization](#test-categorization-rules)                   |
| Creating or modifying hooks                                      | → [Hook Guide](docs/agent/hooks.md)                                                                  |
| ⚠️ Python patterns above                                         | → These are EXCERPTS ONLY - Load dignified-python skill for complete guidance                        |

## 📚 Quick Reference

| Need help with...     | See documentation                                                            |
| --------------------- | ---------------------------------------------------------------------------- |
| **Python standards**  | **🔴 LOAD dignified-python skill FIRST** - Checklist rules are excerpts only |
| **Project terms**     | [docs/agent/glossary.md](docs/agent/glossary.md)                             |
| **Documentation nav** | [docs/agent/guide.md](docs/agent/guide.md)                                   |
| **Testing patterns**  | [docs/agent/testing.md](docs/agent/testing.md)                               |
| **Hooks**             | [docs/agent/hooks.md](docs/agent/hooks.md)                                   |

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

class MyIntegration(ABC):  # ✅ Not Protocol
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

### 9. Subprocess Execution 🔴 MUST

**NEVER use bare `subprocess.run(..., check=True)`. ALWAYS use wrapper functions.**

**For integration layer (raises exceptions):**

```python
from erk.core.subprocess import run_subprocess_with_context

# ✅ CORRECT: Rich error context with stderr
result = run_subprocess_with_context(
    ["git", "worktree", "add", str(path), branch],
    operation_context=f"add worktree for branch '{branch}' at {path}",
    cwd=repo_root,
)
```

**For CLI layer (user-friendly output):**

```python
from erk.cli.subprocess_utils import run_with_error_reporting

# ✅ CORRECT: User-friendly error messages + SystemExit
run_with_error_reporting(
    ["gh", "pr", "view", str(pr_number)],
    operation_context="view pull request",
    cwd=repo_root,
)
```

**WHY this matters:**

- **Rich error messages**: Includes operation context, command, exit code, stderr
- **Exception chaining**: Preserves original CalledProcessError for debugging
- **Consistent patterns**: Two-layer design (integration vs CLI boundaries)

**Two-layer pattern:**

- `run_subprocess_with_context()` - Integration layer (raises RuntimeError)
- `run_with_error_reporting()` - CLI layer (prints message, raises SystemExit)

**DO NOT migrate check=False LBYL patterns:**

```python
# ✅ CORRECT: Intentional LBYL pattern (keep as-is)
result = subprocess.run(cmd, check=False, capture_output=True, text=True)
if result.returncode != 0:
    return None  # Graceful degradation
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

🔴 **MUST**: Use Noop wrappers for dry-run mode
🔴 **MUST NOT**: Pass dry_run flags through business logic functions
🟡 **SHOULD**: Keep dry-run UI logic at the CLI layer only

**Wrong Pattern:**

```python
# ❌ WRONG: Passing dry_run flag through business logic
def execute_plan(plan, git, dry_run=False):
    if not dry_run:
        git.add_worktree(...)
```

**Correct Pattern:**

```python
# ✅ CORRECT: Rely on injected integration implementation
def execute_plan(plan, git):
    # Always execute - behavior depends on git implementation
    git.add_worktree(...)  # NoopGit does nothing, RealGit executes

# At the context creation level:
if dry_run:
    git = NoopGit(real_git)  # or PrintingGit(NoopGit(...))
else:
    git = real_git  # or PrintingGit(real_git)
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

#### CLI Output Abstraction

**Use output abstraction for all CLI output:**

- `user_output()` - Routes to stderr for user-facing messages
- `machine_output()` - Routes to stdout for shell integration data

**Import:** `from erk.cli.output import user_output, machine_output`

**When to use each:**

| Use case                  | Function           | Rationale                   |
| ------------------------- | ------------------ | --------------------------- |
| Status messages           | `user_output()`    | User info, goes to stderr   |
| Error messages            | `user_output()`    | User info, goes to stderr   |
| Progress indicators       | `user_output()`    | User info, goes to stderr   |
| Success confirmations     | `user_output()`    | User info, goes to stderr   |
| Shell activation scripts  | `machine_output()` | Script data, goes to stdout |
| JSON output (--json flag) | `machine_output()` | Script data, goes to stdout |
| Paths for script capture  | `machine_output()` | Script data, goes to stdout |

**Example:**

```python
from erk.cli.output import user_output, machine_output

# User-facing messages
user_output(f"✓ Created worktree {name}")
user_output(click.style("Error: ", fg="red") + "Branch not found")

# Script/machine data
machine_output(json.dumps(result))
machine_output(str(activation_path))
```

**Reference implementations:**

- `src/erk/cli/commands/sync.py` - Uses custom `_emit()` helper
- `src/erk/cli/commands/jump.py` - Uses both user_output() and machine_output()
- `src/erk/cli/commands/consolidate.py` - Uses both abstractions

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

🔴 **MUST add coverage for integration class implementations:**

- **New integration interface method** → Test the real implementation with mocked stateful interactions
- **Example:** Adding `Git.new_method()` → Mock subprocess calls, test error paths
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

#### Test Categorization Rules

🔴 **CRITICAL: A test MUST be categorized as an integration test if:**

1. **It invokes a subprocess** - Any test that calls `subprocess.run()`, `subprocess.Popen()`, or similar
2. **It uses `time.sleep()`** - Tests that rely on actual timing delays (must use mocking or DI instead)
3. **It performs extensive real filesystem I/O** - Tests that interact with external filesystem locations, create many files, or depend on actual filesystem behavior (limited file I/O with `isolated_filesystem()` or `tmp_path` in unit tests is acceptable)
4. **It tests subprocess boundaries** - Tests validating that abstraction layers correctly wrap external tools

**Location rules:**

- **Unit tests** → `tests/unit/`, `tests/commands/`, `tests/core/`
  - Use fakes (FakeGit, FakeShell, etc.)
  - Use `CliRunner` (NOT subprocess)
  - No `time.sleep()` calls
  - Fast, in-memory execution

- **Integration tests** → `tests/integration/`
  - Use real implementations (RealGit, etc.)
  - May invoke subprocess calls
  - May use `tmp_path` fixture for real directories
  - Slower, tests external tool integration

**Examples:**

```python
# ❌ WRONG - Unit test location with subprocess call
# Located in tests/commands/test_sync.py
def test_sync_calls_git() -> None:
    result = subprocess.run(["git", "fetch"], capture_output=True)
    # This MUST be moved to tests/integration/

# ❌ WRONG - Unit test with time.sleep()
# Located in tests/unit/test_retry.py
def test_retry_with_backoff() -> None:
    time.sleep(0.5)  # Actual delay
    # This MUST be moved to tests/integration/ OR use mocking

# ✅ CORRECT - Integration test with subprocess
# Located in tests/integration/test_real_git.py
def test_real_git_fetch(tmp_path: Path) -> None:
    result = subprocess.run(["git", "fetch"], cwd=tmp_path, capture_output=True)
    assert result.returncode == 0

# ✅ CORRECT - Unit test with mocked sleep
# Located in tests/unit/test_retry.py
def test_retry_with_backoff(monkeypatch) -> None:
    mock_sleep = Mock()
    monkeypatch.setattr("time.sleep", mock_sleep)
    # Test logic without actual delay
```

**Why this matters:**

- **CI performance**: Unit tests must remain fast (<2s total) for quick feedback
- **Test reliability**: Subprocess calls can fail due to environment differences
- **Parallel execution**: Tests with subprocesses may have race conditions
- **Resource usage**: Subprocess tests consume more system resources

**If you're unsure:** Default to integration test. It's safer to categorize a test as integration than to slow down the unit test suite.

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

@.agent/kits/README.md
@.agent/kits/kit-registry.md

This registry is automatically maintained and updated when kits are installed, updated, or removed. It is the single source of truth for what kit functionality is available in this project.

## Skills and Agents

See the kit registry for complete documentation on available agents, commands, and skills. The registry is loaded automatically and provides usage guidance for all installed kits.
