# Quick Reference

**Read this when**: You need a quick lookup for file locations, fixtures, or example tests.

## Decision Tree: Where Should I Add My Test?

```
┌─ I need to test...
│
├─ A NEW FEATURE or BUG FIX
│  └─> tests/commands/ or tests/unit/ (over fakes) ← START HERE
│     Example: tests/commands/test_create.py
│
├─ A FAKE IMPLEMENTATION (test infrastructure)
│  └─> tests/unit/fakes/test_fake_*.py
│     Example: tests/unit/fakes/test_fake_gitops.py
│
├─ A REAL IMPLEMENTATION (code coverage with mocks)
│  └─> tests/integration/test_real_*.py
│     Example: tests/integration/test_real_gitops.py
│
└─ CRITICAL USER WORKFLOW (smoke test)
   └─> tests/integration/ (end-to-end, sparingly)
      Example: tests/integration/test_create_e2e.py
```

**Default**: When in doubt, write tests over fakes (Layer 3).

## File Location Map

### Source Code

```
src/workstack/
├── core/
│   ├── gitops.py              ← ABC interfaces, Real*, DryRun* classes
│   ├── graphite_ops.py        ← Graphite ops layer
│   ├── github_ops.py          ← GitHub ops layer
│   └── context.py             ← WorkstackContext
├── commands/                  ← CLI commands (business logic)
│   ├── create.py
│   ├── status.py
│   ├── land_stack.py
│   └── ...
└── ...
```

### Test Code

```
tests/
├── fakes/                     ← Fake implementations (in-memory)
│   ├── gitops.py              ← FakeGitOps
│   ├── graphite_ops.py        ← FakeGraphiteOps
│   ├── github_ops.py          ← FakeGitHubOps
│   └── __init__.py
├── unit/
│   ├── fakes/                 ← Tests OF fakes (Layer 1)
│   │   ├── test_fake_gitops.py
│   │   ├── test_fake_graphite_ops.py
│   │   └── test_fake_github_ops.py
│   └── ...                    ← Other unit tests over fakes
├── commands/                  ← CLI command tests over fakes (Layer 3)
│   ├── test_create.py
│   ├── test_status_with_fakes.py
│   └── ...
├── status/                    ← Business logic tests over fakes (Layer 3)
│   ├── test_plan_collector.py
│   └── ...
├── integration/               ← Tests WITH real ops (Layer 2) + E2E (Layer 4)
│   ├── test_real_gitops.py    ← Layer 2: mocked subprocess
│   ├── test_create_e2e.py     ← Layer 4: real git
│   └── scenario_builder.py    ← Test helpers
└── ...
```

## Common Fixtures

### pytest Built-in Fixtures

| Fixture       | Purpose                           | Usage                           |
| ------------- | --------------------------------- | ------------------------------- |
| `tmp_path`    | Temporary directory (Path object) | `def test_foo(tmp_path: Path):` |
| `monkeypatch` | Mock/patch objects                | `def test_foo(monkeypatch):`    |

### Project-Specific Fixtures

| Fixture/Helper                | Purpose                         | Usage                                                         |
| ----------------------------- | ------------------------------- | ------------------------------------------------------------- |
| `WorkstackContext.for_test()` | Create test context with fakes  | `ctx = WorkstackContext.for_test(git_ops=fake, cwd=tmp_path)` |
| `simulated_workstack_env()`   | Isolated filesystem environment | `with simulated_workstack_env(runner) as env:`                |
| `WorktreeScenario`            | Builder for complex scenarios   | `ctx = WorktreeScenario(tmp_path).with_main_branch().build()` |
| `CliRunner()`                 | Click test runner               | `runner = CliRunner(); result = runner.invoke(cmd, obj=ctx)`  |

### Fake Implementations

| Fake Class        | Location                      | Purpose                       |
| ----------------- | ----------------------------- | ----------------------------- |
| `FakeGitOps`      | `tests/fakes/gitops.py`       | In-memory git operations      |
| `FakeGraphiteOps` | `tests/fakes/graphite_ops.py` | In-memory Graphite operations |
| `FakeGitHubOps`   | `tests/fakes/github_ops.py`   | In-memory GitHub operations   |

## Common Test Patterns

### Basic CLI Test Over Fakes

```python
from click.testing import CliRunner

def test_my_command(tmp_path: Path) -> None:
    # Arrange
    git_ops = FakeGitOps(...)
    ctx = WorkstackContext.for_test(git_ops=git_ops, cwd=tmp_path)

    # Act
    runner = CliRunner()
    result = runner.invoke(my_cmd, obj=ctx)

    # Assert
    assert result.exit_code == 0
    assert "expected" in result.output
```

### Test with Builder Pattern

```python
def test_with_builder(tmp_path: Path) -> None:
    # Arrange
    ctx = (
        WorktreeScenario(tmp_path)
        .with_main_branch()
        .with_feature_branch("feat", pr_number=123)
        .build()
    )

    # Act
    runner = CliRunner()
    result = runner.invoke(status_cmd, obj=ctx)

    # Assert
    assert "#123" in result.output
```

### Test Fake Implementation

```python
def test_fake_tracks_mutations(tmp_path: Path) -> None:
    # Arrange
    git_ops = FakeGitOps()

    # Act
    git_ops.delete_branch(tmp_path, "feature")

    # Assert
    assert "feature" in git_ops.deleted_branches
```

### Test Real Implementation with Mocking

```python
def test_real_calls_correct_command(tmp_path: Path, monkeypatch) -> None:
    # Arrange: Mock subprocess
    calls = []
    def mock_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Act
    git_ops = RealGitOps()
    git_ops.delete_branch(tmp_path, "feature")

    # Assert
    assert calls[0] == ["git", "branch", "-d", "feature"]
```

## Example Tests to Reference

### Layer 1: Fake Infrastructure Tests

**Purpose**: Verify fakes work correctly

| File                                         | What It Tests                              |
| -------------------------------------------- | ------------------------------------------ |
| `tests/unit/fakes/test_fake_gitops.py`       | FakeGitOps tracks operations correctly     |
| `tests/unit/fakes/test_fake_graphite_ops.py` | FakeGraphiteOps simulates stacks correctly |
| `tests/unit/fakes/test_fake_github_ops.py`   | FakeGitHubOps returns configured PRs       |

### Layer 2: Real Ops with Mocking

**Purpose**: Get code coverage of real implementations

| File                                    | What It Tests                         |
| --------------------------------------- | ------------------------------------- |
| `tests/integration/test_real_gitops.py` | RealGitOps calls correct git commands |

### Layer 3: Business Logic Over Fakes (MAJORITY)

**Purpose**: Test features and bug fixes

| File                                       | What It Tests                          |
| ------------------------------------------ | -------------------------------------- |
| `tests/commands/test_create.py`            | Create worktree command                |
| `tests/commands/test_status_with_fakes.py` | Status command displays info correctly |
| `tests/status/test_plan_collector.py`      | Plan file collector logic              |
| `tests/commands/test_land_stack.py`        | Land stack workflow                    |

### Layer 4: End-to-End Integration

**Purpose**: Smoke tests over real system

| File                                   | What It Tests                 |
| -------------------------------------- | ----------------------------- |
| `tests/integration/test_create_e2e.py` | Create worktree with real git |

## Common Imports

```python
# Testing framework
import pytest
from click.testing import CliRunner
from pathlib import Path

# Fakes
from tests.fakes.gitops import FakeGitOps
from tests.fakes.graphite_ops import FakeGraphiteOps
from tests.fakes.github_ops import FakeGitHubOps

# Context
from workstack.core.context import WorkstackContext

# Domain objects
from workstack.core.gitops import WorktreeInfo
from workstack.core.github_ops import PRInfo

# Commands (import what you're testing)
from workstack.commands.create import create as create_cmd
from workstack.commands.status import status as status_cmd
```

## Useful Commands

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/commands/test_create.py

# Run specific test
uv run pytest tests/commands/test_create.py::test_create_worktree

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/workstack

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/

# Type check
uv run pyright

# Format code
uv run ruff format

# Lint code
uv run ruff check
```

## Test Distribution Guidelines

For a typical feature (e.g., "add worktree management"):

| Layer                    | Count       | Example                                                      |
| ------------------------ | ----------- | ------------------------------------------------------------ |
| Layer 1: Fake tests      | 1-2 tests   | Verify `FakeGitOps.add_worktree()` tracks correctly          |
| Layer 2: Real with mocks | 1-2 tests   | Verify `RealGitOps.add_worktree()` calls correct git command |
| Layer 3: Business logic  | 10-15 tests | Test feature over fakes (happy path, errors, edge cases)     |
| Layer 4: E2E             | 1 test      | Smoke test with real git                                     |

**Total**: ~20 tests, with 80% over fakes.

## Quick Checklist: Adding a New Ops Method

When adding a method to an ops interface:

- [ ] Add `@abstractmethod` to ABC (e.g., `GitOps`)
- [ ] Implement in real class (e.g., `RealGitOps`)
- [ ] Implement in fake class (e.g., `FakeGitOps`)
- [ ] Add mutation tracking to fake (if write operation)
- [ ] Add handler in dry-run wrapper (e.g., `DryRunGitOps`)
- [ ] Test fake (`tests/unit/fakes/test_fake_gitops.py`)
- [ ] Test real with mocking (`tests/integration/test_real_gitops.py`)
- [ ] Test business logic over fake (`tests/commands/test_*.py`)

## Related Documentation

- `testing-strategy.md` - Which layer to test at (detailed guide)
- `workflows.md` - Step-by-step guides for common tasks
- `patterns.md` - Common testing patterns explained
- `anti-patterns.md` - What to avoid
- `ops-architecture.md` - Understanding the ops layer
- `docs/agent/testing.md` - Comprehensive testing guide (project-wide)
