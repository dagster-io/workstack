# Testing Strategy by Layer

**Read this when**: You need to decide where to add a test, or understand the four-layer testing approach.

## Overview

This codebase uses a **defense-in-depth testing strategy** with four layers:

```
┌─────────────────────────────────────────┐
│  Layer 4: E2E Integration Tests (5%)   │  ← Smoke tests over real system
├─────────────────────────────────────────┤
│  Layer 3: Business Logic Tests (80%)   │  ← Tests over fakes (fast!)
├─────────────────────────────────────────┤
│  Layer 2: Ops Implementation Tests (15%)│  ← Tests WITH mocking
├─────────────────────────────────────────┤
│  Layer 1: Fake Infrastructure Tests    │  ← Verify test doubles work
└─────────────────────────────────────────┘
```

**Philosophy**: Test business logic extensively over fast in-memory fakes. Use real implementations sparingly for integration validation.

**Test distribution guidance**: Aim for 80% Layer 3, 15% Layer 2, 5% Layer 4. Layer 1 tests grow as needed when adding/changing fakes.

## Layer 1: Unit Tests of Fakes

**Purpose**: Verify test infrastructure is reliable.

**Location**: `tests/unit/fakes/test_fake_*.py`

**When to write**: When adding or changing fake implementations.

**Why**: If fakes are broken, all higher-layer tests become unreliable. These tests validate that your test doubles behave correctly.

### Pattern: Test the Fake Itself

```python
def test_fake_gitops_add_worktree(tmp_path: Path) -> None:
    """Verify FakeGitOps tracks worktree additions."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    git_ops = FakeGitOps()
    new_wt = repo_root / "new-wt"

    # Act
    git_ops.add_worktree(repo_root, new_wt, branch="feature")

    # Assert fake tracked the operation
    worktrees = git_ops.list_worktrees(repo_root)
    assert len(worktrees) == 1
    assert worktrees[0].branch == "feature"
    assert (new_wt, "feature") in git_ops.added_worktrees
```

### What to Test

- **State mutations**: Verify operations update internal state correctly
- **Mutation tracking**: Verify read-only properties track operations
- **Error simulation**: Verify fakes can inject errors when configured
- **State queries**: Verify read operations return expected data

### Example Tests

- `tests/unit/fakes/test_fake_gitops.py` - Tests of FakeGitOps
- `tests/unit/fakes/test_fake_graphite_ops.py` - Tests of FakeGraphiteOps
- `tests/unit/fakes/test_fake_github_ops.py` - Tests of FakeGitHubOps

## Layer 2: Integration Tests of Real Ops (with Mocking)

**Purpose**: Get code coverage of real implementations without slow I/O.

**Location**: `tests/integration/test_real_*.py`

**When to write**: When adding or changing real implementations.

**Why**: Ensures code coverage even when underlying systems (subprocess, filesystem, network) are mocked.

### Pattern: Mock External Systems, Verify Commands

```python
def test_real_gitops_add_worktree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify RealGitOps calls correct git command."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Mock subprocess.run
    run_calls: list[list[str]] = []
    def mock_run(cmd: list[str], **kwargs):
        run_calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    git_ops = RealGitOps()
    git_ops.add_worktree(repo_root, tmp_path / "new-wt", branch="feature")

    # Assert correct command was constructed
    assert run_calls[0] == ["git", "worktree", "add", str(tmp_path / "new-wt"), "feature"]
```

### What to Test

- **Command construction**: Verify correct subprocess commands are built
- **Error handling**: Verify exceptions from subprocess are handled correctly
- **Parsing logic**: Verify output parsing works correctly (can use mock output)
- **Edge cases**: Verify handling of unusual inputs or error conditions

### Tools

- `monkeypatch` fixture for mocking `subprocess.run()`, `Path.exists()`, etc.
- Mock return values to simulate various subprocess outputs
- Test error paths by raising exceptions from mocks

### Example Tests

- `tests/integration/test_real_gitops.py` - Tests of RealGitOps with mocking

## Layer 3: Business Logic Tests over Fakes (MAJORITY)

**Purpose**: Test application logic extensively with fast in-memory fakes.

**Location**: `tests/commands/`, `tests/unit/`, `tests/status/`

**When to write**: For EVERY feature and bug fix. This is the default testing layer.

**Why**: Fast, reliable, easy to debug. Tests run in milliseconds, not seconds. This is where most testing happens.

### Pattern: Configure Fakes, Execute Logic, Assert Behavior

```python
def test_status_command_shows_worktrees(tmp_path: Path) -> None:
    """Verify status command displays worktrees correctly."""
    repo_root = tmp_path / "repo"
    wt = tmp_path / "my-wt"
    wt.mkdir(parents=True)

    # Arrange: Configure fake with desired state
    git_ops = FakeGitOps(
        worktrees={repo_root: [WorktreeInfo(path=wt, branch="main")]},
        current_branches={wt: "main"},
    )

    ctx = WorkstackContext.for_test(git_ops=git_ops, cwd=wt)

    # Act: Execute via CliRunner
    runner = CliRunner()
    result = runner.invoke(status_cmd, obj=ctx)

    # Assert: Check output
    assert result.exit_code == 0
    assert "main" in result.output
```

### Key Tools

- **`FakeGitOps`, `FakeGraphiteOps`, `FakeGitHubOps`**: In-memory ops implementations
- **`CliRunner`**: Click's test runner (NOT subprocess) for CLI command testing
- **`WorkstackContext.for_test()`**: Helper to create test context with fakes
- **`tmp_path`**: pytest fixture for real directories when needed
- **`simulated_workstack_env()`**: Isolated filesystem environment with proper cleanup

### What to Test

- **Feature behavior**: Does the feature work as expected?
- **Error handling**: How does code handle error conditions?
- **Edge cases**: Unusual inputs, empty states, boundary conditions
- **Output formatting**: Is CLI output correct and user-friendly?
- **State mutations**: Did operations modify state correctly? (Check fake's tracking properties)

### Performance

Tests over fakes run in **milliseconds**. A typical test suite of 100+ tests runs in seconds, enabling rapid iteration.

### Example Tests

- `tests/commands/test_status_with_fakes.py` - CLI command tests
- `tests/status/test_plan_collector.py` - Business logic unit tests
- `tests/commands/test_create.py` - Feature tests

## Layer 4: End-to-End Integration Tests

**Purpose**: Smoke tests over real system to catch integration issues.

**Location**: `tests/integration/`

**When to write**: Sparingly, for critical user-facing workflows.

**Why**: Catches issues that mocks miss (actual git behavior, filesystem edge cases), but slow and brittle.

### Pattern: Real Systems, Actual Subprocess

```python
def test_create_worktree_e2e(tmp_path: Path) -> None:
    """End-to-end test: create worktree via CLI with real git."""
    repo_root = tmp_path / "repo"

    # Setup: Initialize real git repo
    subprocess.run(["git", "init"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial"], cwd=repo_root, check=True)

    ctx = WorkstackContext(
        git_ops=RealGitOps(),
        cwd=repo_root,
        ...
    )

    runner = CliRunner()
    result = runner.invoke(create_worktree_cmd, ["feature"], obj=ctx)

    # Assert: Real worktree exists
    assert result.exit_code == 0
    worktrees = subprocess.run(
        ["git", "worktree", "list"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "feature" in worktrees
```

### What to Test

- **Critical workflows**: Core user-facing features (create, status, land)
- **Integration points**: Where multiple systems interact (git + graphite + github)
- **Real system quirks**: Behavior that's hard to mock accurately

### Characteristics

- **Slow**: Tests take seconds, not milliseconds
- **Brittle**: Can fail due to environment issues (git not installed, network problems)
- **High value**: Catches real integration bugs that unit tests miss

### When NOT to Use E2E

- ❌ Testing business logic (use Layer 3 instead)
- ❌ Testing error handling (use Layer 3 with fakes configured for errors)
- ❌ Testing output formatting (use Layer 3)
- ❌ Rapid iteration during development (use Layer 3)

Use E2E tests as **final validation**, not primary testing strategy.

## Decision Tree: Where Should My Test Go?

```
┌─ I need to test...
│
├─ A NEW FEATURE or BUG FIX
│  └─> Layer 3: tests/commands/ or tests/unit/ (over fakes) ← START HERE
│
├─ A FAKE IMPLEMENTATION (test infrastructure)
│  └─> Layer 1: tests/unit/fakes/test_fake_*.py
│
├─ A REAL IMPLEMENTATION (code coverage with mocks)
│  └─> Layer 2: tests/integration/test_real_*.py
│
└─ CRITICAL USER WORKFLOW (smoke test)
   └─> Layer 4: tests/integration/ (end-to-end, sparingly)
```

**Default**: When in doubt, write tests over fakes (Layer 3).

## Test Distribution Example

For a typical feature (e.g., "add worktree management"):

- **1-2 fake tests** (Layer 1): Verify `FakeGitOps.add_worktree()` works
- **1-2 real tests** (Layer 2): Verify `RealGitOps.add_worktree()` calls correct git command
- **10-15 business logic tests** (Layer 3): Test feature over fakes
  - Happy path
  - Error conditions (branch exists, path conflicts, etc.)
  - Edge cases (empty repo, detached HEAD, etc.)
  - Output formatting
- **1 E2E test** (Layer 4): Smoke test entire workflow with real git

**Total**: ~20 tests, with 80% over fakes.

## Related Documentation

- `ops-architecture.md` - Understanding the ops layer being tested
- `workflows.md` - Step-by-step guides for adding tests
- `patterns.md` - Common testing patterns (CliRunner, builders, etc.)
- `anti-patterns.md` - What to avoid when writing tests
