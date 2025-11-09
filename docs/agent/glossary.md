# Workstack Glossary

Definitive terminology reference for the workstack project.

**Purpose**: Eliminate confusion about domain-specific terms. When in doubt about terminology, consult this document.

---

## Core Concepts

### Worktree

Git's native feature for creating additional working directories for a repository.

**Technical**: Created with `git worktree add`, allows working on multiple branches simultaneously without switching branches in a single directory.

**Example**:

```bash
git worktree add ../feature-branch feature-branch
```

### Workstack

A **managed worktree** created and maintained by the workstack tool.

**Distinction from worktree**:

- **Worktree** = git's feature (any directory managed by git worktree)
- **Workstack** = worktree + configuration + environment setup + lifecycle management

**Features**:

- Stored in standardized location (`~/worktrees/<repo>/<name>`)
- Automatic `.env` file generation
- Post-creation hook execution
- Integration with graphite/GitHub

**Example**: `workstack create my-feature` creates both a git worktree and a workstack.

### Repo Root

The main git repository directory containing `.git/` directory.

**Location**: Where you originally cloned the repository.

**Example**: If you cloned to `/Users/you/projects/workstack`, that's the repo root.

**Note**: In a worktree, `git rev-parse --git-common-dir` points back to the repo root's `.git` directory.

### Workstacks Dir

The directory containing all workstacks for a specific repository.

**Path structure**: `{workstacks_root}/{repo_name}/`

**Example**: If `workstacks_root = ~/worktrees` and repo is named `workstack`, then `workstacks_dir = ~/worktrees/workstack/`

**Contents**:

- Individual workstack directories
- `config.toml` (repo-specific configuration)

### Workstacks Root

The top-level directory containing all managed repositories' workstack directories.

**Configuration**: Set in `~/.workstack/config.toml`:

```toml
workstacks_root = "/Users/you/worktrees"
```

**Structure**:

```
~/worktrees/                    ← workstacks root
  ├── workstack/                ← workstacks dir for "workstack" repo
  │   ├── feature-a/           ← individual workstack
  │   ├── feature-b/           ← individual workstack
  │   └── config.toml
  ├── other-project/            ← workstacks dir for another repo
  │   └── ...
```

### Worktree Path

The absolute path to a specific workstack directory.

**Construction**: `{workstacks_dir}/{worktree_name}`

**Example**: `~/worktrees/workstack/my-feature/`

**Code**: `worktree_path_for(repo.workstacks_dir, "my-feature")`

---

## Git & Graphite Concepts

**For comprehensive gt documentation**: See [tools/gt.md](tools/gt.md)

### Trunk Branch

The default branch of the repository (typically `main` or `master`).

**Graphite terminology**: The "trunk" of the stack tree - the base from which all feature branches grow.

**Detection**: `git symbolic-ref refs/remotes/origin/HEAD`

### Stack

**Graphite concept**: A linear chain of dependent branches.

**Example**:

```
main (trunk)
  └─> feature-a (adds user model)
       └─> feature-a-2 (adds user controller)
            └─> feature-a-3 (adds user views)
```

**Purpose**: Break large features into reviewable chunks while maintaining dependencies.

### Default Branch

See: [Trunk Branch](#trunk-branch)

---

## Configuration Terms

### Global Config

Configuration stored in `~/.workstack/config.toml`.

**Scope**: Applies to all repositories managed by workstack.

**Location**: `~/.workstack/config.toml`

**Contents**:

```toml
workstacks_root = "/Users/you/worktrees"
use_graphite = true
show_pr_info = true
shell_setup_complete = true
```

**Access**: Via `GlobalConfigOps` interface.

### Repo Config

Configuration stored in `{workstacks_dir}/config.toml`.

**Scope**: Applies to all workstacks for a specific repository.

**Location**: `{workstacks_root}/{repo_name}/config.toml`

**Contents**:

```toml
[env]
DATABASE_URL = "postgresql://localhost/dev_db"
API_KEY = "${SECRET_API_KEY}"

[[post_create]]
command = ["uv", "sync"]
working_dir = "."
```

**Access**: Via `load_config(workstacks_dir)` function.

---

## Architecture Terms

### Repo Context

A frozen dataclass containing repository information.

**Definition**:

```python
@dataclass(frozen=True)
class RepoContext:
    root: Path        # Repo root directory
    repo_name: str    # Repository name
    workstacks_dir: Path    # Workstacks directory for this repo
```

**Creation**: `discover_repo_context(ctx, Path.cwd())`

**File**: `src/workstack/cli/core.py`

### Workstack Context

A frozen dataclass containing all injected dependencies.

**Definition**:

```python
@dataclass(frozen=True)
class WorkstackContext:
    git_ops: GitOps
    global_config_ops: GlobalConfigOps
    github_ops: GitHubOps
    graphite_ops: GraphiteOps
    dry_run: bool
```

**Purpose**: Dependency injection container passed to all commands.

**Creation**: `create_context(dry_run=False)` in `src/workstack/core/context.py`

**Usage**: Commands receive via `@click.pass_obj` decorator.

**File**: `src/workstack/core/context.py`

---

## Operations Layer Terms

### Ops Interface

An ABC (Abstract Base Class) defining operations for external integrations.

**Pattern**:

```python
class GitOps(ABC):
    @abstractmethod
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        ...
```

**Examples**:

- `GitOps` - Git operations
- `GitHubOps` - GitHub API operations
- `GraphiteOps` - Graphite CLI operations
- `GlobalConfigOps` - Configuration operations

**Purpose**: Abstraction enabling testing with fakes.

### Real Implementation

Production implementation of an ops interface that executes actual commands.

**Naming**: `Real<Interface>` (e.g., `RealGitOps`)

**Pattern**:

```python
class RealGitOps(GitOps):
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        result = subprocess.run(["git", "worktree", "list", ...])
        return parse_worktrees(result.stdout)
```

**Usage**: Instantiated in `create_context()` for production.

### Fake Implementation

In-memory implementation of an ops interface for testing.

**Naming**: `Fake<Interface>` (e.g., `FakeGitOps`)

**Location**: `tests/fakes/<interface>.py`

**Pattern**:

```python
class FakeGitOps(GitOps):
    def __init__(self, *, worktrees: list[WorktreeInfo] | None = None):
        self._worktrees = worktrees or []

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        return self._worktrees
```

**Key Rule**: All state via constructor, NO public setup methods.

**Purpose**: Fast, deterministic tests without filesystem I/O.

### Dry Run Wrapper

A wrapper around a real implementation that prints messages instead of executing destructive operations.

**Naming**: `DryRun<Interface>` (e.g., `DryRunGitOps`)

**Pattern**:

```python
class DryRunGitOps(GitOps):
    def __init__(self, wrapped: GitOps) -> None:
        self._wrapped = wrapped

    def remove_worktree(self, repo_root: Path, path: Path, force: bool) -> None:
        click.echo(f"[DRY RUN] Would remove worktree: {path}")
```

**Usage**: Wrapped around real implementations when `--dry-run` flag is used.

---

## Command-Specific Terms

### Plan File

A markdown file containing implementation plans for a feature.

**Usage**: `workstack create --plan my-plan.md my-feature`

**Behavior**:

- Plan file is moved to `.PLAN.md` in the new worktree
- `.PLAN.md` is gitignored (not committed)
- Useful for keeping implementation notes with the working code

**Example**:

```bash
# Create plan
echo "## Implementation Plan\n- Step 1\n- Step 2" > plan.md

# Create worktree from plan
workstack create --plan plan.md my-feature

# Plan is now at: ~/worktrees/workstack/my-feature/.PLAN.md
```

### Dry Run

Mode where commands print what they would do without executing destructive operations.

**Activation**: `--dry-run` flag on commands

**Behavior**:

- Read-only operations execute normally
- Destructive operations print messages prefixed with `[DRY RUN]`

**Example**:

```bash
workstack rm my-feature --dry-run
# Output: [DRY RUN] Would remove worktree: /Users/you/worktrees/workstack/my-feature
```

---

## Testing Terms

### Isolated Filesystem

A temporary directory created by Click's test runner for unit tests.

**Usage**:

```python
runner = CliRunner()
with runner.isolated_filesystem():
    # Operations here happen in temporary directory
    # Automatically cleaned up after test
```

**Purpose**: Prevent tests from affecting actual filesystem.

### Integration Test

Test that uses real implementations and filesystem operations.

**Location**: `tests/integration/`

**Characteristics**:

- Uses `RealGitOps`, actual git commands
- Slower than unit tests
- Tests real integration with external tools

**Example**: `tests/integration/test_gitops_integration.py`

### Unit Test

Test that uses fake implementations and isolated filesystem.

**Location**: `tests/commands/`, `tests/core/`

**Characteristics**:

- Uses `FakeGitOps`, `FakeGitHubOps`, etc.
- Fast (no subprocess calls)
- Majority of test suite

**Example**: `tests/commands/test_rm.py`

---

## Abbreviations

- **ABC**: Abstract Base Class (Python's `abc` module)
- **CLI**: Command Line Interface
- **DI**: Dependency Injection
- **EAFP**: Easier to Ask for Forgiveness than Permission (exception-based error handling)
- **LBYL**: Look Before You Leap (check-before-operation error handling)
- **PR**: Pull Request (GitHub)
- **TOML**: Tom's Obvious Minimal Language (configuration file format)

---

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - Coding standards
