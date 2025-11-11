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

## When to Use Fakes vs Mocks

### Prefer Fakes (Default Approach)

Fakes simulate entire subsystems in-memory and are the preferred testing approach for workstack.

**Benefits:**

- Enable comprehensive testing without external I/O (filesystem, subprocess, network)
- More maintainable than mocks (no brittle call assertions)
- Easier to understand (clear constructor parameters show test state)
- Support mutation tracking for asserting side effects
- Self-documenting test setup

**When to use fakes:**

- Testing CLI commands with git operations
- Testing configuration management
- Testing GitHub API interactions
- Testing Graphite workflows
- Testing shell completion generation
- Any scenario where you can model system behavior in-memory

**Example:**

```python
def test_with_fake():
    # Clear test setup: configure fake state via constructor
    completion_ops = FakeCompletionOps(
        bash_script="# bash completion code",
        workstack_path="/usr/local/bin/workstack"
    )
    ctx = create_test_context(completion_ops=completion_ops)

    # Run command
    result = runner.invoke(completion_bash, obj=ctx)

    # Assert behavior via mutation tracking
    assert "bash" in completion_ops.generation_calls
    assert "# bash completion code" in result.output
```

### When Mocks Make Sense

While fakes are preferred, mocking has legitimate use cases for scenarios that are difficult or impossible to fake.

**Acceptable use cases:**

1. **Error simulation** - Hardware failures, I/O errors that can't be faked
2. **Environment manipulation** - Testing behavior with specific environment variables
3. **Testing subprocess integration** - When verifying actual subprocess behavior matters
4. **External system edge cases** - Network timeouts, race conditions

**Example - Testing environment-specific behavior:**

```python
@patch.dict(os.environ, {"HOME": "/test/home"})
def test_home_directory_detection():
    # Testing that code correctly reads HOME variable
    result = detect_home_dir()
    assert result == Path("/test/home")
```

**Example - Testing subprocess error handling:**

```python
@patch("subprocess.run")
def test_subprocess_timeout(mock_run):
    # Simulating a subprocess timeout is hard to fake reliably
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="git", timeout=5)
    result = run_with_timeout()
    assert result.timed_out
```

### Decision Tree

```
Can you create a fake for this dependency?
├─ YES → Create/use a fake (preferred)
│  └─ Examples: GitOps, CompletionOps, ShellOps
│
├─ NO → Consider if mocking is necessary
   ├─ Testing error edge cases? → Mock acceptable
   ├─ Testing environment behavior? → Mock acceptable
   ├─ Testing subprocess integration? → Mock acceptable
   └─ Otherwise → Reconsider if test is needed
```

### Migration Strategy

If you encounter existing tests using mocks:

1. **Evaluate**: Does an ops abstraction exist? (GitOps, ShellOps, etc.)
2. **If yes**: Refactor to use the fake implementation
3. **If no**: Consider creating an ops abstraction + fake if the mock is complex
4. **Keep mock only if**: It falls into acceptable use cases above

This codebase has successfully migrated from 100+ mock patches to fake-based testing. The completion tests (17 tests using `@patch`) were refactored to FakeCompletionOps, demonstrating this pattern.

## Real-World Refactoring Examples

### Example 1: Repository Discovery Without Patches

**❌ Before (using mock.patch):**

```python
from unittest.mock import patch
from workstack.cli.core import RepoContext

def test_graphite_branches_json_format(tmp_path: Path) -> None:
    git_ops = FakeGitOps(git_common_dirs={tmp_path: tmp_path / ".git"})
    ctx = create_test_context(git_ops=git_ops, graphite_ops=graphite_ops)
    repo = RepoContext(root=tmp_path, repo_name="test-repo", workstacks_dir=tmp_path / "workstacks")

    runner = CliRunner()
    with patch("workstack.cli.commands.gt.discover_repo_context", return_value=repo):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(graphite_branches_cmd, ["--format", "json"], obj=ctx)
```

**✅ After (using cwd injection):**

```python
def test_graphite_branches_json_format(tmp_path: Path) -> None:
    git_ops = FakeGitOps(git_common_dirs={tmp_path: tmp_path / ".git"})
    ctx = create_test_context(
        git_ops=git_ops,
        graphite_ops=graphite_ops,
        cwd=tmp_path  # ← Set cwd to match git_common_dirs
    )

    runner = CliRunner()
    result = runner.invoke(graphite_branches_cmd, ["--format", "json"], obj=ctx)
```

**Key insight**: `discover_repo_context()` uses `ctx.git_ops.get_git_common_dir(ctx.cwd)`, so configuring FakeGitOps with `git_common_dirs` and setting matching `cwd` allows discovery to work naturally without patching.

**Files refactored**: `tests/commands/graphite/test_gt_branches.py` (4 patches eliminated)

### Example 2: Path Mocking → Real File I/O with tmp_path

**❌ Before (using mock.patch.object):**

```python
from unittest.mock import patch
from pathlib import Path

def test_graphite_ops_get_prs():
    fixture_data = '{"branches": [...]}'

    with patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "read_text", return_value=fixture_data):
        git_ops = MagicMock()
        ops = RealGraphiteOps()
        result = ops.get_prs_from_graphite(git_ops, Path("/fake/repo"))
```

**✅ After (using tmp_path fixture):**

```python
def test_graphite_ops_get_prs(tmp_path: Path):
    # Create real files in temp directory
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    pr_info_file = git_dir / ".graphite_pr_info"
    pr_info_file.write_text('{"branches": [...]}', encoding="utf-8")

    git_ops = FakeGitOps(git_common_dirs={tmp_path: git_dir})
    ops = RealGraphiteOps()
    result = ops.get_prs_from_graphite(git_ops, tmp_path)
```

**Key insight**: Integration tests should use real file I/O with `tmp_path`, not Path mocking. This tests actual file reading behavior and ensures encoding is handled correctly.

**Files refactored**: `tests/integration/test_graphite_ops.py` (20 patches/mocks eliminated)

### Example 3: Subprocess Mocks → Fake Abstractions

**❌ Before (using subprocess mock):**

```python
from unittest import mock

def test_create_uses_graphite():
    with mock.patch("subprocess.run") as mock_run:
        result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)
        # Fragile: relies on subprocess call implementation details
        assert any("gt" in str(call) for call in mock_run.call_args_list)
```

**✅ After (using FakeGraphiteOps):**

```python
def test_create_without_graphite():
    # Test the non-graphite path (uses FakeGitOps successfully)
    graphite_ops = FakeGraphiteOps()
    ctx = create_test_context(git_ops=git_ops, graphite_ops=graphite_ops, graphite=False)

    result = runner.invoke(cli, ["create", "test-feature"], obj=ctx)
    # Clear assertion on actual behavior
    assert result.exit_code == 0
    assert "test-feature" in git_ops.added_worktrees
```

**Key insight**: If command calls subprocess directly without abstraction, refactor tests to focus on paths that DO use abstractions, or test error handling before subprocess is reached.

**Files refactored**: `tests/commands/workspace/test_create.py` (2 patches eliminated)

### Example 4: Environment Variable Mocks → FakeShellOps

**❌ Before (using patch.dict):**

```python
from unittest.mock import patch
import os

def test_shell_detection_zsh():
    with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
        ops = RealShellOps()
        result = ops.detect_shell()
        assert result == ("zsh", Path.home() / ".zshrc")
```

**✅ After (using FakeShellOps):**

```python
def test_shell_detection_zsh():
    shell_ops = FakeShellOps(detected_shell=("zsh", Path.home() / ".zshrc"))
    ctx = create_test_context(shell_ops=shell_ops)

    result = runner.invoke(init_cmd, obj=ctx)
    assert "zsh" in result.output
```

**Key insight**: Use FakeShellOps for shell detection logic in unit tests. Keep integration tests with real environment for actual shell detection.

**Files refactored**: `tests/integration/test_shell_ops.py` (5 patches eliminated)

### Example 5: When Mocks ARE Legitimate

Some mocks are legitimate and should NOT be replaced:

**✅ Legitimate Mock Usage:**

```python
# tests/commands/setup/test_init.py
from unittest import mock

def test_init_creates_global_config_first_time() -> None:
    """Test that init creates global config on first run.

    Mock usage here is LEGITIMATE:
    - os.environ HOME patch: Testing path resolution that depends on $HOME
    - Cannot fake environment variables (external boundary)
    - Patching HOME redirects Path.home() to test directory
    """
    with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
        result = runner.invoke(cli, ["init"], obj=test_ctx)
```

**Why these mocks are acceptable:**
1. Testing environment variable behavior (external boundary)
2. Cannot create an abstraction for `os.environ` (it's the OS interface)
3. Documented clearly in test file docstring
4. Used consistently across related tests

**Files with legitimate mocks**: `tests/commands/setup/test_init.py` (28 mocks, all documented)

## Migration Checklist

When refactoring tests from mocks to fakes:

- [ ] Check if ops abstraction exists (GitOps, ShellOps, GraphiteOps, etc.)
- [ ] Replace mock setup with fake constructor injection
- [ ] Replace mock assertions with mutation tracking properties
- [ ] Set `cwd` in context to match fake configuration
- [ ] Use `tmp_path` for file operations instead of Path mocking
- [ ] Remove unused mock imports
- [ ] Run tests to verify behavior unchanged
- [ ] If mock remains, document why it's legitimate

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
