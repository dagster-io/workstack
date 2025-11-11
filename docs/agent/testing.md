# Test Architecture: Coarse-Grained Dependency Injection

## 🔴 CRITICAL: NEVER Use Hardcoded Paths in Tests

**ABSOLUTELY FORBIDDEN** patterns in test code:

```python
# ❌ WRONG - EXTREMELY DANGEROUS
cwd=Path("/test/default/cwd")
cwd=Path("/some/hardcoded/path")
```

**Why this is catastrophic:**

1. **Global Config Mutation Risk**: If any code tries to write `.workstack` config relative to a hardcoded path, it could pollute the REAL filesystem or global config
2. **False Test Isolation**: Tests appear isolated but may share state through hardcoded paths
3. **Unpredictable Failures**: Tests fail in CI/different environments where paths don't exist
4. **Security Risk**: Creating files at hardcoded system paths can be exploited

**ALWAYS use proper context from test fixtures:**

```python
# ✅ CORRECT - Use simulated environment
with simulated_workstack_env(runner) as env:
    ctx = WorkstackContext(..., cwd=env.cwd)

# ✅ CORRECT - Use tmp_path fixture
def test_something(tmp_path: Path) -> None:
    ctx = WorkstackContext(..., cwd=tmp_path)

# ✅ CORRECT - Use env from simulated helper
ctx = _create_test_context(env, ...)  # env.cwd used internally
```

**If you see `Path("/` in test code, STOP IMMEDIATELY and use proper fixtures.**

---

## Quick Reference

| Testing Scenario              | Use This                                             |
| ----------------------------- | ---------------------------------------------------- |
| Unit test CLI command         | FakeGitOps + FakeGlobalConfigOps + context injection |
| Integration test git behavior | RealGitOps + tmp_path fixture                        |
| Test dry-run behavior         | create_context(dry_run=True) + assertions on output  |
| Test shell detection          | FakeShellOps with detected_shell parameter           |
| Test tool availability        | FakeShellOps with installed_tools parameter          |

## Dependency Categories

### 1. GitOps - Version Control Operations

**Real Implementation**: `RealGitOps()`
**Dry-Run Wrapper**: `DryRunGitOps(wrapped)`
**Fake Implementation**: `FakeGitOps(...)`

**Constructor Parameters**:

```python
FakeGitOps(
    worktrees: dict[Path, list[WorktreeInfo]] = {},
    current_branches: dict[Path, str] = {},
    default_branches: dict[Path, str] = {},
    git_common_dirs: dict[Path, Path] = {},
)
```

**Mutation Tracking** (read-only properties):

- `git_ops.deleted_branches: list[str]`
- `git_ops.added_worktrees: list[tuple[Path, str | None]]`
- `git_ops.removed_worktrees: list[Path]`
- `git_ops.checked_out_branches: list[tuple[Path, str]]`

**Common Patterns**:

```python
# Pattern 1: Empty git state
git_ops = FakeGitOps(git_common_dirs={cwd: cwd / ".git"})

# Pattern 2: Pre-configured worktrees
git_ops = FakeGitOps(
    worktrees={
        repo: [
            WorktreeInfo(path=repo, branch="main"),
            WorktreeInfo(path=wt1, branch="feature"),
        ]
    },
    git_common_dirs={repo: repo / ".git"},
)

# Pattern 3: Track mutations
git_ops = FakeGitOps(...)
# ... run command ...
assert "feature" in git_ops.deleted_branches
```

### 2. GlobalConfigOps - Configuration Management

**Real Implementation**: `RealGlobalConfigOps()`
**Dry-Run Wrapper**: `DryRunGlobalConfigOps(wrapped)`
**Fake Implementation**: `FakeGlobalConfigOps(...)`

**Constructor Parameters**:

```python
FakeGlobalConfigOps(
    exists: bool = True,
    workstacks_root: Path | None = None,
    use_graphite: bool = False,
    shell_setup_complete: bool = False,
    show_pr_info: bool = True,
    show_pr_checks: bool = False,
)
```

**Common Patterns**:

```python
# Pattern 1: Config exists with values
config_ops = FakeGlobalConfigOps(
    exists=True,
    workstacks_root=Path("/tmp/workstacks"),
    use_graphite=True,
)

# Pattern 2: Config doesn't exist (first-time init)
config_ops = FakeGlobalConfigOps(exists=False)

# Pattern 3: Test config mutations
config_ops = FakeGlobalConfigOps(exists=False)
config_ops.set(workstacks_root=Path("/tmp/ws"), use_graphite=True)
assert config_ops.get_workstacks_root() == Path("/tmp/ws")
```

### 3. GitHubOps - GitHub API Interactions

**Real Implementation**: `RealGitHubOps()`
**Dry-Run Wrapper**: `DryRunGitHubOps(wrapped)`
**Fake Implementation**: `FakeGitHubOps(...)`

**Constructor Parameters**:

```python
FakeGitHubOps(
    prs: dict[str, PullRequestInfo] = {},
)
```

**Common Patterns**:

```python
# Pattern 1: No PRs
github_ops = FakeGitHubOps()

# Pattern 2: Pre-configured PRs
from workstack.core.github_ops import PullRequestInfo

github_ops = FakeGitHubOps(
    prs={
        "feature-branch": PullRequestInfo(
            number=123,
            state="OPEN",
            url="https://github.com/owner/repo/pull/123",
            is_draft=False,
            checks_passing=True,
            owner="owner",
            repo="repo",
        ),
    }
)
```

### 4. GraphiteOps - Graphite Tool Operations

**Real Implementation**: `RealGraphiteOps()`
**Dry-Run Wrapper**: `DryRunGraphiteOps(wrapped)`
**Fake Implementation**: `FakeGraphiteOps(...)`

**Constructor Parameters**:

```python
FakeGraphiteOps(
    stacks: dict[Path, list[str]] = {},
    current_branch_in_stack: dict[Path, bool] = {},
)
```

**Common Patterns**:

```python
# Pattern 1: No Graphite stacks
graphite_ops = FakeGraphiteOps()

# Pattern 2: Pre-configured stacks
graphite_ops = FakeGraphiteOps(
    stacks={repo: ["main", "feature-1", "feature-2"]},
    current_branch_in_stack={repo: True},
)
```

### 5. ShellOps - Shell Detection and Tool Availability

**Real Implementation**: `RealShellOps()`
**No Dry-Run Wrapper** (read-only operations)
**Fake Implementation**: `FakeShellOps(...)`

**Constructor Parameters**:

```python
FakeShellOps(
    detected_shell: tuple[str, Path] | None = None,
    installed_tools: dict[str, str] = {},
)
```

**Common Patterns**:

```python
# Pattern 1: No shell detected
shell_ops = FakeShellOps()

# Pattern 2: Bash shell detected
shell_ops = FakeShellOps(
    detected_shell=("bash", Path.home() / ".bashrc")
)

# Pattern 3: Tool installed
shell_ops = FakeShellOps(
    installed_tools={"gt": "/usr/local/bin/gt"}
)

# Pattern 4: Multiple tools
shell_ops = FakeShellOps(
    detected_shell=("zsh", Path.home() / ".zshrc"),
    installed_tools={
        "gt": "/usr/local/bin/gt",
        "gh": "/usr/local/bin/gh",
    }
)
```

## Testing Patterns

### Unit Test Pattern

```python
def test_command_behavior() -> None:
    """Test CLI command with fakes."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()

        # Configure fakes with initial state
        git_ops = FakeGitOps(git_common_dirs={cwd: cwd / ".git"})
        config_ops = FakeGlobalConfigOps(
            workstacks_root=cwd / "workstacks",
            use_graphite=False,
        )

        # Create context with all dependencies
        test_ctx = WorkstackContext(
            git_ops=git_ops,
            global_config_ops=config_ops,
            github_ops=FakeGitHubOps(),
            graphite_ops=FakeGraphiteOps(),
            shell_ops=FakeShellOps(),
            dry_run=False,
        )

        # Invoke command
        result = runner.invoke(cli, ["command", "args"], obj=test_ctx)

        # Assert on results
        assert result.exit_code == 0
        assert "expected output" in result.output

        # Assert on mutations (if tracking enabled)
        assert len(git_ops.deleted_branches) == 1
```

### Integration Test Pattern

```python
def test_real_git_behavior(tmp_path: Path) -> None:
    """Test with real git operations."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Set up real git repo
    init_git_repo(repo, "main")
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature", str(wt1)],
        cwd=repo,
        check=True,
    )

    # Use real GitOps
    git_ops = RealGitOps()
    worktrees = git_ops.list_worktrees(repo)

    assert len(worktrees) == 2
    assert any(wt.branch == "feature" for wt in worktrees)
```

### Dry-Run Test Pattern

```python
def test_dryrun_prevents_mutations() -> None:
    """Test dry-run mode prevents changes."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Use production context factory with dry_run=True
        ctx = create_context(dry_run=True)

        result = runner.invoke(
            cli,
            ["rm", "stack", "--force"],
            obj=ctx,
        )

        # Verify dry-run message printed
        assert "[DRY RUN]" in result.output or "[DRY RUN]" in result.stderr

        # Verify no actual changes (check filesystem)
        assert directory_still_exists
```

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: Using mock.patch

```python
# DON'T DO THIS
def test_bad(monkeypatch):
    monkeypatch.setattr("module.function", lambda: "fake")
    result = function_under_test()
```

**Why it's bad**: Tight coupling to implementation details, fragile tests.

**Do this instead**:

```python
# DO THIS
def test_good():
    fake_ops = FakeShellOps(installed_tools={"tool": "/path"})
    ctx = WorkstackContext(..., shell_ops=fake_ops, ...)
    result = function_under_test(ctx)
```

### ❌ Anti-Pattern 2: Mutating Private Attributes

```python
# DON'T DO THIS
def test_bad():
    ops = RealGlobalConfigOps()
    ops._path = test_path  # Violates encapsulation
```

**Do this instead**:

```python
# DO THIS
def test_good():
    ops = FakeGlobalConfigOps(...)  # Constructor injection
```

### ❌ Anti-Pattern 3: Not Using Context Injection

```python
# DON'T DO THIS
def test_bad():
    result = runner.invoke(cli, ["command"])  # Uses production context
```

**Do this instead**:

```python
# DO THIS
def test_good():
    test_ctx = create_test_context(...)  # Or WorkstackContext(...)
    result = runner.invoke(cli, ["command"], obj=test_ctx)
```

## State Mutation in Fakes

### When Fakes Need Mutation

Some operations require mutating state to simulate external systems:

- Git operations (add/remove worktrees, checkout branches)
- Configuration updates (set values)

### Mutation vs Immutability

- **Initial State**: Always via constructor (immutable after construction)
- **Runtime State**: Modified through operation methods (mutable)
- **Mutation Tracking**: Exposed via read-only properties for assertions

### Example: Testing Mutations

```python
def test_branch_deletion():
    # Initial state via constructor
    git_ops = FakeGitOps(
        worktrees={repo: [WorktreeInfo(path=wt, branch="feature")]},
        git_common_dirs={repo: repo / ".git"},
    )

    # Verify initial state
    assert len(git_ops.list_worktrees(repo)) == 1

    # Perform mutation
    git_ops.delete_branch_with_graphite(repo, "feature", force=True)

    # Verify mutation via tracking property
    assert "feature" in git_ops.deleted_branches
    assert len(git_ops.deleted_branches) == 1
```

## Decision Tree

```
Need to test CLI command?
├─ Unit test (fast, isolated logic)
│  └─ Use Fake* classes
│     └─ Configure state via constructor
│        └─ Inject via WorkstackContext
│           └─ Pass as obj= to runner.invoke()
│
└─ Integration test (verify real system behavior)
   └─ Use Real* classes
      └─ Set up with actual commands (git, etc.)
         └─ Use tmp_path for isolation
            └─ Verify actual filesystem/system changes
```

## Helper Functions

### create_test_context()

Located in `tests/fakes/context.py`:

```python
from tests.fakes.context import create_test_context

# Minimal context (all fakes with defaults)
ctx = create_test_context()

# Custom git_ops
ctx = create_test_context(
    git_ops=FakeGitOps(worktrees={...})
)

# Custom config_ops
ctx = create_test_context(
    global_config_ops=FakeGlobalConfigOps(
        workstacks_root=Path("/tmp/ws")
    )
)

# Dry-run mode
ctx = create_test_context(dry_run=True)
```

## Common Test Fixtures

Recommended fixtures to add to `conftest.py`:

```python
@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Create a fake git repository for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    return repo

@pytest.fixture
def test_context() -> WorkstackContext:
    """Create minimal test context with all fakes."""
    return create_test_context()
```

## Summary

**Key Principles**:

1. Use ABC-based interfaces (not Protocol)
2. Inject dependencies through constructor (no mutation after creation, except for state-tracking operations)
3. Three implementations: Real, Dry-Run (for writes), Fake (for tests)
4. No mock.patch or monkeypatch (except documented edge cases)
5. Unit tests use Fakes, Integration tests use Reals
6. Mutation tracking via read-only properties

**When in Doubt**:

- Use `create_test_context()` helper
- Configure fakes via constructor parameters
- Inject via `obj=test_ctx` to Click commands
- Assert on results and mutation tracking properties
