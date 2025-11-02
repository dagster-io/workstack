# Feature Index

Quick reference for locating feature implementations, tests, and related code.

**Purpose**: Fast lookup table for "where is feature X implemented?" questions.

**Format**: All file paths are relative to repository root.

---

## Table of Contents

- [Core Features](#core-features)
- [Git Operations](#git-operations)
- [GitHub Operations](#github-operations)
- [Graphite Operations](#graphite-operations)
- [Configuration](#configuration)
- [Core Business Logic](#core-business-logic)
- [Shell Integration](#shell-integration)
- [How to Use This Index](#how-to-use-this-index)

---

## Core Features

| Feature            | Implementation                                                      | Tests                                                              | Notes                                            |
| ------------------ | ------------------------------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------ |
| Create worktree    | `src/workstack/cli/commands/create.py`                              | `tests/commands/test_plan.py`                                      | Plan file support, branch creation               |
| Switch worktree    | `src/workstack/cli/commands/switch.py`                              | `tests/commands/test_switch.py`                                    | Shell activation, env loading                    |
| List worktrees     | `src/workstack/cli/commands/list.py`                                | `tests/commands/list/test_basic.py`                                | PR status optional, graphite stacks              |
| Remove worktree    | `src/workstack/cli/commands/remove.py`                              | `tests/commands/test_rm.py`                                        | Branch deletion, force flag                      |
| Rename worktree    | `src/workstack/cli/commands/rename.py`                              | `tests/commands/test_rename.py`                                    | Directory move + git update                      |
| Tree visualization | `src/workstack/cli/commands/tree.py`<br>`src/workstack/cli/tree.py` | `tests/commands/test_tree.py`                                      | Graphite stack hierarchy                         |
| Move worktree      | `src/workstack/cli/commands/move.py`                                | `tests/test_move.py`                                               | Move/swap branches across worktrees              |
| Jump to branch     | `src/workstack/cli/commands/jump.py`                                | `tests/commands/test_jump.py`                                      | Navigate between stack branches                  |
| Status overview    | `src/workstack/cli/commands/status.py`                              | `tests/commands/test_status_with_fakes.py`<br>`tests/unit/status/` | Aggregate repo/worktree status                   |
| Initialize config  | `src/workstack/cli/commands/init.py`                                | N/A                                                                | Presets, shell integration                       |
| Manage config      | `src/workstack/cli/commands/config.py`                              | N/A                                                                | Get/set/list operations                          |
| Prepare recovery   | `src/workstack/cli/commands/prepare_cwd_recovery.py`                | `tests/commands/test_prepare_cwd_recovery.py`                      | Print shell snippet for PWD restore              |
| Garbage collection | `src/workstack/cli/commands/gc.py`                                  | N/A                                                                | Merged PR identification                         |
| Graphite branches  | `src/workstack/cli/commands/gt.py`                                  | `tests/commands/graphite/test_gt_branches.py`                      | `workstack graphite` - machine-readable metadata |
| Sync with graphite | `src/workstack/cli/commands/sync.py`                                | `tests/test_sync.py`                                               | PR detection, cleanup                            |
| Shell completion   | `src/workstack/cli/commands/completion.py`                          | `tests/commands/test_completion.py`                                | Bash/zsh/fish support                            |

---

## Git Operations

All git operations are defined in `src/workstack/core/gitops.py`.

| Operation             | ABC Interface | Real Implementation | Fake Implementation     | Description                                 |
| --------------------- | ------------- | ------------------- | ----------------------- | ------------------------------------------- |
| List worktrees        | `gitops.py`   | `gitops.py`         | `tests/fakes/gitops.py` | Parse `git worktree list --porcelain`       |
| Add worktree          | `gitops.py`   | `gitops.py`         | `tests/fakes/gitops.py` | `git worktree add -b <branch> <path>`       |
| Remove worktree       | `gitops.py`   | `gitops.py`         | `tests/fakes/gitops.py` | `git worktree remove <path> [--force]`      |
| Move worktree         | `gitops.py`   | `gitops.py`         | `tests/fakes/gitops.py` | `git worktree move <source> <dest>`         |
| Get current branch    | `gitops.py`   | `gitops.py`         | `tests/fakes/gitops.py` | `git branch --show-current`                 |
| Checkout branch       | `gitops.py`   | `gitops.py`         | `tests/fakes/gitops.py` | `git checkout <branch>`                     |
| Detect default branch | `gitops.py`   | `gitops.py`         | `tests/fakes/gitops.py` | `git symbolic-ref refs/remotes/origin/HEAD` |
| Delete branch         | `gitops.py`   | `gitops.py`         | `tests/fakes/gitops.py` | Branch deletion with graphite support       |
| Get git common dir    | `gitops.py`   | `gitops.py`         | `tests/fakes/gitops.py` | Worktree support via `git rev-parse`        |
| Get branch head       | `gitops.py`   | `gitops.py`         | `tests/fakes/gitops.py` | Get commit SHA at branch head               |

**Integration Tests**: `tests/integration/test_gitops_integration.py`

---

## GitHub Operations

All GitHub operations are defined in `src/workstack/core/github_ops.py`.

| Operation     | ABC Interface   | Real Implementation | Fake Implementation         | Description                           |
| ------------- | --------------- | ------------------- | --------------------------- | ------------------------------------- |
| Get all PRs   | `github_ops.py` | `github_ops.py`     | `tests/fakes/github_ops.py` | `gh pr list --json` with full PR data |
| Get PR status | `github_ops.py` | `github_ops.py`     | `tests/fakes/github_ops.py` | Parse PR state, checks, reviews       |

**Notes**:

- Gracefully handles missing `gh` CLI (returns `None`)
- Used for PR status display and merged PR detection

---

## Graphite Operations

All graphite operations are defined in `src/workstack/core/graphite_ops.py`.

**For comprehensive gt documentation**: See [tools/gt.md](tools/gt.md)

| Operation        | ABC Interface     | Real Implementation | Fake Implementation           | Description                             |
| ---------------- | ----------------- | ------------------- | ----------------------------- | --------------------------------------- |
| Get graphite URL | `graphite_ops.py` | `graphite_ops.py`   | `tests/fakes/graphite_ops.py` | Construct web URL for repo              |
| Get all branches | `graphite_ops.py` | `graphite_ops.py`   | `tests/fakes/graphite_ops.py` | Read Graphite cache for branch metadata |
| Sync             | `graphite_ops.py` | `graphite_ops.py`   | `tests/fakes/graphite_ops.py` | Run `gt repo sync` command              |

**Related**:

- Graphite metadata loading: `src/workstack/cli/graphite.py`
- Stack parsing and branch relationships

---

## Configuration

| Feature        | Implementation                                                                       | Tests                               | Description                           |
| -------------- | ------------------------------------------------------------------------------------ | ----------------------------------- | ------------------------------------- |
| Global config  | `src/workstack/core/global_config_ops.py`                                            | N/A                                 | `~/.workstack/config.toml` management |
| Repo config    | `src/workstack/cli/config.py`                                                        | `tests/core/test_config_and_env.py` | `{work_dir}/config.toml` loading      |
| Config presets | `src/workstack/cli/presets/dagster.toml`<br>`src/workstack/cli/presets/generic.toml` | `tests/core/test_setup_template.py` | Template configurations               |

**Global Config Operations** (`global_config_ops.py`):

- `get_workstacks_root()` - Resolve workstacks root directory (Path)
- `get_use_graphite()` - Feature flag for Graphite integration
- `get_shell_setup_complete()` - Whether shell wrappers are installed
- `get_show_pr_info()` - Display PR details in `workstack list`
- `get_show_pr_checks()` - Display CI status in PR info
- `set(...)` - Sentinel-based update helper (creates file if missing)
- `exists()` - Does `~/.workstack/config.toml` exist?
- `get_path()` - Return the config file path for messaging

**Repo Config** (`config.py`):

- `load_config(work_dir)` - Load TOML config
- Returns `LoadedConfig` with `env` dict and `post_create` list

---

## Core Business Logic

| Feature           | Implementation                         | Tests                                      | Description                        |
| ----------------- | -------------------------------------- | ------------------------------------------ | ---------------------------------- |
| Repo discovery    | `src/workstack/cli/core.py`            | N/A                                        | Walk tree to find `.git` directory |
| Path construction | `src/workstack/cli/core.py`            | N/A                                        | `worktree_path_for()` helper       |
| Work dir creation | `src/workstack/cli/core.py`            | N/A                                        | `ensure_work_dir()` helper         |
| Name validation   | `src/workstack/cli/core.py`            | N/A                                        | Safety checks for removal          |
| Worktree naming   | `src/workstack/cli/commands/create.py` | `tests/core/test_naming.py`                | Generate names from branches       |
| Branch detection  | `src/workstack/core/gitops.py`         | `tests/core/test_detect_default_branch.py` | Detect main vs master              |
| Dagster detection | `src/workstack/cli/commands/init.py`   | `tests/core/test_detect_dagster.py`        | Auto-detect dagster projects       |
| Stack loading     | `src/workstack/cli/graphite.py`        | N/A                                        | Load graphite metadata             |
| Tree building     | `src/workstack/cli/tree.py`            | N/A                                        | Build visualization tree           |

**Key Types**:

- `RepoContext` - Repo root + work dir (`src/workstack/cli/core.py`)
- `WorkstackContext` - DI container (`src/workstack/core/context.py`)
- `LoadedConfig` - Parsed config (`src/workstack/cli/config.py`)

---

## Shell Integration

| Feature               | Implementation                                          | Description                                   |
| --------------------- | ------------------------------------------------------- | --------------------------------------------- |
| Bash activation       | `src/workstack/cli/shell_integration/bash_wrapper.sh`   | Source in `.bashrc`                           |
| Zsh activation        | `src/workstack/cli/shell_integration/zsh_wrapper.sh`    | Source in `.zshrc`                            |
| Fish activation       | `src/workstack/cli/shell_integration/fish_wrapper.fish` | Source in `config.fish`                       |
| Shell handler         | `src/workstack/cli/shell_integration/handler.py`        | Unified handler for shell-integrated commands |
| Shell command entry   | `src/workstack/cli/commands/shell_integration.py`       | Hidden `__shell` command for wrappers         |
| Completion generation | `src/workstack/cli/commands/completion.py`              | Generate shell-specific completions           |

**Shell Integration Pattern**: The `switch`, `sync`, and `create` commands support a hidden `--script` flag that outputs shell code instead of regular output. Shell wrapper functions use the unified `__shell` command to invoke these commands in script mode.

**Setup**:

- Automatic setup via `workstack init` command
- Manual setup via `workstack completion <shell>` output

**Activation Script Features**:

- `ws` command for quick worktree switching
- Automatic environment variable loading
- Current directory change to worktree path

---

## How to Use This Index

### Finding Implementation

1. **Search this file** for feature keyword (Cmd+F / Ctrl+F)
2. **Navigate to the referenced file** in your editor
3. **Check tests** for usage examples and edge cases

**Example**: Find where worktree removal is implemented

- Search for "Remove worktree"
- See: `src/workstack/cli/commands/remove.py`
- Tests: `tests/commands/test_rm.py`

---

### Understanding a Feature

1. **Find ABC interface** (for ops-related features)
   - Example: `core/gitops.py` for remove operation
2. **Read interface docstrings** to understand contract
3. **Check real implementation** for actual behavior
4. **Review tests** for edge cases and examples

**Example**: Understand how branch deletion works

- Interface: `core/gitops.py` (abstract method)
- Real impl: `core/gitops.py` (subprocess logic)
- Fake impl: `tests/fakes/gitops.py` (test double)

---

### Modifying a Feature

1. **Locate implementation** in this index
2. **Read [ARCHITECTURE.md](ARCHITECTURE.md)** to understand design
3. **Check [GLOSSARY.md](../GLOSSARY.md)** for terminology
4. **Modify code** following patterns in [CLAUDE.md](CLAUDE.md)
5. **Update corresponding tests**

**Example**: Add `--json` output to `workstack list`

- Find: `commands/list.py`
- Understand: Read command structure
- Modify: Add `--json` flag, format output
- Test: Update `tests/commands/list/test_basic.py`

---

### Adding a New Feature

**For new command**:

- Pattern: Study `cli/commands/rename.py` (simple) or `cli/commands/create.py` (complex)

**For new ops interface**:

- Pattern: Study `core/gitops.py` (ABC + Real + DryRun)

---

## Cross-References

### By Module

- **CLI entry** → `src/workstack/cli/cli.py`
- **Commands** → `src/workstack/cli/commands/*.py` (see [.agent/docs/MODULE_MAP.md](.agent/docs/MODULE_MAP.md))
- **Operations** → `src/workstack/core/*_ops.py` (see [ARCHITECTURE.md](ARCHITECTURE.md))
- **Testing** → `tests/fakes/*.py` (see [tests/CLAUDE.md](tests/CLAUDE.md))

### By Concept

- **Architecture overview** → [ARCHITECTURE.md](ARCHITECTURE.md)
- **Module organization** → [.agent/docs/MODULE_MAP.md](.agent/docs/MODULE_MAP.md)
- **Terminology** → [GLOSSARY.md](../GLOSSARY.md)
- **Coding standards** → [CLAUDE.md](CLAUDE.md)

---

## Maintenance

When adding or modifying features, keep this index current:

1. **Add new features** to appropriate table
2. **Update file paths** if files are moved or renamed
3. **Add new categories** if feature doesn't fit existing ones
4. **Keep test paths current** as tests are added/moved

**Frequency**: Update after each significant feature addition or refactoring.

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and patterns
- [GLOSSARY.md](../GLOSSARY.md) - Terminology reference
- [.agent/docs/MODULE_MAP.md](.agent/docs/MODULE_MAP.md) - Detailed module guide
- [CLAUDE.md](CLAUDE.md) - Coding standards
- [README.md](README.md) - User-facing documentation
