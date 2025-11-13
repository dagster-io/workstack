# Testing Anti-Patterns

**Read this when**: You're unsure if your approach is correct, or want to avoid common mistakes.

## Overview

This document covers common anti-patterns in testing and how to avoid them. Each anti-pattern includes examples of what NOT to do and the correct approach.

## ❌ Testing Speculative Features

**NEVER write tests for code that doesn't exist yet** (unless doing TDD RIGHT NOW).

### Wrong Approach

```python
# ❌ WRONG: Placeholder test for future feature
# def test_feature_we_might_add_later():
#     """TODO: Implement this feature next sprint."""
#     pass

# ❌ WRONG: Test stub for "maybe someday" idea
# def test_hypothetical_feature():
#     """Feature we're considering for Q2."""
#     # Not implemented yet, just a placeholder
#     pass
```

### Correct Approach

```python
# ✅ CORRECT: TDD for feature being implemented NOW
def test_new_feature_im_building_today():
    """Test for feature I'm implementing in this session."""
    result = my_new_feature()  # Will implement after this test
    assert result == expected

# ✅ CORRECT: Test for actively worked bug fix
def test_bug_123_is_fixed():
    """Regression test for bug I'm fixing right now."""
    # Reproducing bug, then will fix it
    ...
```

### Why This Is Wrong

**Problems with speculative tests**:

- **Maintenance burden**: Tests need updating when feature changes
- **False confidence**: Test suite looks comprehensive but validates nothing
- **Wasted effort**: Planned features often change significantly before implementation
- **Stale code**: Commented-out tests clutter codebase

**Rule**: Only write tests for code being **actively implemented or fixed in this work session**.

### TDD Is Explicitly Allowed

**TDD workflow is encouraged**:

1. Write failing test for feature you're about to implement
2. Implement feature
3. Test passes

This is NOT speculative because you're implementing NOW, not "maybe later."

---

## ❌ Hardcoded Paths in Tests (CATASTROPHIC)

**NEVER use hardcoded paths in tests**. Always use fixtures.

### Wrong Approach

```python
# ❌ WRONG - CATASTROPHICALLY DANGEROUS
def test_something():
    ctx = WorkstackContext(..., cwd=Path("/test/default/cwd"))

def test_another_thing():
    ctx = WorkstackContext(..., cwd=Path("/some/hardcoded/path"))

def test_with_absolute_path():
    repo = Path("/Users/someone/test/repo")
    # Code may write files to this path!
```

### Correct Approach

```python
# ✅ CORRECT - Use tmp_path fixture
def test_something(tmp_path: Path):
    ctx = WorkstackContext(..., cwd=tmp_path)

# ✅ CORRECT - Use simulated environment
def test_another_thing():
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        ctx = WorkstackContext(..., cwd=env.cwd)

# ✅ CORRECT - Use builder with tmp_path
def test_with_builder(tmp_path: Path):
    ctx = WorktreeScenario(tmp_path).with_main_branch().build()
```

### Why This Is Catastrophic

**Dangers of hardcoded paths**:

1. **Global config mutation**: Code may write `.workstack` files at hardcoded paths, polluting real filesystem
2. **False isolation**: Tests appear isolated but share state through hardcoded paths
3. **Security risk**: Creating files at system paths can be exploited
4. **CI/CD failures**: Paths may not exist on CI systems
5. **Permission errors**: Tests may not have write access to hardcoded paths

**Detection**: **If you see `Path("/` in test code, STOP and use fixtures.**

**See also**: `docs/agent/testing.md#critical-never-use-hardcoded-paths-in-tests`

---

## ❌ Not Updating All Layers When Interface Changes

**When changing an ops interface, you MUST update ALL four implementations.**

### Wrong Approach

```python
# You changed GitOps.list_worktrees() signature:

# 1. GitOps (ABC) ✅ Updated
class GitOps(ABC):
    @abstractmethod
    def list_worktrees(self, repo_root: Path, *, include_bare: bool = False) -> list[WorktreeInfo]:
        ...

# 2. RealGitOps ✅ Updated
class RealGitOps(GitOps):
    def list_worktrees(self, repo_root: Path, *, include_bare: bool = False) -> list[WorktreeInfo]:
        # Updated implementation
        ...

# 3. FakeGitOps ❌ FORGOT TO UPDATE!
class FakeGitOps(GitOps):
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        # Old signature - type error!
        ...

# 4. DryRunGitOps ❌ FORGOT TO UPDATE!
class DryRunGitOps(GitOps):
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        # Old signature - type error!
        ...

# Result: Type errors, broken tests, runtime failures
```

### Correct Approach

**Use this checklist when changing an interface**:

- [ ] Update ABC interface (e.g., `GitOps`)
- [ ] Update real implementation (e.g., `RealGitOps`)
- [ ] Update fake implementation (e.g., `FakeGitOps`)
- [ ] Update dry-run wrapper (e.g., `DryRunGitOps`)
- [ ] Update all call sites in business logic
- [ ] Update unit tests of fake
- [ ] Update integration tests of real
- [ ] Update business logic tests that use the method

**Tool**: Run `uv run pyright` to catch signature mismatches.

### Why This Is Wrong

**Problems**:

- **Type errors**: Implementations don't match interface
- **Runtime errors**: Tests pass locally but fail in production
- **Inconsistent behavior**: Different implementations have different behavior
- **Broken tests**: Tests expect old signature

**Rule**: When changing interface, update ALL four layers + tests.

**See also**: `workflows.md#changing-an-interface`

---

## ❌ Using subprocess in Unit Tests

**Use CliRunner for CLI tests, NOT subprocess**.

### Wrong Approach

```python
# ❌ WRONG: Slow, harder to debug
def test_status_command():
    result = subprocess.run(
        ["workstack", "status"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "main" in result.stdout

# ❌ WRONG: Even worse - shell=True
def test_create_command():
    result = subprocess.run(
        "workstack create feature",
        shell=True,
        capture_output=True,
    )
    assert result.returncode == 0
```

### Correct Approach

```python
# ✅ CORRECT: Fast, better error messages
def test_status_command(tmp_path: Path):
    git_ops = FakeGitOps(...)
    ctx = WorkstackContext.for_test(git_ops=git_ops, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(status_cmd, obj=ctx)

    assert result.exit_code == 0
    assert "main" in result.output

# ✅ CORRECT: With arguments
def test_create_command(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(create_cmd, ["feature"], obj=ctx)
    assert result.exit_code == 0
```

### Why This Is Wrong

**Performance**:

- **CliRunner**: milliseconds per test (~10ms)
- **subprocess**: seconds per test (~1s)
- **~100x slower** with subprocess

**Debugging**:

- subprocess: Harder to set breakpoints, unclear errors
- CliRunner: Direct access to exceptions, clear stack traces

**Reliability**:

- subprocess: Shell interpretation issues, PATH dependencies
- CliRunner: Direct Python invocation, no shell quirks

**Rule**: Always use `CliRunner` for CLI command tests. Only use subprocess for true end-to-end integration tests (Layer 4).

**See also**: `docs/agent/testing.md#cli-testing-patterns`, `patterns.md#using-clirunner-for-cli-tests`

---

## ❌ Complex Logic in Ops Classes

**Ops classes should be THIN wrappers**. Push complexity to business logic layer.

### Wrong Approach

```python
# ❌ WRONG: Business logic in ops class
class RealGitOps(GitOps):
    def smart_branch_selection(self, repo_root: Path) -> str:
        """Complex logic to select best branch."""
        worktrees = self.list_worktrees(repo_root)

        # 50 lines of complex business logic...
        scored_branches = {}
        for wt in worktrees:
            score = self._calculate_branch_score(wt)
            scored_branches[wt.branch] = score

        # More logic...
        best_branch = max(scored_branches, key=scored_branches.get)
        return best_branch

    def _calculate_branch_score(self, wt: WorktreeInfo) -> float:
        # Even more business logic...
        ...
```

**Problems**:

- Hard to fake (complex logic in fake too)
- Hard to test (need to mock everything)
- Hard to understand (mixed concerns)
- Hard to change (logic tied to git implementation)

### Correct Approach

```python
# ✅ CORRECT: Thin ops, just wrap git command
class RealGitOps(GitOps):
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """Just wrap git command - no business logic."""
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return self._parse_output(result.stdout)

    def _parse_output(self, stdout: str) -> list[WorktreeInfo]:
        """Parse git output - simple data transformation."""
        # Simple parsing, no business logic
        ...

# ✅ CORRECT: Business logic in separate layer
def select_best_branch(git_ops: GitOps, repo_root: Path) -> str:
    """Complex logic over thin ops."""
    worktrees = git_ops.list_worktrees(repo_root)

    # 50 lines of business logic - easy to test over fakes!
    scored_branches = {}
    for wt in worktrees:
        score = calculate_branch_score(wt)
        scored_branches[wt.branch] = score

    return max(scored_branches, key=scored_branches.get)
```

**Benefits**:

- Easy to fake (thin ops, simple fake)
- Easy to test (business logic tested over fakes)
- Easy to understand (clear separation of concerns)
- Easy to change (business logic independent of git)

### Rule

**Ops classes should**:

- Wrap external system calls (git, gh, gt)
- Parse output into domain objects
- Validate basic preconditions (path exists, etc.)

**Ops classes should NOT**:

- Contain business logic
- Make decisions about "what to do"
- Implement algorithms or scoring
- Have complex control flow

**Test**: If you can't easily fake an ops class, it's too complex. Push logic up.

---

## ❌ Fakes with I/O Operations

**Fakes should be in-memory ONLY** (except minimal directory creation).

### Wrong Approach

```python
# ❌ WRONG: Fake performs I/O
class FakeGitOps(GitOps):
    def get_branch_name(self, path: Path) -> str:
        # Reading real files defeats the purpose of fakes!
        return (path / ".git" / "HEAD").read_text()

    def has_uncommitted_changes(self, repo_root: Path) -> bool:
        # Running real git commands defeats the purpose!
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
        )
        return len(result.stdout) > 0
```

**Problems**:

- Slow (I/O operations)
- Requires real filesystem setup
- Defeats purpose of fakes
- Tests become integration tests

### Correct Approach

```python
# ✅ CORRECT: Fake uses in-memory state
class FakeGitOps(GitOps):
    def __init__(
        self,
        *,
        current_branches: dict[Path, str] | None = None,
        uncommitted_changes: dict[Path, bool] | None = None,
    ) -> None:
        self._current_branches = current_branches or {}
        self._uncommitted_changes = uncommitted_changes or {}

    def get_branch_name(self, path: Path) -> str:
        """Return in-memory branch name."""
        return self._current_branches.get(path, "main")

    def has_uncommitted_changes(self, repo_root: Path) -> bool:
        """Return in-memory state."""
        return self._uncommitted_changes.get(repo_root, False)
```

**Benefits**:

- Fast (no I/O)
- Simple test setup (configure via constructor)
- True unit testing
- Reliable (no filesystem quirks)

### Exception: Directory Creation

**Acceptable**: Fakes may create real directories when needed for filesystem integration.

```python
# ✅ ACCEPTABLE: Create directory for integration
class FakeGitOps(GitOps):
    def add_worktree(self, repo_root: Path, path: Path, *, branch: str | None) -> None:
        # Update in-memory state
        self._worktrees[repo_root].append(WorktreeInfo(path=path, branch=branch))

        # Create real directory (acceptable for filesystem integration)
        path.mkdir(parents=True, exist_ok=True)

        # But don't write .git files or anything else!
```

**Rule**: Fakes may `mkdir()`, but should not read/write files.

---

## ❌ Testing Implementation Details

**Test behavior, not implementation**.

### Wrong Approach

```python
# ❌ WRONG: Testing internal implementation details
def test_status_uses_collector_pattern():
    """Test that status command uses collector pattern."""
    # Checking how it's implemented, not what it does
    assert hasattr(status_cmd, "_collectors")
    assert len(status_cmd._collectors) == 3
```

### Correct Approach

```python
# ✅ CORRECT: Testing observable behavior
def test_status_shows_worktrees_and_prs(tmp_path: Path):
    """Test that status command displays worktrees and PRs."""
    ctx = (
        WorktreeScenario(tmp_path)
        .with_feature_branch("feature", pr_number=123)
        .build()
    )

    runner = CliRunner()
    result = runner.invoke(status_cmd, obj=ctx)

    # Assert on observable output, not implementation
    assert result.exit_code == 0
    assert "feature" in result.output
    assert "#123" in result.output
```

### Why This Is Wrong

**Problems**:

- Tests break when refactoring
- Couples tests to implementation
- Doesn't verify user-visible behavior
- Makes code harder to change

**Rule**: Test what the code **does**, not **how** it does it.

---

## ❌ Incomplete Test Coverage for Ops Changes

**When adding/changing ops method, you must test ALL implementations**.

### Wrong Approach

```python
# Added new method to GitOps
# ✅ Implemented in RealGitOps
# ✅ Implemented in FakeGitOps
# ❌ Forgot to test FakeGitOps!
# ❌ Forgot to test RealGitOps!

# Result: Untested code, potential bugs
```

### Correct Approach

**Complete testing checklist**:

- [ ] Unit test of fake (`tests/unit/fakes/test_fake_gitops.py`)
- [ ] Integration test of real with mocking (`tests/integration/test_real_gitops.py`)
- [ ] Business logic test using fake (`tests/commands/test_my_feature.py`)
- [ ] (Optional) E2E test with real implementation

**See**: `workflows.md#adding-an-ops-method` for full checklist.

---

## Summary of Anti-Patterns

| Anti-Pattern                 | Why It's Wrong                    | Correct Approach            |
| ---------------------------- | --------------------------------- | --------------------------- |
| Testing speculative features | Maintenance burden, no value      | Only test active work       |
| Hardcoded paths              | Catastrophic: pollutes filesystem | Use `tmp_path` fixture      |
| Not updating all layers      | Type errors, broken tests         | Update ABC/Real/Fake/DryRun |
| subprocess in unit tests     | 100x slower, harder to debug      | Use `CliRunner`             |
| Complex logic in ops         | Hard to test, hard to fake        | Keep ops thin               |
| Fakes with I/O               | Slow, defeats purpose             | In-memory only              |
| Testing implementation       | Breaks on refactoring             | Test behavior               |
| Incomplete ops test coverage | Untested code, potential bugs     | Test all implementations    |

## Related Documentation

- `workflows.md` - Step-by-step guides for correct approaches
- `patterns.md` - Common testing patterns to follow
- `testing-strategy.md` - Which layer to test at
- `ops-architecture.md` - Understanding the ops layer
