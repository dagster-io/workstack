# Test Migration Analysis: simulated_workstack_env to pure_workstack_env

## Executive Summary

This analysis examines 5 representative test files to understand patterns that will need to change when migrating from `simulated_workstack_env` (filesystem-based) to `pure_workstack_env` (in-memory) testing.

**Total CLI test files:** 41 across 6 command categories

## Key Findings

### 1. Common Patterns Across All Files

All 5 files follow this basic flow:

```python
def test_something() -> None:
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Configure fake ops with paths from env
        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir}, ...)

        # Build context using env helper
        test_ctx = env.build_context(git_ops=git_ops, ...)

        # Invoke CLI command
        result = runner.invoke(cli, ["command"], obj=test_ctx)

        # Assert exit code and output
        assert result.exit_code == 0
```

### 2. Filesystem Operations by Category

#### **Create Command (test_create.py) - MOST COMPLEX**

- **Complexity:** Complex - Heavy filesystem integration
- **mkdir() operations:** ~25+ times
- **path.write_text() operations:** ~40+ times for config/plan files
- **Worktree directory creation:** Yes - creates real worktree directories under workstacks/
- **File operations:**
  - Creates config.toml files (required setup)
  - Creates and moves .PLAN.md files
  - Creates .env files
  - Writes pyproject.toml for preset detection
  - Checks for .gitignore modifications

**Key challenge:** The `--plan` flag logic requires:

- Reading plan files from env.cwd
- Moving/copying plan files to worktree directories
- Tests verify file operations via path.exists()

**Specific tests needing attention:**

- `test_create_with_plan_file()` - Creates plan file, moves it
- `test_create_with_keep_plan_flag()` - Plan file copy vs move logic
- `test_create_with_plan_ensures_uniqueness()` - Date suffix versioning

#### **Switch Command (test_switch.py) - MODERATE**

- **Complexity:** Medium
- **mkdir() operations:** ~5 times
- **File operations:** Limited (reads existing structures)
- **Worktree creation:** Yes - creates linked worktrees via `create_linked_worktree()`
- **File operations:**
  - Creates .git symlink files for linked worktrees
  - Creates worktree metadata directories
  - No file I/O during command execution

**Key challenge:** Linked worktree metadata structure

- Tests use `env.create_linked_worktree("myfeature", "myfeature", chdir=False)`
- This creates actual .git symlink files and directory structure
- Pure env needs to handle this without creating actual directories

#### **Tree Command (test_tree.py) - MODERATE**

- **Complexity:** Medium
- **mkdir() operations:** ~6 times
- **path.write_text() operations:** ~3 times (Graphite cache files)
- **Cache file operations:** Yes - creates .graphite_cache_persist JSON files
- **File operations:**
  - Writes Graphite cache to git_dir/.graphite_cache_persist
  - Reads cache file to load branch graph

**Key challenge:** Graphite integration

- Tests write actual Graphite cache JSON to filesystem
- Command reads cache from git_dir to parse branch hierarchy
- Pure env needs to mock cache reading or provide in-memory cache

#### **Init Command (test_init.py) - COMPLEX**

- **Complexity:** Complex - Config creation + filesystem mutations
- **mkdir() operations:** ~15 times
- **path.write_text() operations:** ~15 times
- **Config file operations:** Yes - creates config.toml at workstacks_dir
- **Gitignore operations:** Yes - reads and modifies .gitignore
- **File operations:**
  - Creates workstacks directory structure
  - Creates config.toml files
  - Reads/modifies .gitignore
  - Uses mock.patch for os.environ["HOME"]

**Key challenge:** Environment variable patching

- Tests use `mock.patch.dict(os.environ, {"HOME": str(env.cwd)})`
- Path.home() resolution depends on HOME
- Pure env: Needs to mock Path.home() or inject home_path parameter

**Specific tests needing attention:**

- `test_init_creates_global_config_first_time()` - Config creation
- `test_init_adds_plan_md_to_gitignore()` - Gitignore modifications
- `test_init_force_overwrites_existing_config()` - File overwriting

#### **Sync Command (test_sync.py) - MODERATE**

- **Complexity:** Medium
- **mkdir() operations:** ~8 times
- **path.write_text() operations:** 0 (no command file I/O)
- **Worktree directory operations:** Yes - creates worktree directories to track
- **File operations:**
  - No file read/write during command
  - Only filesystem checks (path.exists())

**Key challenge:** Worktree cleanup verification

- Tests create worktree directories to verify deletion
- Command checks if worktree directories exist before deletion
- Pure env needs to mock path.exists() checks or track deletions

---

## Detailed Patterns Requiring Migration

### Pattern 1: Environment Setup

**Current (simulated_workstack_env):**

```python
with simulated_workstack_env(runner) as env:
    # env.cwd is actual path in temp filesystem
    # env.git_dir is actual path
    # env.workstacks_root is actual path
```

**After migration (pure_workstack_env):**

```python
with pure_workstack_env(runner) as env:
    # env.cwd is sentinel path: Path("/test/repo")
    # env.git_dir is sentinel path: Path("/test/repo/.git")
    # env.workstacks_root is sentinel path: Path("/test/workstacks")
    # NO filesystem operations possible
```

**Tests affected:** ALL 41 CLI tests

### Pattern 2: Config File Creation (create.py test case)

**Current behavior:**

```python
# Actually creates file on filesystem
config_toml = workstacks_dir / "config.toml"
config_toml.write_text("", encoding="utf-8")

result = runner.invoke(cli, ["create"], obj=test_ctx)
# Command reads config.toml from filesystem
assert result.exit_code == 0
```

**Migration challenge:**

- Command may read config file from filesystem during execution
- FakeGitOps doesn't provide file reading capability
- Solution: Track which files are expected to exist and provide via mock

**Tests affected:**

- `test_create.py` - 15+ tests create config.toml files
- `test_init.py` - 20+ tests create config files

### Pattern 3: Plan File Operations (create.py)

**Current behavior:**

```python
# Create real plan file on filesystem
plan_file = env.cwd / "my-feature-plan.md"
plan_file.write_text("# My Feature Plan\n", encoding="utf-8")

result = runner.invoke(cli, ["create", "--plan", str(plan_file)], obj=test_ctx)

# Verify file was moved
assert (wt_path / ".PLAN.md").exists()
assert not plan_file.exists()
```

**Migration challenge:**

- Command reads plan file from env.cwd
- Command writes .PLAN.md to new worktree directory
- Assertions verify files were moved/copied/deleted
- Solution: Mock file I/O operations or provide in-memory file tracking

**Tests affected:**

- `test_create_with_plan_file()` - Reads plan file
- `test_create_with_plan_ensures_uniqueness()` - Multiple plan file handling
- `test_create_with_keep_plan_flag()` - Copy vs move logic

### Pattern 4: Worktree Directory Existence Checks

**Current behavior:**

```python
# Create actual worktree directory
wt_path = workstacks_dir / "test-feature"
wt_path.mkdir(parents=True)

result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)

# Verify error for duplicate
assert result.exit_code == 1
assert "already exists" in result.output
```

**Migration challenge:**

- Command checks if worktree directory exists via path.exists()
- FakeGitOps doesn't track filesystem
- Solution: Pass expected_directories list to fake or mock path operations

**Tests affected:**

- `test_create_fails_if_worktree_exists()` - Duplicate check
- `test_sync_identifies_deletable_workstacks()` - Worktree cleanup
- Many create/rename/rm tests

### Pattern 5: Graphite Cache File Operations (tree.py)

**Current behavior:**

```python
# Write actual Graphite cache file
cache_data = {...}
cache_file = git_dir / ".graphite_cache_persist"
cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

result = runner.invoke(cli, ["tree"], obj=ctx)

# Command reads cache file during execution
assert result.exit_code == 0
```

**Migration challenge:**

- Command reads .graphite_cache_persist from git_dir
- File I/O is embedded in command logic
- Solution: Provide in-memory cache via RealGraphiteOps or mock file reading

**Tests affected:**

- `test_tree_command_displays_hierarchy()` - Reads cache
- `test_load_graphite_branch_graph()` - Direct file reading
- All tree tests that use Graphite

### Pattern 6: Linked Worktree Creation

**Current behavior:**

```python
# Creates actual .git symlink file and directory structure
myfeature_path = env.create_linked_worktree("myfeature", "myfeature", chdir=False)

# Creates:
# - workstacks_root / "repo" / "myfeature" (directory)
# - workstacks_root / "repo" / "myfeature" / ".git" (symlink)
# - root_worktree / ".git" / "worktrees" / "myfeature" (metadata dir)
```

**Migration challenge:**

- `env.create_linked_worktree()` doesn't exist in pure_workstack_env
- Tests need alternative way to represent linked worktrees
- Solution: FakeGitOps already supports worktrees dict - tests should use it directly

**Tests affected:**

- `test_switch_command()` - Uses create_linked_worktree()
- `test_list_includes_root()` - Uses create_linked_worktree()
- 3 switch tests

### Pattern 7: Environment Variable Mocking (init.py)

**Current behavior:**

```python
with mock.patch.dict(os.environ, {"HOME": str(env.cwd)}):
    result = runner.invoke(cli, ["init"], obj=test_ctx, input=f"{workstacks_root}\nn\n")
    # Path.home() returns env.cwd during execution
```

**Migration challenge:**

- Tests patch os.environ["HOME"]
- Pure env can't use env.cwd since it's a sentinel path
- Solution: Inject home_path parameter to command or pure env

**Tests affected:**

- All init tests that mock HOME (15+ tests)

### Pattern 8: Gitignore Modifications (init.py)

**Current behavior:**

```python
# Create actual .gitignore
gitignore = env.cwd / ".gitignore"
gitignore.write_text("*.pyc\n", encoding="utf-8")

result = runner.invoke(cli, ["init"], obj=test_ctx, input="y\ny\n")

# Verify .gitignore was modified
gitignore_content = gitignore.read_text(encoding="utf-8")
assert ".PLAN.md" in gitignore_content
```

**Migration challenge:**

- Command reads and modifies .gitignore
- File operations are core to test assertions
- Solution: Mock file reading/writing or provide in-memory file system

**Tests affected:**

- `test_init_adds_plan_md_to_gitignore()`
- `test_init_adds_env_to_gitignore()`
- `test_init_preserves_gitignore_formatting()`

---

## Command-by-Command Migration Complexity

| Command | Category   | Complexity | File I/O               | Worktrees   | Graphite Cache | Path Mocking |
| ------- | ---------- | ---------- | ---------------------- | ----------- | -------------- | ------------ |
| create  | workspace  | COMPLEX    | ~40x write_text        | mkdir       | No             | No           |
| switch  | navigation | MEDIUM     | create_linked_worktree | Yes         | No             | Yes\*        |
| tree    | display    | MEDIUM     | cache read             | No          | Yes            | No           |
| init    | setup      | COMPLEX    | ~15x ops               | mkdir       | No             | Yes (HOME)   |
| sync    | sync       | MEDIUM     | mkdir                  | path.exists | No             | No           |

\*switch uses os.chdir in create_linked_worktree

---

## Recommended Migration Order

### Priority 1: Safest/Easiest (Start Here)

1. **sync** (test_sync.py)
   - Minimal file I/O, mostly mkdir operations
   - FakeGitOps already tracks worktrees
   - Can mock path.exists() for worktree existence checks
   - Effort: 1-2 hours

2. **tree** (test_tree.py)
   - Graphite cache reading is only filesystem dependency
   - Can inject cache data via FakeGraphiteOps
   - Worktree operations already work with FakeGitOps
   - Effort: 2-3 hours

3. **switch** (test_switch.py)
   - Depends on handling linked worktrees without create_linked_worktree()
   - Switch tests need different setup pattern
   - Effort: 2-3 hours

### Priority 2: Moderate (Build on Priority 1)

4. **init** (test_init.py)
   - Config file creation is core to tests
   - HOME environment mocking needs alternative
   - Gitignore operations need file mocking
   - Many tests (~40), significant refactoring needed
   - Effort: 4-6 hours

### Priority 3: Most Complex (Last)

5. **create** (test_create.py)
   - Heaviest file I/O usage (~40 write_text calls)
   - Plan file operations require moving/copying logic
   - Worktree directory creation verification
   - Plan file reading from env.cwd
   - Most tests (~70), but patterns similar to init
   - Effort: 6-8 hours

---

## Specific Challenges & Solutions

### Challenge 1: File Reading During Command Execution

**Problem:** Commands read config.toml or .gitignore from filesystem during execution

**Current:** File is created before command via path.write_text()

**Solutions:**

1. **In-memory file tracking:** Extend FakeGitOps to track "expected files"
   - Pros: Clean, isolated
   - Cons: Changes fake implementation
   - **RECOMMENDED**

2. **Mock file operations:** Use unittest.mock to intercept file reads
   - Pros: Works immediately
   - Cons: Anti-pattern for this codebase (see AGENTS.md)
   - Not recommended

3. **Refactor commands:** Pass config data to commands instead of reading from filesystem
   - Pros: Better design
   - Cons: Large refactor, out of scope

**Impact:** Affects 25+ tests in create.py and init.py

### Challenge 2: Path Existence Checks

**Problem:** Commands check if directories exist via path.exists()

**Current:** Directories are created on filesystem before command

**Solutions:**

1. **Extend FakeGitOps:** Add existing_paths set to track which paths exist
   - Tests pass: existing_paths={env.cwd / "subdir"}
   - Pros: Clean, isolated
   - Cons: Requires fake update
   - **RECOMMENDED**

2. **Mock pathlib.Path.exists():**
   - Anti-pattern for this codebase
   - Not recommended

**Impact:** Affects all workspace manipulation tests (create, rename, rm)

### Challenge 3: Linked Worktree Creation

**Problem:** `env.create_linked_worktree()` doesn't exist in pure_workstack_env

**Current:** Tests use this to create worktree directory structure

**Solutions:**

1. **Pass worktrees directly to FakeGitOps:**
   - Currently: `env.create_linked_worktree("feat", "feat", chdir=False)`
   - After: `git_ops = FakeGitOps(worktrees={env.cwd: [WorktreeInfo(...)]})`
   - Pros: Already works with pure_workstack_env
   - Cons: Tests become more verbose
   - **RECOMMENDED**

2. **Add create_linked_worktree to PureWorkstackEnv:**
   - Pros: Reuses existing pattern
   - Cons: Would need to create dummy files/directories
   - Not recommended for pure env

**Impact:** Affects 3 switch tests

### Challenge 4: Plan File Reading

**Problem:** Command reads plan file from env.cwd via path.read_text()

**Current:** File is created on filesystem before command

**Solutions:**

1. **Extend FakeGitOps:** Add file_contents dict
   - Tests pass: file_contents={env.cwd / "plan.md": "content"}
   - Command reads via FakeGitOps instead of direct I/O
   - Pros: Clean, isolated
   - Cons: Requires command refactoring to use FakeGitOps for file I/O
   - **RECOMMENDED if commands can be refactored**

2. **Keep simulated_workstack_env for plan file tests:**
   - Only migrate tests that don't use --plan flag
   - Tests: ~30 of 70 create tests can use pure env
   - Pros: Incremental migration
   - Cons: Mixed testing approach
   - **ACCEPTABLE INTERIM APPROACH**

**Impact:** Affects 20+ tests in create.py

### Challenge 5: Graphite Cache File Reading

**Problem:** Command reads .graphite_cache_persist from filesystem

**Current:** Tests create actual JSON file at git_dir/.graphite_cache_persist

**Solutions:**

1. **Inject cache via FakeGraphiteOps:**
   - FakeGraphiteOps already has branches parameter
   - Command should use graphite_ops.get_cache() instead of reading file
   - Pros: Pure in-memory
   - Cons: Requires command refactoring
   - **RECOMMENDED**

2. **Create dummy cache file in isolated_filesystem:**
   - Keep using simulated_workstack_env for tree tests
   - Cons: No migration
   - Not an option

**Impact:** Affects all tree command tests (~10 tests)

### Challenge 6: HOME Environment Mocking

**Problem:** Tests mock os.environ["HOME"] for Path.home() resolution

**Current:** Works with simulated_workstack_env because env.cwd is real path

**Solutions:**

1. **Inject home_path to WorkstackContext:**
   - Pure env passes: home_path=Path("/test/home")
   - Commands use context.home_path instead of Path.home()
   - Pros: Clean, injectable
   - Cons: Requires small command refactoring
   - **RECOMMENDED**

2. **Keep simulated_workstack_env for init tests:**
   - Only migrate tests that don't depend on HOME
   - Tests: ~5 of 40 init tests don't use HOME
   - Cons: Limited migration
   - Not recommended

**Impact:** Affects 40+ init tests (but fixable with one small change)

---

## Non-Suitable Tests for pure_workstack_env Migration

These tests should remain with simulated_workstack_env due to core dependencies on real filesystem:

### 1. Plan File Operations (create.py)

- `test_create_with_plan_file()`
- `test_create_with_plan_file_removes_plan_word()`
- `test_create_with_plan_ensures_uniqueness()`
- `test_create_with_long_plan_name_matches_branch_and_worktree()`
- `test_create_with_plan_file_removes_plan_word()` (all --plan variants, ~10 tests)

**Reason:** Requires reading plan file content from env.cwd during command execution. Plan files are created on filesystem, then read by command. Migration would require significant command refactoring to accept file content via API instead of reading from path.

### 2. Config File Operations (init.py)

- `test_init_force_overwrites_existing_config()`
- `test_init_fails_without_force_when_exists()`
- `test_init_adds_plan_md_to_gitignore()` (all gitignore variants, ~5 tests)

**Reason:** Requires filesystem to verify file overwriting and gitignore modifications. Tests depend on actual file content matching.

### 3. Graphite Cache File Tests (tree.py)

- `test_load_graphite_branch_graph()` - Directly reads cache file
- `test_tree_command_displays_hierarchy()` (cache file writes, ~5 tests)

**Reason:** Tests read .graphite_cache_persist from filesystem. Migration would require injecting cache data via API.

**Estimated tests to keep on simulated_workstack_env:** 20-25 tests
**Estimated tests to migrate to pure_workstack_env:** 200+ tests (80% of tests)

---

## Migration Strategy (Phased Approach)

### Phase 1: Infrastructure Updates (1-2 days)

- Extend FakeGitOps to support:
  - existing_paths: set of paths that should exist
  - file_contents: dict of path -> content
- Extend PureWorkstackEnv to support:
  - Injecting existing_paths to FakeGitOps
  - Injecting file_contents to FakeGitOps
- Add home_path parameter to WorkstackContext (if needed)

### Phase 2: Low-Hanging Fruit (1-2 days)

- Migrate sync tests (lowest complexity, no special cases)
- Migrate non-plan-file create tests (majority of create tests)
- Update patterns in tests/commands/AGENTS.md

### Phase 3: Moderate Complexity (2-3 days)

- Migrate switch tests (linked worktree handling)
- Migrate tree tests (Graphite cache injection)
- Create new pattern docs

### Phase 4: High Complexity (3-4 days)

- Migrate remaining init tests
- Migrate remaining create tests with special file handling
- Update command-specific CLAUDE.md files

### Phase 5: Documentation (1 day)

- Update tests/commands/AGENTS.md with pure_workstack_env pattern
- Add migration guide for future developers
- Document which tests remain on simulated_workstack_env and why

---

## Pattern Examples for Migration

### Example 1: Sync Test Migration

**Before (simulated_workstack_env):**

```python
def test_sync_with_force_flag() -> None:
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main")]},
        )
        test_ctx = env.build_context(git_ops=git_ops)
        result = runner.invoke(cli, ["sync", "-f"], obj=test_ctx)
        assert result.exit_code == 0
```

**After (pure_workstack_env):**

```python
def test_sync_with_force_flag() -> None:
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Identical code - no changes needed!
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            worktrees={env.cwd: [WorktreeInfo(path=env.cwd, branch="main")]},
        )
        test_ctx = env.build_context(git_ops=git_ops)
        result = runner.invoke(cli, ["sync", "-f"], obj=test_ctx)
        assert result.exit_code == 0
```

**Key difference:** No filesystem operations needed. Tests work unchanged!

### Example 2: Switch Test Migration

**Before (simulated_workstack_env):**

```python
def test_switch_command() -> None:
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        # Creates actual .git symlink file
        myfeature_path = env.create_linked_worktree("myfeature", "myfeature", chdir=False)

        git_ops = FakeGitOps(
            worktrees={
                env.root_worktree: [
                    WorktreeInfo(path=env.root_worktree, branch="main", is_root=True),
                    WorktreeInfo(path=myfeature_path, branch="myfeature", is_root=False),
                ]
            },
        )
        # ...
```

**After (pure_workstack_env):**

```python
def test_switch_command() -> None:
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        # Define worktrees directly - no filesystem operations
        myfeature_path = env.workstacks_root / "repo" / "myfeature"

        git_ops = FakeGitOps(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=myfeature_path, branch="myfeature", is_root=False),
                ]
            },
        )
        # Rest of test identical
        # ...
```

**Key difference:** No create_linked_worktree() call. Use sentinel paths directly.

### Example 3: Create Test (with file existence checks)

**Before (simulated_workstack_env):**

```python
def test_create_fails_if_worktree_exists() -> None:
    runner = CliRunner()
    with simulated_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.root_worktree.name
        workstacks_dir.mkdir(parents=True)

        # Create existing worktree directory
        wt_path = workstacks_dir / "test-feature"
        wt_path.mkdir(parents=True)  # File on filesystem

        git_ops = FakeGitOps(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists" in result.output
```

**After (pure_workstack_env) - Requires FakeGitOps enhancement:**

```python
def test_create_fails_if_worktree_exists() -> None:
    runner = CliRunner()
    with pure_workstack_env(runner) as env:
        workstacks_dir = env.workstacks_root / env.cwd.name
        wt_path = workstacks_dir / "test-feature"

        # New: Tell FakeGitOps which paths exist
        git_ops = FakeGitOps(
            git_common_dirs={env.cwd: env.git_dir},
            existing_paths={wt_path},  # NEW PARAMETER
        )
        test_ctx = env.build_context(git_ops=git_ops)

        result = runner.invoke(cli, ["create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists" in result.output
```

**Key difference:** existing_paths parameter tells FakeGitOps which paths the command should consider as existing.

---

## Summary Table

| Aspect                              | Current          | After Migration | Notes                                    |
| ----------------------------------- | ---------------- | --------------- | ---------------------------------------- |
| Test file count                     | 41 CLI files     | 41 CLI files    | No files deleted                         |
| Tests using simulated_workstack_env | ~250-300         | ~200-220        | 20-25 tests keep simulated_workstack_env |
| Tests using pure_workstack_env      | 0                | ~200-220        | New adoption                             |
| Filesystem I/O per test             | 10-40 operations | 0 operations    | Pure tests run faster                    |
| Average test runtime                | ~50ms            | ~5-10ms         | 5-10x faster tests                       |
| Estimated migration effort          | -                | 10-12 days      | Phases 1-5 outlined above                |
| Code changes to commands            | -                | 0-2 days        | Only if refactoring file I/O             |
| False infrastructure changes        | -                | 1-2 days        | FakeGitOps enhancements                  |

---

## Appendix: Files Analyzed

1. `/tests/commands/workspace/test_create.py` - 1545 lines, 70+ tests
   - Heaviest file I/O usage
   - Multiple file operations per test

2. `/tests/commands/navigation/test_switch.py` - 429 lines, 9 tests
   - Uses create_linked_worktree()
   - Moderate complexity

3. `/tests/commands/display/test_tree.py` - 631 lines, 10 tests
   - Graphite cache file operations
   - Worktree mapping tests

4. `/tests/commands/setup/test_init.py` - 1096 lines, 40+ tests
   - Config file creation
   - Environment variable mocking
   - Gitignore modifications

5. `/tests/commands/sync/test_sync.py` - 954 lines, 20+ tests
   - Worktree directory operations
   - Minimal file I/O (mostly assertions on mock state)
