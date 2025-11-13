# Testing Workflows

**Read this when**: You're doing a specific task and need step-by-step guidance.

## Overview

This document provides concrete workflows for common testing scenarios. Each workflow includes a checklist and code examples.

## Adding a New Feature

**Test-first workflow** (TDD is encouraged):

### Step 1: Write Test Over Fakes

**Location**: `tests/commands/test_my_feature.py` or `tests/unit/test_my_logic.py`

```python
from click.testing import CliRunner
from pathlib import Path

def test_my_feature(tmp_path: Path) -> None:
    """Test my new feature."""
    # Arrange: Configure fake with initial state
    git_ops = FakeGitOps(
        worktrees={tmp_path / "repo": [WorktreeInfo(path=tmp_path / "wt", branch="main")]},
        current_branches={tmp_path / "wt": "main"},
    )

    ctx = WorkstackContext.for_test(git_ops=git_ops, cwd=tmp_path)

    # Act: Execute via CliRunner
    runner = CliRunner()
    result = runner.invoke(my_feature_cmd, obj=ctx)

    # Assert: Check expected behavior
    assert result.exit_code == 0
    assert "expected output" in result.output

    # Assert: Check state mutations (if applicable)
    assert len(git_ops.added_worktrees) == 1
```

**Key points**:

- Use `FakeGitOps`, `FakeGraphiteOps`, `FakeGitHubOps` for speed
- Use `CliRunner` (NOT subprocess)
- Use `tmp_path` for real directories when needed
- Test runs in milliseconds

### Step 2: Implement Feature

**Location**: `src/workstack/commands/` or `src/workstack/core/`

```python
@click.command()
@click.pass_obj
def my_feature_cmd(ctx: WorkstackContext) -> None:
    """Implement my new feature."""
    # Write business logic that calls ops interfaces
    worktrees = ctx.git_ops.list_worktrees(ctx.repo.root)

    # Keep ops classes thin - push complexity here
    filtered = [wt for wt in worktrees if some_business_logic(wt)]

    # Output using click.echo()
    for wt in filtered:
        click.echo(f"Found: {wt.branch}")
```

**Design principles**:

- Keep ops classes thin (thin wrappers)
- Push complexity to business logic layer
- Business logic calls ops interfaces, not subprocess directly

### Step 3: Run Tests

```bash
uv run pytest tests/commands/test_my_feature.py -v
```

**Expected outcome**:

- Test should pass (if implementation correct)
- Test should reveal bugs (if implementation has issues)
- Fast feedback loop (milliseconds per test)

### Step 4: Add Integration Test (Optional)

**When to add**: For critical user-facing features only.

**Location**: `tests/integration/test_my_feature_e2e.py`

```python
def test_my_feature_e2e(tmp_path: Path) -> None:
    """End-to-end test with real git."""
    # Setup real git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial"], cwd=tmp_path, check=True)

    ctx = WorkstackContext(
        git_ops=RealGitOps(),
        cwd=tmp_path,
        ...
    )

    runner = CliRunner()
    result = runner.invoke(my_feature_cmd, obj=ctx)

    # Assert: Verify real system state
    assert result.exit_code == 0
    # ... check actual filesystem/git state
```

---

## Fixing a Bug

### Step 1: Reproduce Bug with Test Over Fakes

**Write a failing test first** to demonstrate the bug:

```python
def test_bug_xyz_is_fixed(tmp_path: Path) -> None:
    """Regression test for bug #XYZ: feature crashes with empty repo."""
    # Arrange: Configure state that triggers bug
    git_ops = FakeGitOps(
        worktrees={},  # Empty repo triggers bug
        current_branches={},
    )

    ctx = WorkstackContext.for_test(git_ops=git_ops, cwd=tmp_path)

    # Act
    runner = CliRunner()
    result = runner.invoke(buggy_cmd, obj=ctx)

    # Assert: This should FAIL initially (demonstrating the bug)
    assert result.exit_code == 0  # Bug: currently exits with 1
    assert "No worktrees found" in result.output  # Bug: currently crashes
```

**Key insight**: Test should FAIL initially. This proves you've reproduced the bug.

### Step 2: Fix the Bug

**Location**: `src/workstack/commands/` or `src/workstack/core/`

```python
# Before (buggy):
def buggy_cmd(ctx: WorkstackContext) -> None:
    worktrees = ctx.git_ops.list_worktrees(ctx.repo.root)
    first_wt = worktrees[0]  # ❌ Crashes if empty!

# After (fixed):
def buggy_cmd(ctx: WorkstackContext) -> None:
    worktrees = ctx.git_ops.list_worktrees(ctx.repo.root)

    if not worktrees:  # ✅ Check first (LBYL)
        click.echo("No worktrees found")
        return

    first_wt = worktrees[0]
```

### Step 3: Run Test

```bash
uv run pytest tests/commands/test_bug_xyz_is_fixed.py -v
```

**Expected outcome**: Test should now PASS.

### Step 4: Leave Test as Regression Test

**Don't delete the test!** It prevents future regressions.

```python
def test_bug_xyz_is_fixed(tmp_path: Path) -> None:
    """Regression test for bug #XYZ: feature crashed with empty repo."""
    # Keep this test to prevent regression
    ...
```

---

## Adding an Ops Method

**Use this checklist when adding a new method to an ops interface.**

### Checklist

- [ ] Add `@abstractmethod` to ABC interface (e.g., `GitOps`)
- [ ] Implement in real class (e.g., `RealGitOps`) with subprocess/filesystem
- [ ] Implement in fake class (e.g., `FakeGitOps`) with in-memory state
- [ ] Add mutation tracking property to fake if it's a write operation
- [ ] Add handler in dry-run wrapper (e.g., `DryRunGitOps`)
- [ ] Write unit test of fake (`tests/unit/fakes/test_fake_gitops.py`)
- [ ] Write integration test of real (`tests/integration/test_real_gitops.py`)
- [ ] Update business logic to call new method
- [ ] Write business logic test over fake

### Example: Adding `GitOps.rename_branch()`

#### 1. Interface (`src/workstack/core/gitops.py`)

```python
class GitOps(ABC):
    @abstractmethod
    def rename_branch(self, repo_root: Path, old_name: str, new_name: str) -> None:
        """Rename a branch."""
```

#### 2. Real Implementation (`src/workstack/core/gitops.py`)

```python
class RealGitOps(GitOps):
    def rename_branch(self, repo_root: Path, old_name: str, new_name: str) -> None:
        subprocess.run(
            ["git", "branch", "-m", old_name, new_name],
            cwd=repo_root,
            check=True,
        )
```

#### 3. Fake Implementation (`tests/fakes/gitops.py`)

```python
class FakeGitOps(GitOps):
    def __init__(self, ...):
        ...
        self._renamed_branches: list[tuple[str, str]] = []

    def rename_branch(self, repo_root: Path, old_name: str, new_name: str) -> None:
        # Update in-memory state
        if old_name in self._branches:
            self._branches[new_name] = self._branches.pop(old_name)

        # Track mutation
        self._renamed_branches.append((old_name, new_name))

    @property
    def renamed_branches(self) -> list[tuple[str, str]]:
        """Read-only access for test assertions."""
        return self._renamed_branches.copy()
```

#### 4. Dry-Run Wrapper (`src/workstack/core/gitops.py`)

```python
class DryRunGitOps(GitOps):
    def rename_branch(self, repo_root: Path, old_name: str, new_name: str) -> None:
        click.echo(f"[DRY RUN] Would rename branch: {old_name} → {new_name}")
```

#### 5. Test Fake (`tests/unit/fakes/test_fake_gitops.py`)

```python
def test_fake_gitops_rename_branch() -> None:
    """Test that FakeGitOps tracks branch renames."""
    git_ops = FakeGitOps(branches={"old-name"})

    git_ops.rename_branch(Path("/repo"), "old-name", "new-name")

    # Assert mutation was tracked
    assert ("old-name", "new-name") in git_ops.renamed_branches

    # Assert state was updated
    assert "new-name" in git_ops.list_branches(Path("/repo"))
    assert "old-name" not in git_ops.list_branches(Path("/repo"))
```

#### 6. Test Real (`tests/integration/test_real_gitops.py`)

```python
def test_real_gitops_rename_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that RealGitOps calls correct git command."""
    # Mock subprocess.run
    run_calls: list[list[str]] = []
    def mock_run(cmd: list[str], **kwargs):
        run_calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    git_ops = RealGitOps()
    git_ops.rename_branch(tmp_path, "old-name", "new-name")

    # Assert correct command was constructed
    assert run_calls[0] == ["git", "branch", "-m", "old-name", "new-name"]
```

#### 7. Update Business Logic

```python
# src/workstack/commands/rename.py
@click.command()
@click.argument("old_name")
@click.argument("new_name")
@click.pass_obj
def rename_branch_cmd(ctx: WorkstackContext, old_name: str, new_name: str) -> None:
    """Rename a branch."""
    ctx.git_ops.rename_branch(ctx.repo.root, old_name, new_name)
    click.echo(f"✓ Renamed {old_name} → {new_name}")
```

#### 8. Write Business Logic Test

```python
# tests/commands/test_rename.py
def test_rename_branch_command(tmp_path: Path) -> None:
    """Test rename branch command."""
    git_ops = FakeGitOps(branches={"old-name"})
    ctx = WorkstackContext.for_test(git_ops=git_ops, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(rename_branch_cmd, ["old-name", "new-name"], obj=ctx)

    assert result.exit_code == 0
    assert "Renamed old-name → new-name" in result.output
    assert ("old-name", "new-name") in git_ops.renamed_branches
```

---

## Changing an Interface

**When modifying an existing method signature.**

### Checklist

- [ ] Update ABC interface
- [ ] Update real implementation
- [ ] Update fake implementation
- [ ] Update dry-run wrapper
- [ ] Update all call sites in business logic
- [ ] Update unit tests of fake
- [ ] Update integration tests of real
- [ ] Update business logic tests that use the method

### Example: Adding a Parameter

**Before**:

```python
def delete_branch(self, repo_root: Path, branch: str) -> None:
    """Delete a branch."""
```

**After** (adding `force` parameter):

```python
def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
    """Delete a branch, optionally with --force."""
```

**Steps**:

1. Update `GitOps` (ABC)
2. Update `RealGitOps`: `["git", "branch", "-D" if force else "-d", branch]`
3. Update `FakeGitOps`: Track `force` in mutations
4. Update `DryRunGitOps`: Print force flag
5. Update all call sites: `git_ops.delete_branch(repo, "feat", force=True)`
6. Update tests

---

## Managing Dry-Run Features

**Pattern**: Pass dry-run flag down to ops layer by wrapping with `DryRunGitOps`.

### CLI Level

**Location**: `src/workstack/commands/`

```python
@click.command()
@click.option("--dry-run", is_flag=True, help="Show what would be done without doing it")
@click.pass_obj
def remove_worktree_cmd(ctx: WorkstackContext, dry_run: bool) -> None:
    """Remove a worktree."""
    git_ops = ctx.git_ops

    # Wrap ops layer with dry-run wrapper
    if dry_run:
        git_ops = DryRunGitOps(git_ops)

    # Business logic uses git_ops normally
    # If dry-run, operations will print instead of executing
    git_ops.remove_worktree(ctx.repo.root, path, force=False)

    if not dry_run:
        click.echo(f"✓ Removed worktree at {path}")
```

**Key insight**: Business logic doesn't change. Dry-run wrapping happens at CLI level.

### Testing Dry-Run

**Pattern**: Verify operations are NOT executed, but messages are printed.

```python
def test_remove_worktree_dry_run(tmp_path: Path) -> None:
    """Verify --dry-run doesn't remove worktree."""
    repo_root = tmp_path / "repo"
    wt_path = tmp_path / "wt"

    git_ops = FakeGitOps(
        worktrees={repo_root: [WorktreeInfo(path=wt_path, branch="feature")]},
    )
    ctx = WorkstackContext.for_test(git_ops=git_ops, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(remove_worktree_cmd, ["--dry-run"], obj=ctx)

    # Verify operation was NOT executed
    assert len(git_ops.removed_worktrees) == 0

    # Verify dry-run message was printed
    assert "[DRY RUN]" in result.output
    assert "Would remove worktree" in result.output
```

### Implementing Dry-Run in Wrapper

**Pattern**: Read operations delegate, write operations print.

```python
class DryRunGitOps(GitOps):
    def __init__(self, git_ops: GitOps) -> None:
        self._git_ops = git_ops

    # Read operation: delegate
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        return self._git_ops.list_worktrees(repo_root)

    # Write operation: print instead of executing
    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        force_flag = " (force)" if force else ""
        click.echo(f"[DRY RUN] Would remove worktree: {path}{force_flag}")
        # Does NOT call self._git_ops.remove_worktree()
```

---

## Testing with Builder Patterns

**Use builder pattern for complex test scenarios.**

### Example: WorktreeScenario Builder

```python
class WorktreeScenario:
    """Builder for complex worktree test scenarios."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.worktrees: dict[Path, list[WorktreeInfo]] = {}
        self.prs: dict[str, PRInfo] = {}
        self.stacks: dict[str, list[str]] = {}

    def with_feature_branch(self, name: str) -> WorktreeScenario:
        """Add a feature branch worktree."""
        path = self.base_path / name
        if self.base_path not in self.worktrees:
            self.worktrees[self.base_path] = []
        self.worktrees[self.base_path].append(
            WorktreeInfo(path=path, branch=name, ...)
        )
        return self

    def with_pr(self, branch: str, *, number: int, title: str = "Test PR") -> WorktreeScenario:
        """Add a PR for a branch."""
        self.prs[branch] = PRInfo(number=number, title=title, ...)
        return self

    def with_stack(self, branches: list[str]) -> WorktreeScenario:
        """Add a Graphite stack."""
        for i, branch in enumerate(branches):
            if i > 0:
                self.stacks[branch] = [branches[i-1]]
        return self

    def build(self) -> WorkstackContext:
        """Build context with configured state."""
        git_ops = FakeGitOps(worktrees=self.worktrees)
        github_ops = FakeGitHubOps(prs=self.prs)
        graphite_ops = FakeGraphiteOps(stacks=self.stacks)

        return WorkstackContext.for_test(
            git_ops=git_ops,
            github_ops=github_ops,
            graphite_ops=graphite_ops,
            cwd=self.base_path,
        )
```

### Usage

```python
def test_complex_scenario(tmp_path: Path) -> None:
    """Test with multiple worktrees, PRs, and stacks."""
    ctx = (
        WorktreeScenario(tmp_path)
        .with_feature_branch("feature-1")
        .with_feature_branch("feature-2")
        .with_pr("feature-1", number=123, title="Add new feature")
        .with_pr("feature-2", number=124, title="Fix bug")
        .with_stack(["main", "feature-1", "feature-2"])
        .build()
    )

    runner = CliRunner()
    result = runner.invoke(status_cmd, obj=ctx)

    assert "#123" in result.output
    assert "#124" in result.output
```

**Benefits**:

- Readable test setup
- Reusable across tests
- Clear intent (declarative)
- Easy to extend

---

## Related Documentation

- `testing-strategy.md` - Which layer to test at
- `ops-architecture.md` - Understanding the ops layer
- `patterns.md` - Common testing patterns (CliRunner, mutation tracking, etc.)
- `anti-patterns.md` - What to avoid
