# Testing Fake Implementations

## Purpose

Fake implementations are test infrastructure that simulate real behavior without external dependencies (git, filesystem, network). These fakes need their own validation through dedicated unit tests.

**Why test fakes separately:**

- Fakes are test infrastructure - they need validation just like production code
- Catches behavior drift before it affects actual tests
- Documents expected fake behavior for maintainers
- Fast, isolated tests without subprocess overhead
- Validates mutation tracking properties independently

## ABC Interface Contract

All operations use ABC (Abstract Base Class) pattern:

- Both real and fake implementations must implement all abstract methods
- Python enforces method signatures at runtime
- However, ABCs only validate INTERFACE, not BEHAVIOR

**This is why we need fake tests:** ABCs guarantee method signatures exist, but cannot guarantee the fake's behavior matches the real implementation's behavior.

## Test File Structure

Every fake implementation should have a corresponding test file in `tests/unit/fakes/`:

| Fake Implementation | Test File                      | Test Count | Status      |
| ------------------- | ------------------------------ | ---------- | ----------- |
| FakeGitOps          | test_fake_gitops.py            | 31         | ✅ Complete |
| FakeGlobalConfigOps | test_fake_global_config_ops.py | 6          | ✅ Complete |
| FakeGitHubOps       | test_fake_github_ops.py        | 10         | ✅ Complete |
| FakeGraphiteOps     | test_fake_graphite_ops.py      | 18         | ✅ Complete |
| FakeShellOps        | test_fake_shell_ops.py         | 9          | ✅ Complete |
| **Total**           | **5 test files**               | **74**     | ✅ Complete |

## Standard Test Pattern

Each fake test file should validate:

### 1. Initialization Tests

Verify empty state and pre-configured state work correctly.

```python
def test_fake_ops_initialization() -> None:
    """Test that fake initializes with empty state."""
    ops = FakeOps()
    assert ops.some_method() == expected_default
```

### 2. Method Behavior Tests

One test per abstract method to verify it returns correct pre-configured data.

```python
def test_fake_ops_method_returns_configured_data() -> None:
    """Test that method returns pre-configured value."""
    ops = FakeOps(some_data={"key": "value"})
    result = ops.get_some_data("key")
    assert result == "value"
```

### 3. Mutation Tracking Tests

Verify mutation tracking properties update correctly when operations modify state.

```python
def test_fake_ops_tracks_mutations() -> None:
    """Test that fake tracks state changes."""
    ops = FakeOps()
    ops.perform_operation("target")

    # Verify mutation tracking property updated
    assert "target" in ops.performed_operations
```

### 4. State Management Tests

Verify state changes are visible to subsequent method calls.

```python
def test_fake_ops_state_persistence() -> None:
    """Test that state changes persist across calls."""
    ops = FakeOps()
    ops.set_value("key", "initial")

    # Modify state
    ops.update_value("key", "updated")

    # Verify change is visible
    assert ops.get_value("key") == "updated"
```

### 5. Edge Case Tests

Handle missing keys, invalid inputs, empty state gracefully.

```python
def test_fake_ops_missing_key() -> None:
    """Test behavior when key not configured."""
    ops = FakeOps()
    result = ops.get_value("nonexistent")
    assert result is None  # or raises exception, depending on contract
```

## Coverage Requirements

Every fake test file MUST validate:

✅ All abstract methods return correct pre-configured data
✅ Mutation tracking properties work as documented
✅ State changes visible to subsequent calls
✅ Edge cases handled gracefully (no crashes)
✅ Constructor parameters configure initial state correctly

## High-Risk Patterns Requiring Extra Attention

### Complex Parsing Methods

Methods with >30 LOC in real implementation need comprehensive testing:

**Example: `get_file_status` (GitOps, 35 LOC parsing)**

- Real implementation parses `git status --porcelain` output
- Interprets status codes: `??` (untracked), ` M` (modified), `M ` (staged), `MM` (both)
- Fake returns pre-configured tuples - must match real behavior exactly
- Used heavily in status display - bugs are user-visible

**Test pattern:**

```python
def test_fake_gitops_get_file_status_empty() -> None:
    """Test get_file_status with no changes."""
    git_ops = FakeGitOps(file_statuses={Path("/repo"): ([], [], [])})
    staged, modified, untracked = git_ops.get_file_status(Path("/repo"))
    assert staged == []
    assert modified == []
    assert untracked == []

def test_fake_gitops_get_file_status_mixed() -> None:
    """Test get_file_status with all change types."""
    git_ops = FakeGitOps(
        file_statuses={Path("/repo"): (["a.txt"], ["b.txt"], ["c.txt"])}
    )
    staged, modified, untracked = git_ops.get_file_status(Path("/repo"))
    assert staged == ["a.txt"]
    assert modified == ["b.txt"]
    assert untracked == ["c.txt"]
```

### Stateful Operations

Operations that modify internal state need both behavior and mutation tracking tests:

**Example: `add_worktree` (GitOps)**

```python
def test_fake_gitops_add_worktree(tmp_path: Path) -> None:
    """Test add_worktree updates state and tracks mutation."""
    repo_root = tmp_path / "repo"
    git_ops = FakeGitOps()

    new_wt = repo_root / "new-wt"
    git_ops.add_worktree(repo_root, new_wt, branch="new-branch")

    # Test state mutations
    worktrees = git_ops.list_worktrees(repo_root)
    assert len(worktrees) == 1

    # Test mutation tracking
    assert (new_wt, "new-branch") in git_ops.added_worktrees

    # Test filesystem side effect
    assert new_wt.exists()
```

## Examples from Existing Tests

### Comprehensive Coverage: test_fake_global_config_ops.py

Shows pattern for testing all configuration fields:

```python
def test_fake_global_config_ops_initial_state() -> None:
    """All getters reflect the constructor-provided state."""
    ops = FakeGlobalConfigOps(
        workstacks_root=Path("/ws"),
        use_graphite=True,
        shell_setup_complete=True,
    )

    assert ops.get_workstacks_root() == Path("/ws")
    assert ops.get_use_graphite() is True
    assert ops.get_shell_setup_complete() is True
```

### Mutation Tracking: test_fake_gitops.py

Shows pattern for testing mutation tracking properties:

```python
def test_fake_gitops_delete_branch_tracking() -> None:
    """Test that FakeGitOps tracks deleted branches."""
    repo_root = Path("/repo")
    git_ops = FakeGitOps()

    git_ops.delete_branch_with_graphite(repo_root, "old-branch", force=True)

    assert "old-branch" in git_ops.deleted_branches
```

### Parametrized Edge Cases: test_fake_global_config_ops.py

Shows pattern for testing multiple edge cases efficiently:

```python
@pytest.mark.parametrize(
    "exists_flag",
    [True, False],
    ids=["exists", "missing"],
)
def test_fake_global_config_ops_exists_flag(exists_flag: bool) -> None:
    """exists() exposes whether the fake config file should be considered present."""
    ops = FakeGlobalConfigOps(exists=exists_flag)
    assert ops.exists() is exists_flag
```

## When to Add or Update Fake Tests

**Add tests when:**

- Creating a new fake implementation
- Adding a new method to an existing fake
- Discovering drift between fake and real behavior
- Adding mutation tracking properties

**Update tests when:**

- Modifying fake implementation behavior
- Changing method signatures
- Fixing bugs in fakes

## Maintenance Process

When modifying ANY real operations implementation:

1. Check if corresponding fake implements the same method
2. Check if tests exist for that method in `tests/unit/fakes/`
3. If tests missing, add them BEFORE merging changes
4. Run both unit tests (fakes) AND integration tests (real)

**Process checklist:**

- [ ] Modified real implementation method
- [ ] Checked fake has matching method
- [ ] Verified fake tests exist
- [ ] Added/updated fake tests if needed
- [ ] All tests pass (unit + integration)

## Running Fake Tests

Run all fake tests:

```bash
uv run pytest tests/unit/fakes/ -v
```

Run specific fake test file:

```bash
uv run pytest tests/unit/fakes/test_fake_gitops.py -v
```

## Success Criteria for Fake Modifications

Before merging changes to any fake:

✅ All abstract methods have at least 1 test
✅ All mutation tracking properties validated
✅ Edge cases covered (missing keys, empty state, invalid inputs)
✅ All tests pass
✅ Documentation updated if behavior changed

## Test Coverage Statistics

As of implementation completion:

- **Total test files**: 5
- **Total tests**: 74
- **Coverage**: 100% of fake implementations have dedicated tests
- **All abstract methods**: Validated across all fakes
- **Mutation tracking**: All properties tested
- **Edge cases**: Comprehensively covered

### Test Breakdown by Fake

- **FakeGitOps** (31 tests):
  - 16 existing tests for core operations
  - 15 new tests for critical gap methods
  - 5 comprehensive tests for `get_file_status` (high-risk method)
  - All mutation tracking properties validated
- **FakeGitHubOps** (10 tests):
  - All abstract methods covered
  - Both legacy and modern PR info formats tested
  - Edge cases (missing branches, empty state) covered
- **FakeGraphiteOps** (18 tests):
  - Branch metadata and stack traversal tested
  - Sync operation tracking validated
  - Configuration variations covered
- **FakeShellOps** (9 tests):
  - All shell detection scenarios tested
  - Tool path lookup with edge cases
  - Multiple shell type configurations
- **FakeGlobalConfigOps** (6 tests):
  - All configuration fields validated
  - Existing and missing file scenarios
  - State mutations tracked

## See Also

- [tests/unit/fakes/AGENTS.md](../../tests/unit/fakes/AGENTS.md) - Directory structure and organization
- [testing.md](testing.md) - Overall testing architecture
- [glossary.md](glossary.md) - Project terminology
