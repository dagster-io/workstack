# Testing Architecture: Ops Layer and Fakes

This document describes universal testing architecture patterns used across Python projects that employ the ops layer abstraction and fake implementations for testing.

**Audience:** This is universal architecture guidance applicable to any Python project using these patterns, not specific to any particular codebase.

**Related:** For erk-specific terminology and testing details, see [erk/glossary.md](erk/glossary.md).

---

## Table of Contents

- [Overview](#overview)
- [Operations Layer (Ops)](#operations-layer-ops)
- [Fake Implementations](#fake-implementations)
- [Dry Run Wrappers](#dry-run-wrappers)
- [Testing Strategy](#testing-strategy)
- [Best Practices](#best-practices)

---

## Overview

The **ops layer** is an architectural pattern that abstracts external dependencies (filesystem, subprocess calls, network APIs) behind ABC interfaces. This enables:

- **Fast unit tests** - Use in-memory fakes instead of real I/O
- **Testability** - Inject controlled test doubles
- **Composability** - Wrap implementations with decorators (dry-run, logging, etc.)
- **Clear boundaries** - Explicit separation between business logic and external interactions

**Core principle:** Business logic depends on ops interfaces (ABCs), not concrete implementations.

---

## Operations Layer (Ops)

### Ops Interface Pattern

An **ops interface** is an Abstract Base Class (ABC) that defines operations for external integrations.

**Structure:**

```python
from abc import ABC, abstractmethod
from pathlib import Path

class GitOps(ABC):
    """Interface for git operations."""

    @abstractmethod
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository.

        Args:
            repo_root: Path to repository root

        Returns:
            List of worktree information
        """
        pass

    @abstractmethod
    def create_branch(self, repo_root: Path, branch_name: str, ref: str) -> None:
        """Create a new branch.

        Args:
            repo_root: Path to repository root
            branch_name: Name for the new branch
            ref: Starting reference (commit, branch, tag)
        """
        pass
```

**Characteristics:**

- **ABC-based** - Use `abc.ABC`, not `typing.Protocol`
- **Explicit methods** - Each operation is a separate abstract method
- **Type annotations** - Full type signatures for all parameters and returns
- **Docstrings** - Document behavior, parameters, and return values
- **Stateless** - No instance state in the interface definition

**Common ops interfaces:**

- `GitOps` - Git repository operations
- `FileOps` - Filesystem operations
- `ConfigOps` - Configuration read/write
- `GitHubOps` - GitHub API operations
- `SlackOps` - Slack API operations

### Real Implementation

A **real implementation** executes actual operations against external systems.

**Naming convention:** `Real<Interface>` (e.g., `RealGitOps`)

**Pattern:**

```python
import subprocess
from pathlib import Path

class RealGitOps(GitOps):
    """Production git operations using subprocess."""

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List worktrees by parsing git worktree list output."""
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return self._parse_worktree_output(result.stdout)

    def create_branch(self, repo_root: Path, branch_name: str, ref: str) -> None:
        """Create branch using git branch command."""
        subprocess.run(
            ["git", "branch", branch_name, ref],
            cwd=repo_root,
            check=True,
        )

    def _parse_worktree_output(self, output: str) -> list[WorktreeInfo]:
        """Private helper to parse git output."""
        # Implementation details...
        pass
```

**Characteristics:**

- **Subprocess calls** - Uses `subprocess.run()` with `check=True`
- **Actual I/O** - Reads/writes to real filesystem, network, etc.
- **Error handling** - Subprocess errors bubble up as `CalledProcessError`
- **Private helpers** - Use private methods for parsing/formatting
- **Stateless** - No mutable instance state (may cache immutable config)

**Usage:**

```python
# Instantiated in production context creation
def create_production_context() -> Context:
    return Context(
        git_ops=RealGitOps(),
        file_ops=RealFileOps(),
        config_ops=RealConfigOps(),
    )
```

---

## Fake Implementations

A **fake implementation** provides in-memory, deterministic behavior for testing.

**Naming convention:** `Fake<Interface>` (e.g., `FakeGitOps`)

**Location:** `tests/fakes/<interface>.py`

### Constructor-Only State Rule

🔴 **CRITICAL RULE:** All fake state MUST be set via constructor parameters. NO public setup methods.

**Why:**

- **Immutability** - Fakes are immutable after construction
- **Discoverability** - All state visible at construction site
- **No surprises** - Test data defined upfront, not scattered
- **Composability** - Easy to create test fixtures with different configurations

### Fake Implementation Pattern

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class WorktreeInfo:
    """Immutable worktree data."""
    path: Path
    branch: str
    is_root: bool


class FakeGitOps(GitOps):
    """In-memory fake for git operations."""

    def __init__(
        self,
        *,
        worktrees: list[WorktreeInfo] | None = None,
        branches: set[str] | None = None,
    ):
        """Initialize fake with predetermined state.

        Args:
            worktrees: Worktrees that exist in the fake repository
            branches: Branches that exist in the fake repository
        """
        self._worktrees = worktrees or []
        self._branches = branches or set()

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """Return predetermined worktree list."""
        return self._worktrees

    def create_branch(self, repo_root: Path, branch_name: str, ref: str) -> None:
        """Record branch creation (in-memory only)."""
        if branch_name in self._branches:
            raise ValueError(f"Branch already exists: {branch_name}")
        self._branches.add(branch_name)
```

**Characteristics:**

- **Constructor parameters** - All state via `__init__` kwargs
- **Keyword-only** - Use `*,` to force keyword arguments
- **Optional defaults** - Provide sensible defaults (empty lists, None, etc.)
- **Immutable** - Use frozen dataclasses or tuples for data
- **No I/O** - No subprocess calls, no filesystem access
- **Fast** - Operations complete in microseconds

### Usage in Tests

```python
def test_list_worktrees():
    """Test listing worktrees with fake."""
    # Setup: Create fake with test data
    fake_git = FakeGitOps(
        worktrees=[
            WorktreeInfo(path=Path("/repo/main"), branch="main", is_root=True),
            WorktreeInfo(path=Path("/repo/feature"), branch="feature-x", is_root=False),
        ]
    )

    # Execute: Use fake in business logic
    context = Context(git_ops=fake_git)
    result = list_all_worktrees(context, Path("/repo"))

    # Assert: Verify behavior
    assert len(result) == 2
    assert result[0].branch == "main"
```

### Anti-Patterns to Avoid

```python
# ❌ WRONG: Public setup methods
class FakeGitOps(GitOps):
    def __init__(self):
        self._worktrees = []

    def add_worktree(self, worktree: WorktreeInfo) -> None:
        """Public method to add worktrees - FORBIDDEN"""
        self._worktrees.append(worktree)


# ❌ WRONG: Mutable state after construction
def test_something():
    fake_git = FakeGitOps()
    fake_git.add_worktree(...)  # State scattered across test
    fake_git.add_worktree(...)  # Hard to see full test scenario


# ✅ CORRECT: Constructor-only state
class FakeGitOps(GitOps):
    def __init__(self, *, worktrees: list[WorktreeInfo] | None = None):
        self._worktrees = worktrees or []


# ✅ CORRECT: All state at construction
def test_something():
    fake_git = FakeGitOps(
        worktrees=[...]  # All test data visible upfront
    )
```

---

## Dry Run Wrappers

A **dry run wrapper** intercepts destructive operations and prints what would happen instead of executing.

**Naming convention:** `DryRun<Interface>` or `Noop<Interface>` (e.g., `DryRunGitOps`, `NoopGitOps`)

### Pattern: Wrapper with Selective Passthrough

```python
class DryRunGitOps(GitOps):
    """Wrapper that prints instead of executing destructive operations."""

    def __init__(self, wrapped: GitOps):
        """Wrap an existing ops implementation.

        Args:
            wrapped: Real ops implementation to wrap
        """
        self._wrapped = wrapped

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """Read-only operation - pass through to wrapped implementation."""
        return self._wrapped.list_worktrees(repo_root)

    def create_branch(self, repo_root: Path, branch_name: str, ref: str) -> None:
        """Destructive operation - print message instead of executing."""
        print(f"[DRY RUN] Would create branch '{branch_name}' from '{ref}'")
```

**Characteristics:**

- **Decorator pattern** - Wraps another ops implementation
- **Selective passthrough** - Read-only operations execute normally
- **Destructive operations blocked** - Write operations print messages
- **Composable** - Can wrap real or fake implementations

### Usage: Dependency Injection for Dry Run

**Wrong pattern:** Boolean flags through business logic

```python
# ❌ WRONG: Passing dry_run flag
def execute_plan(plan, git_ops, dry_run=False):
    if not dry_run:
        git_ops.create_branch(...)
```

**Correct pattern:** Inject dry run wrapper

```python
# ✅ CORRECT: Dependency injection
def execute_plan(plan, git_ops):
    # Business logic doesn't know about dry run
    git_ops.create_branch(...)  # Behavior depends on injected implementation


# At CLI layer / context creation:
if dry_run:
    git_ops = DryRunGitOps(RealGitOps())
else:
    git_ops = RealGitOps()

context = Context(git_ops=git_ops)
```

**Benefits:**

- Business logic stays pure and testable
- Dry-run behavior controlled by dependency injection
- No conditional logic scattered through the codebase
- Single responsibility: business logic doesn't know about UI modes

---

## Testing Strategy

### Three-Tier Testing Approach

**1. Unit Tests (Majority of Suite)**

- **Location:** `tests/unit/`, `tests/commands/`
- **Dependencies:** Fake implementations only
- **Speed:** Very fast (milliseconds)
- **Coverage:** Business logic, edge cases, error paths

```python
def test_create_worktree_validation():
    """Test validation logic with fakes."""
    fake_git = FakeGitOps(worktrees=[...])
    fake_config = FakeConfigOps(config={...})

    context = Context(git_ops=fake_git, config_ops=fake_config)

    with pytest.raises(ValidationError):
        create_worktree(context, invalid_name)
```

**2. Integration Tests (Selective Coverage)**

- **Location:** `tests/integration/`
- **Dependencies:** Real implementations, real filesystem
- **Speed:** Slower (seconds)
- **Coverage:** Integration with external systems

```python
def test_git_operations_integration(tmp_path):
    """Test real git operations."""
    real_git = RealGitOps()

    # Setup real git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)

    # Test real operation
    real_git.create_branch(tmp_path, "test-branch", "HEAD")

    # Verify with real git command
    result = subprocess.run(
        ["git", "branch", "--list", "test-branch"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "test-branch" in result.stdout
```

**3. End-to-End Tests (Minimal Coverage)**

- **Location:** `tests/e2e/`
- **Dependencies:** Full stack, real external services
- **Speed:** Slowest (seconds to minutes)
- **Coverage:** Critical user journeys

### Test Organization

```
tests/
├── fakes/              # Fake implementations
│   ├── git_ops.py      # FakeGitOps
│   ├── config_ops.py   # FakeConfigOps
│   └── github_ops.py   # FakeGitHubOps
├── unit/               # Fast unit tests with fakes
│   ├── test_commands/
│   └── test_core/
├── integration/        # Real I/O tests
│   └── test_git_integration.py
└── e2e/                # Full stack tests
    └── test_workflow.py
```

---

## Best Practices

### Ops Interface Design

**DO:**

- ✅ Use ABC, not Protocol
- ✅ One interface per external system
- ✅ Stateless interfaces
- ✅ Explicit method signatures
- ✅ Type annotations everywhere
- ✅ Docstrings for all methods

**DON'T:**

- ❌ Don't use Protocol (use ABC)
- ❌ Don't add instance state to interfaces
- ❌ Don't use default arguments (make explicit at call sites)
- ❌ Don't expose internal implementation details in interface

### Fake Implementation Design

**DO:**

- ✅ Constructor-only state (critical rule)
- ✅ Use keyword-only arguments (`*,` in `__init__`)
- ✅ Provide sensible defaults (empty lists, None)
- ✅ Use immutable data structures (frozen dataclasses)
- ✅ Keep fakes fast (no I/O, no subprocess)
- ✅ Store fakes in `tests/fakes/` directory

**DON'T:**

- ❌ NEVER add public setup methods (violates constructor-only rule)
- ❌ Don't use mutable default arguments
- ❌ Don't add complex logic in fakes (keep them simple)
- ❌ Don't do I/O in fakes (defeats the purpose)

### Testing Strategy

**DO:**

- ✅ Write unit tests with fakes first
- ✅ Use integration tests for external system contracts
- ✅ Keep integration tests focused and minimal
- ✅ Use temporary directories for filesystem tests
- ✅ Clean up resources in teardown

**DON'T:**

- ❌ Don't use real implementations in unit tests
- ❌ Don't skip unit tests because you have integration tests
- ❌ Don't test business logic in integration tests
- ❌ Don't leave test artifacts on the filesystem

### Dependency Injection

**DO:**

- ✅ Inject ops implementations via context/container
- ✅ Use dry run wrappers for `--dry-run` flags
- ✅ Create context at CLI layer, not in business logic
- ✅ Keep business logic pure (no knowledge of dry run)

**DON'T:**

- ❌ Don't pass `dry_run` boolean flags through business logic
- ❌ Don't create ops implementations in business logic
- ❌ Don't use global singletons for ops

---

## Related Documentation

**Universal patterns:**

- Load `dignified-python` skill for Python coding standards
- Load `layered-testing` skill for defense-in-depth testing strategy

**Project-specific:**

- [erk/glossary.md](erk/glossary.md) - Erk-specific terminology
- Project AGENTS.md - Coding standards for specific project

---

## Examples in Practice

### Example: Complete Ops Setup

```python
# 1. Define interface
class DatabaseOps(ABC):
    @abstractmethod
    def execute_query(self, query: str) -> list[dict]:
        pass


# 2. Real implementation
class RealDatabaseOps(DatabaseOps):
    def __init__(self, connection_string: str):
        self._conn_string = connection_string

    def execute_query(self, query: str) -> list[dict]:
        conn = psycopg2.connect(self._conn_string)
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()


# 3. Fake implementation
class FakeDatabaseOps(DatabaseOps):
    def __init__(self, *, results: list[list[dict]] | None = None):
        """Initialize with predetermined query results.

        Args:
            results: List of result sets (one per query call)
        """
        self._results = results or []
        self._call_count = 0

    def execute_query(self, query: str) -> list[dict]:
        """Return next predetermined result."""
        if self._call_count >= len(self._results):
            return []
        result = self._results[self._call_count]
        self._call_count += 1
        return result


# 4. Test usage
def test_user_query():
    fake_db = FakeDatabaseOps(
        results=[
            [{"id": 1, "name": "Alice"}],  # First query result
            [{"id": 2, "name": "Bob"}],    # Second query result
        ]
    )

    users = get_all_users(fake_db)
    assert len(users) == 1
    assert users[0]["name"] == "Alice"
```

---

This architecture enables fast, maintainable tests while keeping business logic decoupled from external dependencies.
