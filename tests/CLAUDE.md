---
mdstack:
  version: 0.1.0
  generated_docs:
    tests: .mdstack/TESTS.md
    lookup: .mdstack/LOOKUP.md
    architecture: .mdstack/OBSERVED_ARCHITECTURE.md
  instructions: "AI Agent: This scope has generated documentation in .mdstack/


    When to consult generated docs:

    - tests: For test coverage, testing patterns, what functionality is validated

    - lookup: For semantic search, finding code by concept/capability

    - architecture: For module organization, patterns, data flow, extension points


    Load these files only when needed for the current task."
---

# Test Structure Documentation

For comprehensive testing patterns and architecture, see:
**[.agent/docs/TESTING.md](../.agent/docs/TESTING.md)**

## Quick Commands

Run all tests: `uv run pytest`
Run specific test: `uv run pytest tests/commands/workspace/test_rm.py::test_rm_force_removes_directory`
Run with coverage: `uv run pytest --cov=workstack`

## Important: Directory Structure Requirements

**Every new subdirectory under `tests/` must include `__init__.py`** to ensure Python recognizes it as a regular package (not a namespace package).

Without `__init__.py`, pytest's import system breaks because Python 3.3+ treats directories without `__init__.py` as namespace packages, which disrupts absolute imports like `from tests.fakes.gitops import FakeGitOps`.

**When adding a new test directory:**

```bash
mkdir -p tests/my_new_category
touch tests/my_new_category/__init__.py  # ← ALWAYS add this!
```

See [unit/CLAUDE.md](unit/CLAUDE.md#directory-structure) for more details.

## Test Organization

Tests are organized hierarchically to optimize context loading and provide targeted guidance:

### Command Tests (CLI Layer)

- `tests/commands/` - CLI command tests with subcategories:
  - `workspace/` - Create, rename, rm, move commands
  - `navigation/` - Switch, up, down commands
  - `display/` - Status, tree, list commands
  - `shell/` - Shell integration and wrappers
  - `management/` - Garbage collection, planning
  - `setup/` - Init, config, completion

See [commands/CLAUDE.md](commands/CLAUDE.md) for CLI testing patterns.

### Core Tests (Business Logic Layer)

- `tests/core/` - Core logic unit tests with subcategories:
  - `config/` - Configuration management
  - `operations/` - Git, Graphite, GitHub operations (see [core/operations/CLAUDE.md](core/operations/CLAUDE.md))
  - `detection/` - Auto-detection logic
  - `utils/` - Utility functions
  - `foundation/` - Core infrastructure

See [core/CLAUDE.md](core/CLAUDE.md) for core testing patterns.

### Other Test Directories

- `tests/integration/` - Integration tests with real git
- `tests/status/` - Status system tests
- `tests/dev_cli_core/` - Dev CLI infrastructure tests
- `tests/fakes/` - Fake implementations for dependency injection

## Test Organization by Layer

Tests are organized by architectural layer to clarify dependencies:

### Layer 1: Unit Tests of Fakes (tests/unit/fakes/)

Tests that verify fake implementations work correctly. These test the **test infrastructure itself**.

**Contains:**

- `test_fake_gitops.py` - Tests FakeGitOps mutation tracking
- `test_fake_global_config_ops.py` - Tests FakeGlobalConfigOps state management
- Tests OF other fakes (GraphiteOps, GitHubOps, ShellOps)

**When to add tests here:** When modifying fake implementations or adding new fakes.

**Key principle:** These tests ensure fakes are reliable test doubles. If fakes are broken, all higher-layer tests are unreliable.

### Layer 2: Integration Tests (tests/integration/)

Tests with REAL implementations (actual git, filesystem, subprocess calls).

**Contains:**

- `test_real_gitops.py` - Tests RealGitOps with actual git commands
- `test_real_global_config.py` - Tests RealGlobalConfigOps with real filesystem
- `test_dryrun_integration.py` - Tests dry-run wrappers

**When to add tests here:** When testing that abstraction layers correctly wrap external tools.

**Key principle:** Uses `tmp_path` fixture, real subprocess calls, actual I/O.

### Layer 3: Command Tests (tests/commands/)

CLI layer tests using fakes. Tests user-facing command behavior.

**Contains:**

- `workspace/` - create, rename, move, rm commands
- `navigation/` - switch, up, down, jump commands
- `sync/` - sync command with Graphite integration
- `display/` - status, tree, list commands
- `setup/` - init, config commands

**When to add tests here:** When adding/modifying CLI commands.

**Key principle:** Uses `CliRunner` + `WorkstackContext` injection with fakes. May use `isolated_filesystem()` when fakes create directories.

### Layer 4: Core Tests (tests/core/)

Business logic tests using fakes. No CLI concerns.

**Contains:**

- `operations/` - Core logic (not fake tests!)
- `detection/` - Auto-detection algorithms
- `utils/` - Utility functions
- `foundation/` - Core infrastructure

**When to add tests here:** When adding core algorithms, utilities, detection logic.

**Key principle:** Direct function calls, no CliRunner. Never uses `isolated_filesystem()`.

## Layer Boundaries

```
┌─────────────────────────────────────┐
│   tests/commands/   (Layer 3)       │  Uses fakes
│   CLI commands via CliRunner        │
├─────────────────────────────────────┤
│   tests/core/       (Layer 4)       │  Uses fakes
│   Business logic, direct calls      │
├─────────────────────────────────────┤
│   tests/unit/fakes/ (Layer 1)       │  Tests fakes
│   Test infrastructure itself        │
├─────────────────────────────────────┤
│   tests/integration/ (Layer 2)      │  Uses real
│   Real git, filesystem, subprocess  │
└─────────────────────────────────────┘
```

## Quick Reference

| Need to...                      | See                                                                                                   |
| ------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Understand testing architecture | [.agent/docs/TESTING.md](../.agent/docs/TESTING.md)                                                   |
| Write a new CLI command test    | [.agent/docs/TESTING.md#unit-test-pattern](../.agent/docs/TESTING.md#unit-test-pattern)               |
| Test real git behavior          | [.agent/docs/TESTING.md#integration-test-pattern](../.agent/docs/TESTING.md#integration-test-pattern) |
| Test dry-run mode               | [.agent/docs/TESTING.md#dry-run-test-pattern](../.agent/docs/TESTING.md#dry-run-test-pattern)         |
| Configure fakes                 | [.agent/docs/TESTING.md#dependency-categories](../.agent/docs/TESTING.md#dependency-categories)       |

## Context Window Strategy

Each subdirectory has targeted CLAUDE.md files with domain-specific patterns:

- Load only the CLAUDE.md relevant to your current work
- Example: working on `test_create.py` → load `commands/workspace/CLAUDE.md`
- This reduces context noise by 50-70% compared to flat structure

## Testing Principles

1. **Use dependency injection** - All tests inject fakes via WorkstackContext
2. **No mock.patch** - Use FakeShellOps, FakeGitOps, etc. instead
3. **Constructor injection** - All fake state configured at construction
4. **Mutation tracking** - Use read-only properties for assertions (e.g., `git_ops.deleted_branches`)
5. **Three implementations** - Real (production), Dry-Run (safety), Fake (testing)

For complete details, see [.agent/docs/TESTING.md](../.agent/docs/TESTING.md).
