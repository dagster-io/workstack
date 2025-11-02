# Workstack Architecture

**Last Updated**: 2025-10-07
**Status**: Living document

---

## Table of Contents

- [System Purpose](#system-purpose)
- [Core Concepts](#core-concepts)
- [Architecture Overview](#architecture-overview)
- [Module Organization](#module-organization)
- [Dependency Graph](#dependency-graph)
- [Command Execution Flow](#command-execution-flow)
- [Key Design Patterns](#key-design-patterns)
- [Testing Architecture](#testing-architecture)
- [Integration Points](#integration-points)
- [Design Decisions](#design-decisions)
- [Quick Navigation](#quick-navigation)

---

## System Purpose

Workstack is a CLI tool that manages git worktrees in a centralized location with:

- **Automatic environment setup** - Each worktree gets configured env vars
- **Graphite integration** - Optional integration with graphite stack management
- **GitHub PR tracking** - Display PR status alongside worktrees
- **Shell activation** - Automatic environment activation when switching worktrees

**Core Problem Solved**: Managing multiple feature branches without switching branches in a single working directory. Instead, each branch gets its own directory (worktree) with proper environment configuration.

---

## Core Concepts

See [GLOSSARY.md](../GLOSSARY.md) for detailed term definitions. Key concepts:

- **Worktree**: Git's native feature for multiple working directories
- **Workstack**: A _managed_ worktree with additional features (config, env vars)
- **Repo Root**: Original git repository directory (contains `.git/`)
- **Work Dir**: Global directory containing all workstacks for a specific repo
- **Workstacks Root**: Top-level directory for all managed repos (e.g., `~/worktrees/`)

**Relationship**:

```
~/.workstack/config.toml  (global config)
    ↓
~/worktrees/              (workstacks root)
    ├── workstack/        (work dir for "workstack" repo)
    │   ├── feature-a/    (individual workstack)
    │   ├── feature-b/    (individual workstack)
    │   └── config.toml   (repo-specific config)
    └── other-repo/       (work dir for another repo)
```

---

## Architecture Overview

### Layer Architecture

Workstack uses a **3-layer architecture**:

```
┌─────────────────────────────────────────┐
│         CLI Layer (Commands)            │  User-facing commands
│   commands/*.py                         │  Click decorators
└────────────────┬────────────────────────┘
                 │
                 │ uses WorkstackContext
                 ↓
┌─────────────────────────────────────────┐
│       Core Layer (Business Logic)       │  Pure functions
│   core.py, config.py, tree.py          │  No side effects
│   graphite.py                           │
└────────────────┬────────────────────────┘
                 │
                 │ calls through context
                 ↓
┌─────────────────────────────────────────┐
│    Operations Layer (External I/O)      │  ABC interfaces
│   gitops.py, github_ops.py              │  Real & Fake impls
│   graphite_ops.py, global_config_ops.py │  DryRun wrappers
└─────────────────────────────────────────┘
```

**Key Principle**: Dependencies flow downward only. Commands never directly call subprocess or filesystem operations.

---

## Module Organization

### Root Packages (`src/workstack/`)

**CLI Package (`cli/`)**

- `cli/cli.py` - CLI entry point and Click command registration
- `cli/__init__.py` - Exposes `cli` group for `workstack` console script
- `cli/core.py` - Repo discovery, worktree path helpers, validation
- `cli/config.py` - Repository config loading (`config.toml`)
- `cli/tree.py` - Tree rendering helpers for `workstack tree`
- `cli/graphite.py` - Graphite stack helpers consumed by commands
- `cli/shell_utils.py` - Shared shell helper utilities
- `cli/shell_integration/` - Shell wrapper scripts + handler used by `workstack __shell`
- `cli/commands/` - Individual Click commands (see below)

**Core Package (`core/`)**

- `core/context.py` - `WorkstackContext` creator + dependency injection wiring
- `core/gitops.py` - Git worktree operations (ABC + real + dry-run wrappers)
- `core/global_config_ops.py` - Global config management
- `core/github_ops.py` - GitHub CLI integrations
- `core/graphite_ops.py` - Graphite CLI integrations
- `core/file_utils.py` - File helpers shared across layers

**Status Package (`status/`)**

- `status/orchestrator.py` - Coordinates collectors and renderers
- `status/collectors/` - Git, Graphite, GitHub, and plan file collectors
- `status/models/` - Pydantic-style data structures for status payloads
- `status/renderers/` - Output renderers (currently `SimpleRenderer`)

**Developer CLI (`dev_cli/`)**

- PEP 723 powered scripts for maintenance tasks (see `src/workstack/dev_cli/CLAUDE.md`)

### Commands (`src/workstack/cli/commands/`)

Each command is a self-contained module:

| Command                   | Purpose                                             |
| ------------------------- | --------------------------------------------------- |
| `create.py`               | Create new worktree with plan file support          |
| `list.py`                 | List worktrees with PR status/graphite info         |
| `remove.py`               | Remove worktree and optionally delete branch        |
| `switch.py`               | Switch worktrees, generate shell activation         |
| `sync.py`                 | Sync with graphite, identify merged PRs             |
| `init.py`                 | Initialize global/repo config, shell setup          |
| `config.py`               | Manage configuration (list/get/set)                 |
| `completion.py`           | Generate shell completion scripts                   |
| `gc.py`                   | Garbage collect merged worktrees                    |
| `rename.py`               | Rename worktree (move directory)                    |
| `tree.py`                 | Display tree visualization                          |
| `move.py`                 | Move current branch into a new or existing worktree |
| `status.py`               | Aggregate git/graphite/GitHub/plan status           |
| `prepare_cwd_recovery.py` | Print shell snippet to recover current directory    |

### Testing (`tests/`)

```
tests/
├── fakes/                    # In-memory implementations
│   ├── gitops.py            # FakeGitOps
│   ├── github_ops.py        # FakeGitHubOps
│   ├── graphite_ops.py      # FakeGraphiteOps
│   └── global_config_ops.py # FakeGlobalConfigOps
├── commands/                 # Command-level tests
│   ├── test_rm.py
│   ├── test_switch.py
│   ├── list/                # Complex tests in subdirectory
│   └── ...
├── core/                     # Core logic tests
└── integration/              # Real git integration tests
```

---

## Dependency Graph

### Module Dependencies

```
cli/cli.py
  │
  ├──> core/context.py ──> gitops.py (ABC)
  │                      ├──> github_ops.py (ABC)
  │                      ├──> graphite_ops.py (ABC)
  │                      └──> global_config_ops.py (ABC)
  │
  └──> cli/commands/*.py
         │
         ├──> cli/core.py ───> core/context.py (types only)
         ├──> cli/config.py
         ├──> cli/tree.py ───> cli/graphite.py ───> core/graphite_ops.py
         ├──> cli/shell_utils.py ───> core/gitops.py (via context)
         └──> status/orchestrator.py (status command only)
                                └──> status/collectors/* (may use context ops)
```

**Import Rules**:

1. Commands _never_ import `core/*_ops.py` directly — all external effects flow through the injected `WorkstackContext`.
2. Shared CLI helpers live under `workstack.cli.*` and may depend on `core` operations through the context.
3. The status package depends on both CLI helpers and `core` ops but has no knowledge of individual commands.
4. Operations (`workstack.core.*`) remain leaf modules with no imports from CLI or status layers.

### Data Flow

```
User Input (CLI)
    ↓
Click Command Handler (cli/commands/*.py)
    ↓
WorkstackContext (injected via @click.pass_obj)
    ↓
Core Business Logic (core.py functions)
    ↓
Ops Interfaces (via ctx.git_ops, ctx.github_ops, etc.)
    ↓
Real Implementations (RealGitOps, RealGitHubOps, etc.)
    ↓
Subprocess / Filesystem / External APIs
```

---

## Command Execution Flow

### Detailed Flow Example: `workstack create my-feature`

```
1. User runs: workstack create my-feature
   ↓
2. cli/cli.py main() called
   ↓
3. create_context(dry_run=False) creates WorkstackContext
   - Instantiates RealGitOps()
   - Instantiates RealGlobalConfigOps()
   - Instantiates RealGitHubOps()
   - Instantiates RealGraphiteOps()
   ↓
4. Click routes to create_cmd() in cli/commands/create.py
   ↓
5. create_cmd receives WorkstackContext via @click.pass_obj
   ↓
6. Calls discover_repo_context(ctx, Path.cwd())
   - Walks up directory tree to find .git
   - Gets workstacks root from ctx.global_config_ops
   - Returns RepoContext(root, repo_name, workstacks_dir)
   ↓
7. Validates worktree name doesn't already exist
   - Calls ctx.git_ops.list_worktrees(repo.root)
   - RealGitOps runs: git worktree list --porcelain
   ↓
8. Creates new worktree
   - Calls ctx.git_ops.add_worktree(repo.root, branch, path)
   - RealGitOps runs: git worktree add -b branch path
   ↓
9. Sets up environment
   - Loads config from workstacks_dir/config.toml
   - Writes .env file to worktree
   ↓
10. Runs post-create commands
    - Executes commands from config.post_create
    ↓
11. Success message displayed via click.echo()
```

### Error Handling Flow

```
Exception in Real Ops (e.g., git command fails)
    ↓
subprocess.CalledProcessError raised
    ↓
Bubbles up through Core Layer (no try/except)
    ↓
Bubbles up through Command Layer
    ↓
Click catches at CLI boundary
    ↓
User sees error message and traceback
```

**Key Principle**: LBYL (Look Before You Leap) - Check conditions proactively rather than catching exceptions.

See: [docs/EXCEPTION_HANDLING.md](../docs/EXCEPTION_HANDLING.md) for complete guide.

---

## Key Design Patterns

### 1. ABC-Based Dependency Injection

**Why**: Enables testing with in-memory fakes, no filesystem I/O in unit tests.

**Pattern**:

```python
# 1. Define ABC interface
class GitOps(ABC):
    @abstractmethod
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        ...

# 2. Real implementation
class RealGitOps(GitOps):
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        result = subprocess.run(["git", "worktree", "list", ...], ...)
        return parse_worktrees(result.stdout)

# 3. Fake for testing
class FakeGitOps(GitOps):
    def __init__(self, *, worktrees: list[WorktreeInfo] | None = None):
        self._worktrees = worktrees or []

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        return self._worktrees

# 4. Inject via context
ctx = WorkstackContext(
    git_ops=RealGitOps(),  # or FakeGitOps() in tests
    ...
)
```

**Benefits**:

- Fast tests (no subprocess calls)
- Deterministic tests (no filesystem state)
- Easy to mock edge cases
- Clear interface contracts

### 2. Frozen Dataclass Contexts

**Why**: Prevents accidental mutation during command execution.

**Pattern**:

```python
@dataclass(frozen=True)
class WorkstackContext:
    git_ops: GitOps
    global_config_ops: GlobalConfigOps
    github_ops: GitHubOps
    graphite_ops: GraphiteOps
    dry_run: bool
```

**Benefits**:

- Immutable = thread-safe
- Clear dependencies
- Type-safe access
- Cannot be modified after creation

### 3. Pure Core Functions

**Why**: Easier to reason about, test, and refactor.

**Pattern**:

```python
def discover_repo_context(ctx: WorkstackContext, start: Path) -> RepoContext:
    """Pure function: takes context + input, returns output.

    No side effects. All external interactions through ctx.
    """
    # Uses ctx.git_ops and ctx.global_config_ops
    # Returns new RepoContext
    # Doesn't modify anything
```

**Benefits**:

- Predictable behavior
- Easy to test
- Composable
- No hidden side effects

### 4. Click Context Passing

**Why**: Standardized way to pass dependencies through command hierarchy.

**Pattern**:

```python
@click.command("create")
@click.argument("name")
@click.pass_obj  # ← Receives WorkstackContext
def create_cmd(ctx: WorkstackContext, name: str) -> None:
    # ctx is the WorkstackContext created in cli.py
    repo = discover_repo_context(ctx, Path.cwd())
    ctx.git_ops.add_worktree(repo.root, name, path)
```

### 5. Dry-Run Wrapper Pattern

**Why**: Allow users to preview destructive operations without executing them.

**Pattern**:

```python
class DryRunGitOps(GitOps):
    def __init__(self, wrapped: GitOps) -> None:
        self._wrapped = wrapped

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        # Read-only: delegate to wrapped
        return self._wrapped.list_worktrees(repo_root)

    def remove_worktree(self, repo_root: Path, path: Path, force: bool) -> None:
        # Destructive: print instead of execute
        click.echo(f"[DRY RUN] Would remove worktree: {path}")
```

---

## Testing Architecture

### Test Types

**Unit Tests** (fast, isolated):

- Use `FakeGitOps`, `FakeGitHubOps`, etc.
- Use `CliRunner.isolated_filesystem()` for filesystem tests
- No subprocess calls
- Test business logic in isolation

**Integration Tests** (slower, real git):

- Use `RealGitOps` with temporary repositories
- Test git interactions work correctly
- Located in `tests/integration/`

### Fake Pattern

**Key Rule**: All state configured via constructor, NO public setup methods.

```python
# ✅ CORRECT: State via constructor
git_ops = FakeGitOps(
    worktrees=[
        WorktreeInfo(path=Path("/repo/main"), branch="main", ...),
        WorktreeInfo(path=Path("/repo/feature"), branch="feature", ...),
    ],
    git_common_dirs={Path("/repo"): Path("/repo/.git")},
)

# ❌ WRONG: Setup methods
git_ops = FakeGitOps()
git_ops.add_worktree(...)  # No such method!
```

**Why**: Forces test to be explicit about initial state, prevents order-dependent bugs.

See: [tests/CLAUDE.md](../../tests/CLAUDE.md) for details.

---

## Integration Points

### Git Integration (`gitops.py`)

**Operations**:

- List worktrees: `git worktree list --porcelain`
- Add worktree: `git worktree add -b <branch> <path>`
- Remove worktree: `git worktree remove <path> [--force]`
- Move worktree: `git worktree move <source> <dest>`
- Get/checkout branches
- Detect default branch: `git symbolic-ref refs/remotes/origin/HEAD`

**Error Handling**: All git errors bubble up as `subprocess.CalledProcessError`.

### GitHub Integration (`github_ops.py`)

**Operations**:

- Get all PRs: `gh pr list --repo <repo> --json ...`
- Get PR status: Parse PR state, checks, reviews

**Graceful Degradation**: If `gh` CLI not available, operations return `None`.

### Graphite Integration (`graphite_ops.py`)

**For complete gt mental model**: See [tools/gt.md](tools/gt.md)

**Operations**:

- Get graphite URL: Construct web URL for repo
- Sync: `gt repo sync`

**Optional**: Graphite features only available if `use_graphite` config is true.

### Configuration Storage

**Global Config**: `~/.workstack/config.toml`

```toml
workstacks_root = "/Users/you/worktrees"
use_graphite = true
show_pr_info = true
```

**Repo Config**: `<workstacks_root>/<repo>/config.toml`

```toml
[env]
DATABASE_URL = "postgresql://localhost/dev_db"

[[post_create]]
command = ["uv", "sync"]
```

---

## Design Decisions

### Why ABC instead of Protocol?

**Decision**: Use `abc.ABC` for all interfaces.

**Rationale**:

- Explicit inheritance is more discoverable
- Runtime validation of complete implementations
- Better IDE support
- Clearer intent: this is a formal interface contract

### Why frozen dataclasses?

**Decision**: Use `@dataclass(frozen=True)` for all contexts and data classes.

**Rationale**:

- Prevents accidental mutation
- Makes data flow explicit
- Thread-safe by default
- Easier to reason about

### Why LBYL over EAFP?

**Decision**: Prefer checking conditions before operations (LBYL) over catching exceptions (EAFP).

**Rationale**:

- Makes error conditions explicit
- Prevents using exceptions for control flow
- More predictable behavior
- Easier to test edge cases

See: [docs/EXCEPTION_HANDLING.md](../docs/EXCEPTION_HANDLING.md) for complete guide.

### Why no relative imports?

**Decision**: Always use absolute imports (`from workstack.config import load_config`).

**Rationale**:

- Clearer where modules live
- Easier to move code around
- Avoids ambiguity
- Better for tooling

---

## Quick Navigation

### "I want to..."

- **Understand terminology** → [GLOSSARY.md](GLOSSARY.md)
- **Find where feature lives** → [FEATURE_INDEX.md](FEATURE_INDEX.md)
- **See module details** → [docs/MODULE_MAP.md](docs/MODULE_MAP.md)
- **See code examples** → [docs/PATTERNS.md](../docs/PATTERNS.md)
- **Write tests** → [../tests/CLAUDE.md](../tests/CLAUDE.md)

---

## Related Documentation

- [GLOSSARY.md](GLOSSARY.md) - Term definitions
- [FEATURE_INDEX.md](FEATURE_INDEX.md) - Feature → file mapping
- [.agent/docs/MODULE_MAP.md](docs/MODULE_MAP.md) - Detailed module guide
- [CLAUDE.md](CLAUDE.md) - Coding standards
- [README.md](README.md) - User-facing documentation
