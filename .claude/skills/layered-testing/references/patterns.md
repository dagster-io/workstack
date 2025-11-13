# Testing Patterns

**Read this when**: You need to implement a specific pattern (constructor injection, mutation tracking, CliRunner, builders, etc.).

## Overview

This document covers common patterns used throughout the test suite. Each pattern includes examples and explanations.

## Constructor Injection for Fakes

**Pattern**: Pass all initial state via constructor keyword arguments.

### Implementation

```python
class FakeGitOps(GitOps):
    def __init__(
        self,
        *,
        worktrees: dict[Path, list[WorktreeInfo]] | None = None,
        current_branches: dict[Path, str] | None = None,
        branches: set[str] | None = None,
    ) -> None:
        # Initialize mutable state from constructor
        self._worktrees = worktrees or {}
        self._current_branches = current_branches or {}
        self._branches = branches or set()

        # Initialize mutation tracking
        self._deleted_branches: list[str] = []
        self._added_worktrees: list[tuple[Path, str | None]] = []
```

### Usage in Tests

```python
# ✅ CORRECT: Constructor injection
def test_with_constructor_injection(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    wt = tmp_path / "wt"

    git_ops = FakeGitOps(
        worktrees={repo_root: [WorktreeInfo(path=wt, branch="main")]},
        current_branches={wt: "main"},
        branches={"main", "feature"},
    )

    # Fake is fully configured, ready to use
    assert len(git_ops.list_worktrees(repo_root)) == 1
```

### Anti-Pattern

```python
# ❌ WRONG: Mutation after construction
def test_with_mutation() -> None:
    git_ops = FakeGitOps()

    # Don't mutate private state directly!
    git_ops._worktrees[repo_root] = [...]  # Bypasses encapsulation
    git_ops._branches.add("main")  # Fragile, couples to implementation
```

### Why Constructor Injection?

**Benefits**:

- **Declarative**: Test setup is explicit and readable
- **Encapsulation**: Doesn't expose private implementation details
- **Maintainable**: Changes to fake internals don't break tests
- **Clear intent**: Constructor signature documents what can be configured

**Rule**: If tests need to set up state, add a constructor parameter. Don't mutate private fields.

---

## Mutation Tracking Properties

**Pattern**: Track operations in private lists/dicts, expose via read-only properties.

### Implementation

```python
class FakeGitOps(GitOps):
    def __init__(self) -> None:
        # Private mutation tracking
        self._deleted_branches: list[str] = []
        self._added_worktrees: list[tuple[Path, str | None]] = []
        self._removed_worktrees: list[tuple[Path, bool]] = []

    def delete_branch(self, repo_root: Path, branch: str) -> None:
        """Delete a branch."""
        # Update state
        self._branches.discard(branch)

        # Track mutation
        self._deleted_branches.append(branch)

    def add_worktree(
        self, repo_root: Path, path: Path, *, branch: str | None
    ) -> None:
        """Add a worktree."""
        # Update state
        if repo_root not in self._worktrees:
            self._worktrees[repo_root] = []
        self._worktrees[repo_root].append(WorktreeInfo(path=path, branch=branch))

        # Track mutation
        self._added_worktrees.append((path, branch))

    @property
    def deleted_branches(self) -> list[str]:
        """Read-only access for test assertions."""
        return self._deleted_branches.copy()  # Return copy to prevent tampering

    @property
    def added_worktrees(self) -> list[tuple[Path, str | None]]:
        """Read-only access for test assertions."""
        return self._added_worktrees.copy()
```

### Usage in Tests

```python
def test_mutation_tracking(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    wt = tmp_path / "wt"

    git_ops = FakeGitOps(branches={"feature", "bugfix"})

    # Perform operations
    git_ops.delete_branch(repo_root, "feature")
    git_ops.add_worktree(repo_root, wt, branch="bugfix")

    # Assert mutations were tracked
    assert "feature" in git_ops.deleted_branches
    assert (wt, "bugfix") in git_ops.added_worktrees
```

### Why Track Mutations?

**Benefits**:

- **Verification**: Tests can verify operations were called
- **Ordering**: Lists preserve call order for sequential assertions
- **Arguments**: Track arguments passed to operations
- **Debugging**: Easy to see what operations were performed

**Rule**: For every write operation, track the mutation in a read-only property.

---

## Using CliRunner for CLI Tests

**Pattern**: Use Click's `CliRunner` for testing CLI commands, NOT subprocess.

### Basic Usage

```python
from click.testing import CliRunner

def test_status_command(tmp_path: Path) -> None:
    """Test CLI command with CliRunner."""
    # Arrange: Set up fakes
    git_ops = FakeGitOps(...)
    ctx = WorkstackContext.for_test(git_ops=git_ops, cwd=tmp_path)

    # Act: Invoke command via CliRunner
    runner = CliRunner()
    result = runner.invoke(status_cmd, obj=ctx)

    # Assert: Check exit code and output
    assert result.exit_code == 0
    assert "expected output" in result.output
```

### With Arguments

```python
def test_command_with_args(tmp_path: Path) -> None:
    """Test command that takes arguments."""
    runner = CliRunner()
    ctx = WorkstackContext.for_test(...)

    # Pass arguments as list
    result = runner.invoke(create_cmd, ["feature-branch", "--stack"], obj=ctx)

    assert result.exit_code == 0
```

### With Isolated Filesystem

```python
def test_command_with_files() -> None:
    """Test command that creates files."""
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Command runs in temporary directory
        result = runner.invoke(init_cmd)

        assert result.exit_code == 0
        assert Path(".workstack").exists()
```

### Capturing Exceptions

```python
def test_command_error() -> None:
    """Test command that raises an exception."""
    runner = CliRunner()

    # CliRunner catches exceptions and sets exit_code
    result = runner.invoke(buggy_cmd, catch_exceptions=True)

    assert result.exit_code != 0
    assert "Error:" in result.output
```

### Why CliRunner (NOT subprocess)?

**Performance**:

- CliRunner: **milliseconds** per test
- Subprocess: **seconds** per test
- **~100x faster** with CliRunner

**Better debugging**:

- Direct access to exceptions
- No shell interpretation issues
- Easier to debug with breakpoints

**Rule**: Always use `CliRunner` for CLI tests. Only use subprocess for true end-to-end integration tests.

**See**: `docs/agent/testing.md#cli-testing-patterns` for detailed comparison.

---

## Builder Patterns for Complex Scenarios

**Pattern**: Use builder pattern to construct complex test scenarios declaratively.

### Implementation

```python
class WorktreeScenario:
    """Builder for complex worktree test scenarios."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.worktrees: dict[Path, list[WorktreeInfo]] = {base_path: []}
        self.current_branches: dict[Path, str] = {}
        self.prs: dict[str, PRInfo] = {}
        self.stacks: dict[str, list[str]] = {}

    def with_main_branch(self) -> WorktreeScenario:
        """Add main branch in root worktree."""
        root_wt = WorktreeInfo(
            path=self.base_path,
            branch="main",
            head="abc123",
            is_bare=False,
            is_detached=False,
        )
        self.worktrees[self.base_path] = [root_wt]
        self.current_branches[self.base_path] = "main"
        return self

    def with_feature_branch(
        self, name: str, *, pr_number: int | None = None
    ) -> WorktreeScenario:
        """Add a feature branch worktree."""
        path = self.base_path / "workstacks" / name
        wt_info = WorktreeInfo(
            path=path,
            branch=name,
            head="def456",
            is_bare=False,
            is_detached=False,
        )
        if self.base_path not in self.worktrees:
            self.worktrees[self.base_path] = []
        self.worktrees[self.base_path].append(wt_info)
        self.current_branches[path] = name

        if pr_number:
            self.with_pr(name, number=pr_number)

        return self

    def with_pr(
        self, branch: str, *, number: int, title: str = "Test PR"
    ) -> WorktreeScenario:
        """Add a PR for a branch."""
        self.prs[branch] = PRInfo(
            number=number,
            title=title,
            state="OPEN",
            url=f"https://github.com/user/repo/pull/{number}",
        )
        return self

    def with_stack(self, branches: list[str]) -> WorktreeScenario:
        """Add a Graphite stack."""
        for i, branch in enumerate(branches):
            if i > 0:
                parent = branches[i - 1]
                self.stacks[branch] = [parent]
        return self

    def build(self) -> WorkstackContext:
        """Build context with configured state."""
        git_ops = FakeGitOps(
            worktrees=self.worktrees,
            current_branches=self.current_branches,
        )
        github_ops = FakeGitHubOps(prs=self.prs)
        graphite_ops = FakeGraphiteOps(stacks=self.stacks)

        return WorkstackContext.for_test(
            git_ops=git_ops,
            github_ops=github_ops,
            graphite_ops=graphite_ops,
            cwd=self.base_path,
        )
```

### Usage in Tests

```python
def test_complex_scenario(tmp_path: Path) -> None:
    """Test with multiple worktrees, PRs, and stacks."""
    # Declarative, fluent API
    ctx = (
        WorktreeScenario(tmp_path)
        .with_main_branch()
        .with_feature_branch("feature-1", pr_number=123)
        .with_feature_branch("feature-2", pr_number=124)
        .with_stack(["main", "feature-1", "feature-2"])
        .build()
    )

    runner = CliRunner()
    result = runner.invoke(status_cmd, obj=ctx)

    assert result.exit_code == 0
    assert "#123" in result.output
    assert "#124" in result.output
    assert "Stack:" in result.output
```

### When to Use Builders

**Use builders when**:

- Setting up complex multi-component scenarios
- Same scenario reused across multiple tests
- Test setup obscures test intent
- Many optional configurations

**Don't use builders when**:

- Simple single-component setup
- Setup is only used once
- Constructor injection is sufficient

### Benefits

**Readability**: Fluent API makes test intent clear
**Reusability**: Share builder across test suite
**Maintainability**: Changes to setup logic in one place
**Flexibility**: Mix and match components as needed

**Example builder in codebase**: `tests/integration/scenario_builder.py`

---

## Simulated Environment Pattern

**Pattern**: Use `simulated_workstack_env()` for isolated filesystem tests.

### Implementation

```python
@contextmanager
def simulated_workstack_env(runner: CliRunner):
    """Create isolated test environment with proper cleanup."""
    with runner.isolated_filesystem():
        # Setup test environment
        repo_root = Path.cwd() / "repo"
        repo_root.mkdir()

        workstacks_dir = Path.cwd() / "workstacks"
        workstacks_dir.mkdir()

        env = SimulatedEnv(
            cwd=Path.cwd(),
            repo_root=repo_root,
            workstacks_dir=workstacks_dir,
        )

        try:
            yield env
        finally:
            # Cleanup happens automatically with isolated_filesystem()
            pass
```

### Usage

```python
def test_with_simulated_env() -> None:
    """Test in isolated environment."""
    runner = CliRunner()

    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps()
        ctx = WorkstackContext.for_test(
            git_ops=git_ops,
            cwd=env.cwd,  # Use simulated cwd
        )

        result = runner.invoke(status_cmd, obj=ctx)
        assert result.exit_code == 0
```

### Why Simulated Environments?

**Benefits**:

- **Isolation**: Each test runs in clean temporary directory
- **Safety**: No risk of polluting real filesystem
- **Cleanup**: Automatic cleanup after test
- **Realistic**: Tests can create real files/directories

**Rule**: Use `simulated_workstack_env()` for tests that create files. Use `tmp_path` for simpler cases.

---

## Error Injection Pattern

**Pattern**: Configure fakes to raise errors for testing error handling.

### Implementation in Fake

```python
class FakeGraphiteOps(GraphiteOps):
    def __init__(
        self,
        *,
        sync_raises: Exception | None = None,
        submit_branch_raises: Exception | None = None,
    ) -> None:
        self._sync_raises = sync_raises
        self._submit_branch_raises = submit_branch_raises

    def sync(self) -> None:
        """Sync Graphite stack."""
        if self._sync_raises:
            raise self._sync_raises

        # Normal sync logic
        ...

    def submit_branch(self, branch: str) -> None:
        """Submit branch for PR."""
        if self._submit_branch_raises:
            raise self._submit_branch_raises

        # Normal submit logic
        ...
```

### Usage in Tests

```python
def test_handles_graphite_sync_error(tmp_path: Path) -> None:
    """Test error handling when Graphite sync fails."""
    # Configure fake to raise error
    graphite_ops = FakeGraphiteOps(
        sync_raises=subprocess.CalledProcessError(
            1, ["gt", "sync"], stderr="error: conflict detected"
        )
    )

    ctx = WorkstackContext.for_test(graphite_ops=graphite_ops, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(sync_cmd, obj=ctx)

    # Assert error is handled gracefully
    assert result.exit_code != 0
    assert "conflict detected" in result.output
```

### Benefits

**Fast**: No need for real system to fail
**Reliable**: Errors are deterministic, not flaky
**Complete**: Test all error paths, even rare ones
**Safe**: No risk of corrupting real state

**Rule**: Add error injection parameters for operations that can fail.

---

## Dry-Run Testing Pattern

**Pattern**: Verify operations are intercepted, not executed.

### Implementation

```python
def test_remove_worktree_dry_run(tmp_path: Path) -> None:
    """Verify --dry-run doesn't remove worktree."""
    repo_root = tmp_path / "repo"
    wt_path = tmp_path / "wt"

    # Arrange: Set up fake with worktree
    git_ops = FakeGitOps(
        worktrees={repo_root: [WorktreeInfo(path=wt_path, branch="feature")]},
    )
    ctx = WorkstackContext.for_test(git_ops=git_ops, cwd=tmp_path)

    # Act: Invoke with --dry-run
    runner = CliRunner()
    result = runner.invoke(remove_worktree_cmd, ["--dry-run"], obj=ctx)

    # Assert: Operation was NOT executed
    assert len(git_ops.removed_worktrees) == 0

    # Assert: Dry-run message was printed
    assert "[DRY RUN]" in result.output
    assert "Would remove worktree" in result.output

    # Assert: Worktree still exists (wasn't removed)
    worktrees = git_ops.list_worktrees(repo_root)
    assert len(worktrees) == 1
```

### Pattern

1. **Arrange**: Set up fake with initial state
2. **Act**: Invoke command with `--dry-run` flag
3. **Assert**:
   - Mutation tracking shows operation NOT executed
   - Output contains `[DRY RUN]` message
   - State unchanged (operation didn't happen)

### Benefits

**Verifies**:

- Dry-run wrapper correctly intercepts operations
- Messages accurately describe what would happen
- No side effects occur in dry-run mode

---

## Related Documentation

- `workflows.md` - Step-by-step guides for using these patterns
- `testing-strategy.md` - Which layer to test at
- `ops-architecture.md` - Understanding fakes and ops layer
- `anti-patterns.md` - What to avoid
