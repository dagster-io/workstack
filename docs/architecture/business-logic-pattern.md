# Business Logic Extraction Pattern

## Overview

The Workstack codebase follows a **three-layer architecture** that separates pure business logic from I/O and user interaction concerns. This pattern enables fast unit tests (5-10× faster), better code reusability, and clearer separation of concerns.

## The Three Layers

```
┌─────────────────────────────────────────────────┐
│              CLI Layer (Orchestration)          │
│  Commands in src/workstack/cli/commands/       │
│  - User interaction (click.echo)                │
│  - I/O coordination (filesystem, git, GitHub)   │
│  - Error handling and user feedback             │
│  - Thin orchestrators (~50-150 lines)           │
└─────────────────┬───────────────────────────────┘
                  │ imports & calls
                  ▼
┌─────────────────────────────────────────────────┐
│         Business Logic Layer (Pure Functions)   │
│  Utilities in src/workstack/core/*_utils.py    │
│  - Pure functions operating on data objects     │
│  - No I/O, no side effects                      │
│  - Deterministic and easily testable            │
│  - Reusable across multiple commands            │
└─────────────────┬───────────────────────────────┘
                  │ tested by
                  ▼
┌─────────────────────────────────────────────────┐
│           Test Layer (Fast Unit Tests)          │
│  Tests in tests/core/utils/test_*_utils.py     │
│  - Uses FakeGitOps for dependency injection     │
│  - No filesystem I/O                            │
│  - No subprocess calls                          │
│  - Tests run in ~50-100ms vs ~500ms             │
└─────────────────────────────────────────────────┘
```

## Core Principles

### 1. Pure Business Logic

**Business logic functions must be pure:**

- No filesystem I/O (no `Path.read_text()`, `Path.mkdir()`, etc.)
- No subprocess calls (no `subprocess.run()`)
- No network requests
- No side effects or mutations (except internal state for tracking)
- Deterministic output for given input

**Benefits:**

- Fast testing without I/O overhead
- Easy to reason about behavior
- Reusable across multiple commands
- No dependency on external state

### 2. Data Classes for Immutability

**Use frozen dataclasses for data objects:**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ConsolidationPlan:
    """Immutable plan for workspace consolidation."""
    worktrees_to_remove: list[Path]
    branches_to_delete: list[str]
    target_worktree: Path
    stack_range: tuple[int, int]
```

**Benefits:**

- Clear contracts (no hidden mutations)
- Easy to test (construct once, use many times)
- Type-safe with pyright/mypy

### 3. Thin CLI Orchestrators

**CLI commands should be thin orchestrators:**

- Call business logic functions for decisions
- Perform I/O based on those decisions
- Handle user feedback and error messages
- No complex logic inline

**Example:**

```python
# ❌ WRONG - Business logic mixed with I/O
def create_command(name: str):
    # Inline sanitization logic
    sanitized = name.lower().replace("_", "-")
    # Create worktree
    subprocess.run(["git", "worktree", "add", sanitized])
    click.echo(f"Created {sanitized}")

# ✅ CORRECT - Business logic extracted
def create_command(name: str):
    # Pure business logic (reusable, testable)
    sanitized = sanitize_worktree_name(name)
    # I/O orchestration
    ctx.git_ops.add_worktree(path, branch=sanitized)
    click.echo(f"Created {sanitized}")
```

## Pattern Reference: Naming Utilities

This example demonstrates the complete pattern from business logic to CLI usage.

### Business Logic Module

**File:** `src/workstack/core/naming_utils.py`

```python
"""Pure business logic for naming and sanitization."""

def sanitize_worktree_name(name: str) -> str:
    """Sanitize a worktree name for use as a directory name.

    - Lowercases input
    - Replaces characters outside [A-Za-z0-9.-] with `-`
    - Truncates to 30 characters maximum
    - Returns "work" if result is empty

    Args:
        name: Arbitrary string to sanitize

    Returns:
        Sanitized worktree name (max 30 chars)
    """
    lowered = name.strip().lower()
    replaced = re.sub(r"[^a-z0-9.-]+", "-", lowered.replace("_", "-"))
    collapsed = re.sub(r"-+", "-", replaced)
    trimmed = collapsed.strip("-")
    result = trimmed or "work"

    if len(result) > 30:
        result = result[:30].rstrip("-")

    return result

def ensure_unique_worktree_name(base_name: str, workstacks_dir: Path) -> str:
    """Ensure unique worktree name with date suffix.

    Adds date suffix (-YY-MM-DD) and increments if needed.
    Uses LBYL: checks path.exists() before operations.
    """
    date_suffix = datetime.now().strftime("%y-%m-%d")
    candidate_name = f"{base_name}-{date_suffix}"

    # LBYL: Check before using
    if not (workstacks_dir / candidate_name).exists():
        return candidate_name

    # Find next available number
    counter = 2
    while True:
        versioned_name = f"{base_name}-{counter}-{date_suffix}"
        if not (workstacks_dir / versioned_name).exists():
            return versioned_name
        counter += 1
```

**Key characteristics:**

- ✅ Pure functions (deterministic output)
- ✅ No I/O except existence checks (LBYL pattern)
- ✅ Comprehensive docstrings with examples
- ✅ Type hints for all parameters and returns
- ✅ Single responsibility (naming concerns only)

### CLI Command Usage

**File:** `src/workstack/cli/commands/create.py`

```python
"""Create command - thin orchestrator."""

from workstack.core.naming_utils import (
    sanitize_worktree_name,
    ensure_unique_worktree_name,
    default_branch_for_worktree,
)

@click.command()
@click.argument("name")
def create(ctx: WorkstackContext, name: str) -> None:
    """Create a new worktree."""

    # 1. Call business logic for naming
    sanitized = sanitize_worktree_name(name)
    unique_name = ensure_unique_worktree_name(sanitized, workstacks_dir)
    branch_name = default_branch_for_worktree(unique_name)

    # 2. Perform I/O based on business logic results
    worktree_path = workstacks_dir / unique_name
    ctx.git_ops.add_worktree(repo_root, worktree_path, branch=branch_name)

    # 3. User feedback
    click.echo(f"Created worktree: {click.style(unique_name, fg='cyan', bold=True)}")
    click.echo(f"  Path: {click.style(str(worktree_path), fg='green')}")
```

**Key characteristics:**

- ✅ Thin orchestrator (~50-100 lines)
- ✅ Business logic delegated to utilities
- ✅ I/O clearly separated
- ✅ User feedback handles styling and output

### Unit Tests

**File:** `tests/core/utils/test_naming.py`

```python
"""Fast unit tests for naming utilities."""

import pytest
from workstack.core.naming_utils import (
    sanitize_worktree_name,
    ensure_unique_worktree_name,
)

def test_sanitize_worktree_name_basic() -> None:
    """Test basic sanitization."""
    assert sanitize_worktree_name("My_Feature") == "my-feature"
    assert sanitize_worktree_name("Fix Bug!") == "fix-bug"
    assert sanitize_worktree_name("") == "work"

def test_sanitize_worktree_name_length_limit() -> None:
    """Test 30 character truncation."""
    long_name = "a" * 40
    result = sanitize_worktree_name(long_name)
    assert len(result) == 30
    assert result == "a" * 30

def test_ensure_unique_name_no_conflict(tmp_path: Path) -> None:
    """Test unique name generation without conflicts."""
    workstacks_dir = tmp_path / "workstacks"
    workstacks_dir.mkdir()

    # First call returns base name with date
    result = ensure_unique_worktree_name("feature", workstacks_dir)
    assert result.startswith("feature-")
    assert re.match(r"feature-\d{2}-\d{2}-\d{2}", result)

def test_ensure_unique_name_with_conflict(tmp_path: Path) -> None:
    """Test unique name generation with existing conflict."""
    workstacks_dir = tmp_path / "workstacks"
    workstacks_dir.mkdir()

    # Create conflicting directory
    date_suffix = datetime.now().strftime("%y-%m-%d")
    (workstacks_dir / f"feature-{date_suffix}").mkdir()

    # Should return versioned name
    result = ensure_unique_worktree_name("feature", workstacks_dir)
    assert result == f"feature-2-{date_suffix}"
```

**Key characteristics:**

- ✅ Fast tests (no subprocess, no real git)
- ✅ Uses tmp_path fixture for filesystem isolation
- ✅ Comprehensive edge case coverage
- ✅ Clear test names describing scenarios

## Utility Modules Reference

### Created During Refactoring

| Module                   | Purpose                          | Functions                                                                                                        | Status        |
| ------------------------ | -------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------- |
| `naming_utils.py`        | Name sanitization and uniqueness | `sanitize_worktree_name`, `ensure_unique_worktree_name`, `sanitize_branch_component`, `strip_plan_from_filename` | ✅ Phase 1    |
| `worktree_utils.py`      | Worktree operations and queries  | `get_worktree_branch`, `find_worktree_with_branch`, `filter_non_trunk_branches`, `determine_move_operation`      | ✅ Phase 1, 3 |
| `tree_utils.py`          | Tree building and rendering      | `build_branch_graph_from_metadata`, `filter_graph_to_active_branches`, `build_tree_from_graph`, `render_tree`    | ✅ Phase 2    |
| `display_utils.py`       | Display formatting               | `format_worktree_line`, `format_pr_info`, `get_pr_status_emoji`, `filter_stack_for_worktree`                     | ✅ Phase 2    |
| `consolidation_utils.py` | Workspace consolidation          | `calculate_stack_range`, `identify_removable_worktrees`, `create_consolidation_plan`                             | ✅ Phase 3    |
| `sync_utils.py`          | Sync and PR management           | `identify_deletable_worktrees`                                                                                   | ✅ Phase 4    |
| `init_utils.py`          | Initialization logic             | `detect_root_project_name`, `discover_presets`, `render_config_template`                                         | ✅ Phase 4    |

## Good vs Bad Patterns

### ❌ Anti-Pattern 1: Business Logic in CLI Commands

```python
# BAD: Logic mixed with I/O
@click.command()
def consolidate(ctx: WorkstackContext) -> None:
    stack = ctx.graphite_ops.get_stack(ctx.cwd)

    # Complex business logic inline
    removable = []
    for i, branch in enumerate(stack):
        if i > 0 and i < len(stack) - 1:
            wt = find_worktree_for_branch(branch)
            if wt and wt != ctx.cwd and not wt.is_root:
                removable.append(wt)

    # More inline logic for removal...
    for wt in removable:
        ctx.git_ops.remove_worktree(wt.path)
```

**Problems:**

- Cannot test logic without full CLI invocation
- Cannot reuse logic in other commands
- Hard to test edge cases
- Complex conditional logic in orchestrator

### ✅ Correct Pattern: Extracted Business Logic

```python
# GOOD: Business logic extracted to utility module

# In consolidation_utils.py
def identify_removable_worktrees(
    stack: list[str],
    current_worktree: Path,
    root_worktree: Path,
    worktree_mapping: dict[str, Path],
) -> list[Path]:
    """Identify worktrees safe to remove during consolidation.

    Pure function - no I/O, easily testable.
    """
    removable = []
    for i, branch in enumerate(stack):
        # Skip first and last (source and target)
        if i == 0 or i == len(stack) - 1:
            continue

        if branch not in worktree_mapping:
            continue

        wt_path = worktree_mapping[branch]

        # Never remove current or root worktree
        if wt_path == current_worktree or wt_path == root_worktree:
            continue

        removable.append(wt_path)

    return removable

# In consolidate.py CLI command
@click.command()
def consolidate(ctx: WorkstackContext) -> None:
    """Consolidate workspace - thin orchestrator."""
    stack = ctx.graphite_ops.get_stack(ctx.cwd)
    worktrees = ctx.git_ops.list_worktrees(ctx.cwd)
    mapping = {wt.branch: wt.path for wt in worktrees if wt.branch}

    # Call pure business logic
    removable = identify_removable_worktrees(
        stack=stack,
        current_worktree=ctx.cwd,
        root_worktree=next(wt.path for wt in worktrees if wt.is_root),
        worktree_mapping=mapping,
    )

    # Perform I/O based on results
    for wt in removable:
        ctx.git_ops.remove_worktree(wt)
        click.echo(f"Removed: {wt.name}")
```

**Benefits:**

- ✅ `identify_removable_worktrees()` is pure and testable
- ✅ Can test edge cases without real git operations
- ✅ Reusable in other commands
- ✅ CLI command is thin orchestrator

### ❌ Anti-Pattern 2: Duplicate Logic Across Commands

```python
# BAD: Duplicate sanitization in multiple commands

# In create.py
def create(name: str):
    sanitized = name.lower().replace("_", "-")[:30]
    # ... create worktree ...

# In move.py
def move(source: str, target: str):
    sanitized_target = target.lower().replace("_", "-")[:30]
    # ... move worktree ...

# In rename.py
def rename(old_name: str, new_name: str):
    sanitized_new = new_name.lower().replace("_", "-")[:30]
    # ... rename worktree ...
```

**Problems:**

- Logic duplicated 3 times
- Inconsistent behavior if one changes
- Hard to maintain
- No single source of truth

### ✅ Correct Pattern: Shared Utility Functions

```python
# GOOD: Shared utility with single implementation

# In naming_utils.py
def sanitize_worktree_name(name: str) -> str:
    """Sanitize worktree name (max 30 chars).

    Single source of truth for sanitization.
    """
    lowered = name.strip().lower()
    replaced = re.sub(r"[^a-z0-9.-]+", "-", lowered.replace("_", "-"))
    collapsed = re.sub(r"-+", "-", replaced)
    trimmed = collapsed.strip("-")
    result = trimmed or "work"

    if len(result) > 30:
        result = result[:30].rstrip("-")

    return result

# In create.py, move.py, rename.py
from workstack.core.naming_utils import sanitize_worktree_name

def create(name: str):
    sanitized = sanitize_worktree_name(name)
    # ... create worktree ...
```

**Benefits:**

- ✅ Single source of truth
- ✅ Consistent behavior across all commands
- ✅ Easy to test comprehensively once
- ✅ Easy to enhance with new logic

### ❌ Anti-Pattern 3: Testing with Real Git Operations

```python
# BAD: Slow tests with real git

def test_consolidate_removes_worktrees(tmp_path: Path) -> None:
    """Test consolidation (SLOW - uses real git)."""
    repo = tmp_path / "repo"
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "worktree", "add", "wt1", "-b", "feat1"], cwd=repo, check=True)
    subprocess.run(["git", "worktree", "add", "wt2", "-b", "feat2"], cwd=repo, check=True)

    # Test the command
    runner = CliRunner()
    result = runner.invoke(consolidate_cmd, obj=create_context_with_real_git(repo))

    # Verify (slow filesystem operations)
    assert not (repo / "wt1").exists()
```

**Problems:**

- Slow (500ms+ per test)
- Requires real git installation
- Hard to test edge cases (detached HEAD, corrupted git state)
- Tests become flaky

### ✅ Correct Pattern: Fast Tests with Fakes

```python
# GOOD: Fast tests with FakeGitOps

def test_identify_removable_worktrees() -> None:
    """Test removal identification (FAST - no I/O)."""
    stack = ["main", "feat1", "feat2", "feat3"]
    current = Path("/repo")
    root = Path("/repo")
    mapping = {
        "feat1": Path("/workstacks/feat1"),
        "feat2": Path("/workstacks/feat2"),
        "feat3": Path("/workstacks/feat3"),
    }

    # Pure function - no I/O needed
    removable = identify_removable_worktrees(
        stack=stack,
        current_worktree=current,
        root_worktree=root,
        worktree_mapping=mapping,
    )

    # Verify business logic
    assert removable == [Path("/workstacks/feat1"), Path("/workstacks/feat2")]
    assert Path("/workstacks/feat3") not in removable  # Target kept
```

**Benefits:**

- ✅ Fast (~50-100ms per test)
- ✅ No git installation required
- ✅ Easy to test edge cases
- ✅ Deterministic and reliable

## Migration Checklist

When refactoring a CLI command to follow this pattern:

- [ ] Identify business logic mixed with I/O
- [ ] Extract pure functions to `*_utils.py` module
- [ ] Add comprehensive type hints
- [ ] Add docstrings with examples
- [ ] Write unit tests in `tests/core/utils/test_*_utils.py`
- [ ] Use `FakeGitOps` for testing (no real git)
- [ ] Update CLI command to call utility functions
- [ ] Verify CLI command is now a thin orchestrator
- [ ] Run `/ensure-ci` to validate
- [ ] Check test performance improvement with `pytest --durations=10`

## Success Metrics

### Quantitative

Across the four phases of refactoring:

- **Test Speed**: 5-10× faster per test (from ~500ms to ~50-100ms)
- **Code Reduction**: ~30-40% in command files
- **Test Coverage**: Increased from ~85% to >90%
- **Duplication**: Zero duplicate business logic across commands
- **Test Count**: Added 70+ new unit tests for pure functions

### Qualitative

- Clear separation of concerns (CLI/Business/Test layers)
- Business logic reusable across multiple commands
- Easier to test edge cases with pure functions
- Consistent patterns across entire codebase
- Improved maintainability and readability

## Related Documentation

- [docs/agent/testing.md](../agent/testing.md) - Comprehensive testing patterns with fakes
- [docs/agent/glossary.md](../agent/glossary.md) - Project terminology
- Load `dignified-python` skill for Python coding standards
