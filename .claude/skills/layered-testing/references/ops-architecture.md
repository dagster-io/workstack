# Ops Layer Architecture

**Read this when**: You need to understand or modify the ops layer (the thin wrapper interfaces over external state).

## Overview

**Naming note**: "Ops" is an arbitrary name used in this codebase. These classes are also called **adapters**, **gateways**, or **providers** in other contexts. The pattern matters more than the name.

## What Are Ops Classes?

**Ops classes are thin wrappers around heavyweight external APIs** that:

- Touch external state (filesystem, git, GitHub API, Graphite CLI)
- Could be slow (network calls, subprocess execution)
- Could fail periodically (API rate limits, network issues)
- Are difficult to test directly

## The Four Implementations

Every ops interface has **four implementations**:

### 1. Abstract Interface (ABC)

Defines the contract all implementations must follow.

**Example**: `GitOps` (`src/workstack/core/gitops.py`)

```python
from abc import ABC, abstractmethod

class GitOps(ABC):
    """Thin wrapper over git operations."""

    @abstractmethod
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in repository."""

    @abstractmethod
    def add_worktree(
        self, repo_root: Path, path: Path, *, branch: str | None
    ) -> None:
        """Add a new worktree."""

    # ... more methods
```

**Key characteristics**:

- Uses `ABC` (not `Protocol`)
- All methods are `@abstractmethod`
- Contains ONLY runtime operations (no test setup methods)
- May have concrete helper methods (all implementations inherit)

### 2. Real Implementation

Calls actual external systems (subprocess, filesystem, API).

**Example**: `RealGitOps` (`src/workstack/core/gitops.py`)

```python
class RealGitOps(GitOps):
    """Real git operations via subprocess."""

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """Execute: git worktree list --porcelain"""
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,  # ← Always use check=True
        )
        return self._parse_worktree_output(result.stdout)

    def add_worktree(
        self, repo_root: Path, path: Path, *, branch: str | None
    ) -> None:
        """Execute: git worktree add <path> <branch>"""
        cmd = ["git", "worktree", "add", str(path)]
        if branch:
            cmd.append(branch)
        subprocess.run(cmd, cwd=repo_root, check=True)
```

**Key characteristics**:

- Uses `subprocess.run()` with `check=True`
- Uses `pathlib.Path` for all filesystem operations
- LBYL: checks `.exists()` before path operations
- Lets exceptions bubble up (no try/except for control flow)

### 3. Fake Implementation

In-memory simulation for fast testing.

**Example**: `FakeGitOps` (`tests/fakes/gitops.py`)

```python
class FakeGitOps(GitOps):
    """In-memory git simulation for testing."""

    def __init__(
        self,
        *,
        worktrees: dict[Path, list[WorktreeInfo]] | None = None,
        current_branches: dict[Path, str] | None = None,
    ) -> None:
        # Mutable state (private)
        self._worktrees = worktrees or {}
        self._current_branches = current_branches or {}

        # Mutation tracking (private, accessed via properties)
        self._added_worktrees: list[tuple[Path, str | None]] = []
        self._deleted_branches: list[str] = []

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """Return in-memory worktrees."""
        return self._worktrees.get(repo_root, []).copy()

    def add_worktree(
        self, repo_root: Path, path: Path, *, branch: str | None
    ) -> None:
        """Update in-memory state and create directory."""
        if repo_root not in self._worktrees:
            self._worktrees[repo_root] = []

        wt_info = WorktreeInfo(path=path, branch=branch, ...)
        self._worktrees[repo_root].append(wt_info)

        # Track mutation for test assertions
        self._added_worktrees.append((path, branch))

        # May create real directories for filesystem integration
        path.mkdir(parents=True, exist_ok=True)

    @property
    def added_worktrees(self) -> list[tuple[Path, str | None]]:
        """Read-only access for test assertions."""
        return self._added_worktrees.copy()
```

**Key characteristics**:

- **Constructor injection**: All initial state via keyword arguments
- **In-memory storage**: Dictionaries, lists for state
- **Mutation tracking**: Read-only properties for assertions
- **Fast**: No subprocess, no I/O (except minimal directory creation)
- **Simulation**: May mimic real behavior (e.g., checking branch conflicts)

**Mutation tracking pattern**:

```python
# In test:
git_ops = FakeGitOps()
git_ops.remove_worktree(repo_root, path, force=False)

# Assert operation was called
assert (path, False) in git_ops.removed_worktrees
```

### 4. Dry-Run Wrapper

Intercepts write operations, delegates reads.

**Example**: `DryRunGitOps` (`src/workstack/core/gitops.py`)

```python
class DryRunGitOps(GitOps):
    """Wrapper that prints instead of executing writes."""

    def __init__(self, git_ops: GitOps) -> None:
        self._git_ops = git_ops  # Wrap any GitOps implementation

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """Delegate read operation."""
        return self._git_ops.list_worktrees(repo_root)

    def add_worktree(
        self, repo_root: Path, path: Path, *, branch: str | None
    ) -> None:
        """Print instead of executing."""
        click.echo(f"[DRY RUN] Would add worktree: {path} (branch: {branch})")
        # Does NOT call self._git_ops.add_worktree()
```

**Key characteristics**:

- **Wrapper pattern**: Accepts any `GitOps` implementation
- **Read operations**: Delegate to wrapped implementation
- **Write operations**: Print `[DRY RUN]` message, don't execute
- **Testing**: Verify operations are intercepted correctly

## When to Add/Change Ops Methods

### Adding a Method

**If you need to add a method to an ops interface:**

1. Add `@abstractmethod` to ABC interface (e.g., `GitOps`)
2. Implement in real class (e.g., `RealGitOps`) with subprocess/I/O
3. Implement in fake class (e.g., `FakeGitOps`) with in-memory state
4. Add handler in dry-run wrapper (e.g., `DryRunGitOps`)
5. Write unit test of fake implementation (`tests/unit/fakes/test_fake_gitops.py`)
6. Write integration test of real implementation (`tests/integration/test_real_gitops.py`)

### Changing an Interface

**If you need to change an interface:**

- Update all four implementations above
- Update all tests that use the changed method
- Update any business logic that calls the method

## Existing Ops Interfaces

**File locations** in `src/workstack/core/`:

- **`gitops.py`**: Git operations (worktrees, branches, commits)
  - `GitOps` (ABC), `RealGitOps`, `DryRunGitOps`
  - Fakes: `tests/fakes/gitops.py`

- **`graphite_ops.py`**: Graphite CLI operations (stacks, sync, submit)
  - `GraphiteOps` (ABC), `RealGraphiteOps`, `DryRunGraphiteOps`
  - Fakes: `tests/fakes/graphite_ops.py`

- **`github_ops.py`**: GitHub API operations (PRs, status, mergeability)
  - `GitHubOps` (ABC), `RealGitHubOps`, `DryRunGitHubOps`
  - Fakes: `tests/fakes/github_ops.py`

## Design Principles

### Keep Ops Thin

**Ops classes should NOT contain business logic**. Push complexity to the business layer.

```python
# ❌ WRONG: Business logic in ops class
class RealGitOps(GitOps):
    def smart_branch_selection(self, repo_root: Path) -> str:
        """Complex logic to select best branch."""
        worktrees = self.list_worktrees(repo_root)
        # ... 50 lines of logic ...
        return best_branch

# ✅ CORRECT: Thin ops, logic in business layer
class RealGitOps(GitOps):
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """Just wrap git command."""
        result = subprocess.run(["git", "worktree", "list", ...], check=True)
        return self._parse_output(result.stdout)

# Business logic layer:
def select_best_branch(git_ops: GitOps, repo_root: Path) -> str:
    """Complex logic over thin ops."""
    worktrees = git_ops.list_worktrees(repo_root)
    # ... 50 lines of logic ...
    return best_branch
```

**Why**: Thin ops are easier to fake, easier to test, easier to understand.

### Fakes Should Be In-Memory

**Fakes should avoid I/O operations** (except minimal directory creation).

```python
# ❌ WRONG: Fake performs I/O
class FakeGitOps(GitOps):
    def get_branch_name(self, path: Path) -> str:
        # Reading real files defeats the purpose of fakes!
        return (path / ".git" / "HEAD").read_text()

# ✅ CORRECT: Fake uses in-memory state
class FakeGitOps(GitOps):
    def __init__(self, *, current_branches: dict[Path, str] | None = None):
        self._current_branches = current_branches or {}

    def get_branch_name(self, path: Path) -> str:
        return self._current_branches.get(path, "main")
```

**Exception**: Fakes may create real directories (like `add_worktree()`), but should not read/write files.

## Related Documentation

- `testing-strategy.md` - How to test ops classes at different layers
- `workflows.md` - Step-by-step guide for adding ops methods
- `patterns.md` - Constructor injection and mutation tracking patterns
