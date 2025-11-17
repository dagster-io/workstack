# `erk`

**Effortless `git` worktree management for parallel development.**

Create, switch, and manage multiple worktrees from a centralized location with automatic environment setup.

## Philosophy

erk makes git worktrees lightweight and disposable:

- **One branch per worktree** - No more `git checkout` conflicts. Each feature gets its own working directory.
- **Lightweight and ephemeral** - Create and destroy worktrees freely. Branches persist, worktrees don't.
- **Automatic environment setup** - Each worktree gets .env files, virtual environments, and activation scripts.
- **Organized in ~/.erk/repos/<repo>/worktrees/** - All worktrees for a repository in one predictable location.

Think of worktrees as "working directories for branches" rather than "branches you switch between."

## Installation

```bash
# With uv (recommended)
uv tool install erk

# From source
uv tool install git+https://github.com/dagster-io/erk.git
```

## Quick Start

```bash
# Initialize in your repo
cd /path/to/your/repo
erk init
source ~/.zshrc  # or ~/.bashrc

# Create and switch to a worktree
erk create user-auth
erk switch user-auth

# Switch back and clean up
erk checkout root
erk delete user-auth
```

## Overview

`erk` solves the pain of managing multiple `git` worktrees for parallel agenetic coding sessions.

**Key features:**

- Centralized worktrees in `~/.erk/repos/<repo>/worktrees/<feature>/`
- Automatic environment setup (`.env`, virtual environments, activation scripts)
- Simple CLI: `create`, `checkout`, `delete`, `ls`
- Plan-based development workflow
- Optional Graphite integration for stacked diffs

## Core Commands

### Creating Worktrees

```bash
# New feature branch
erk create feature-x                          # Creates worktree 'feature-x' with branch 'feature-x'
erk create fix --branch hotfix/bug           # Creates worktree 'fix' with branch 'hotfix/bug'

# From existing branch
erk create --from-branch feature/login       # Creates worktree from existing branch 'feature/login'
erk create login --from-branch feature/login # Creates worktree 'login' from branch 'feature/login'

# Move current work
erk create --from-current-branch             # Move current branch to new worktree

# From a plan file
erk create --plan Add_Auth.md                # Creates worktree with .plan/ folder
```

### Managing Worktrees

```bash
erk checkout BRANCH        # Checkout branch (finds worktree automatically)
erk co BRANCH              # Alias for checkout
erk up                     # Navigate to child branch in Graphite stack
erk down                   # Navigate to parent branch in Graphite stack
erk status                 # Show status of current worktree
erk list                   # List all worktrees (alias: ls)
erk list --stacks          # List with graphite stacks and PR status
erk rename OLD NEW         # Rename a worktree
erk delete NAME            # Delete worktree
erk sync                   # Sync with Graphite, show cleanup candidates
erk sync --dry-run         # Show safe-to-delete worktrees (merged PRs)
erk sync -f                # Sync and auto-remove merged worktrees
```

### Stack Navigation

With Graphite enabled, navigate your stacks directly:

```bash
erk up                # Move to child branch in stack
erk down              # Move to parent branch in stack
erk checkout BRANCH   # Checkout any branch in a stack (finds worktree automatically)
```

#### Jump to Branch

Find and switch to a worktree by branch name:

```bash
erk jump feature/user-auth    # Finds worktree containing this branch
erk jump hotfix/critical-bug  # Works with any branch in your stacks
erk jump origin-branch        # Auto-creates from remote if not local
```

**How it works:**

- Searches all worktrees to find which one contains the target branch in its Graphite stack
- If not found in any worktree, checks if branch exists locally
- If not local, checks if `origin/branch` exists remotely
- Automatically creates tracking branch and worktree if needed
- No need to remember which worktree has which branch

**Requirements:**

- Graphite must be enabled for stack-based search (`erk config set use_graphite true`)
- Branch auto-creation works without Graphite

**Behavior:**

- **Branch checked out in one worktree**: Switches to that worktree and checks out the branch
- **Branch checked out in multiple worktrees**: Shows all worktrees (choose manually with `erk switch`)
- **Branch exists locally but not checked out**: Auto-creates worktree for the branch
- **Branch exists on origin but not locally**: Auto-creates tracking branch and worktree
- **Branch doesn't exist anywhere**: Shows error with suggestion to create new branch

Example workflow:

```bash
# You have multiple worktrees with different stacks:
# - worktree "feature-work": main -> feature-1 -> feature-2 -> feature-3
# - worktree "bugfix-work": main -> bugfix-1 -> bugfix-2

# Jump to existing branch in worktree
erk jump feature-2    # → Switches to "feature-work" and checks out feature-2
erk jump bugfix-1     # → Switches to "bugfix-work" and checks out bugfix-1

# Jump to unchecked local branch
erk jump feature-4    # → Auto-creates worktree for feature-4

# Jump to remote-only branch (like git checkout origin/branch)
erk jump hotfix-123   # → Creates tracking branch + worktree from origin/hotfix-123
```

#### Stack Navigation with Switch

Example workflow:

```bash
# Current stack: main -> feature-1 -> feature-2 -> feature-3
# You are in: feature-2

erk switch --up       # → feature-3
erk switch --down     # → feature-2
erk switch --down     # → feature-1
erk switch --down     # → root (main)
```

**Requirements:**

- Graphite must be enabled (`erk config set use_graphite true`)
- Target branch must have an existing worktree
- If no worktree exists, shows helpful message: `erk create <branch>`

**Behavior:**

- `--up`: Navigates to child branch (up the stack)
- `--down`: Navigates to parent branch (down toward trunk)
- At stack boundaries, shows clear error messages
- Cannot be combined with NAME argument

### Moving Branches

Move or swap branches between worktrees:

```bash
erk move target-wt                      # Move from current to new worktree
erk move --worktree old-wt new-wt       # Move from specific source to target
erk move --current existing-wt          # Swap branches between worktrees
erk move --branch feature-x new-wt      # Auto-detect source from branch name
```

Example output:

```bash
$ erk list
root [master]
feature-a [feature-a]
feature-b [work/feature-b]

$ erk list --stacks
root [master]
  ◉  master

feature-a [feature-a]
  ◯  master
  ◉  feature-a ✅ #123

feature-b [work/feature-b]
  ◯  master
  ◉  work/feature-b 🚧 #456
```

**PR Status Indicators:**

- ✅ Checks passing
- ❌ Checks failing
- 🟣 Merged
- 🚧 Draft
- ⭕ Closed
- ◯ Open (no checks)

Note: The repository root is displayed as `root` and can be accessed with `erk switch root`.

### Configuration

```bash
erk init                   # Initialize in repository
erk init --shell           # Show shell integration setup instructions
erk init --list-presets    # List available config presets
erk init --repo            # Initialize repo config only (skip global)
erk config list            # Show all configuration
erk config get KEY         # Get config value
erk config set KEY VALUE   # Set config value
erk completion bash/zsh/fish  # Generate shell completion script
```

## Configuration Files

**Global** (`~/.erk/config.toml`):

```toml
erk_root = "/Users/you/.erk"  # Defaults to ~/.erk
use_graphite = true            # Auto-detected if gt CLI installed
show_pr_info = true            # Display PR status in list --stacks (requires gh CLI)
```

**Per-Repository** (`~/.erk/repos/<repo>/config.toml`):

```toml
[env]
# Template variables: {worktree_path}, {repo_root}, {name}
DATABASE_URL = "postgresql://localhost/{name}_db"

[post_create]
shell = "bash"
commands = [
  "uv venv",
  "uv pip install -e .",
]
```

## Common Workflows

### Parallel Feature Development

```bash
erk create feature-a
erk switch feature-a
# ... work on feature A ...

erk create feature-b
erk switch feature-b
# ... work on feature B ...

erk switch feature-a  # Instantly back to feature A
```

### Plan-Based Development

`erk` promotes an opinionated workflow that separates planning from implementation:

**Core principles:**

- **Plan in main/master** - Keep your main branch "read-only" for planning. Since planning doesn't modify code, you can create multiple plans in parallel without worktrees.
- **Execute in worktrees** - All code changes happen in dedicated worktrees, keeping work isolated and switchable.
- **Plans as artifacts** - Each plan is a markdown file that travels with its worktree.

**Workflow:**

```bash
# 1. Stay in root repo for planning
erk switch root

# 2. Create your plan and save it to disk (e.g. Add_User_Auth.md)

# 3. Create worktree from plan
erk create --plan Add_User_Auth.md
# This automatically:
#   - Creates worktree named 'add-user-auth'
#   - Creates .plan/ folder with plan.md (immutable) and progress.md (mutable)
#   - .plan/ is already in .gitignore (added by erk init)

# 4. Switch and execute
erk switch add-user-auth
# Your plan is now at .plan/plan.md for reference during implementation
# Progress tracking in .plan/progress.md shows step completion
```

**Why this works:**

- Plans don't clutter PR reviews (`.plan/` in `.gitignore`)
- Each worktree has its own plan context
- Clean separation between thinking and doing
- Progress tracking separates plan content from completion status
- Workflow guides user to start implementation with clean context and progress visibility

This workflow emerged from experience - checking in planning documents created noise in reviews and maintenance overhead without clear benefits.

### Moving Current Work

```bash
# Started work on main by accident?
erk create --from-current-branch
# Creates worktree with current branch, switches you back to root
```

### Syncing and Cleanup

After merging PRs, sync your local branches and clean up:

```bash
erk sync
# This will:
# 1. Switch to root (avoiding git conflicts)
# 2. Run gt sync to update branch tracking
# 3. Identify merged/closed PR worktrees
# 4. Prompt for confirmation before removing them
# 5. Switch back to your original worktree

# Or use -f to skip confirmation:
erk sync -f
```

Options:

```bash
erk sync                   # Sync and show cleanup candidates
erk sync -f                # Force gt sync and auto-remove merged erks
erk sync --dry-run         # Preview without executing
```

Requires Graphite CLI (`gt`) and GitHub CLI (`gh`) installed.

## Command Reference

### `create` Options

| Option                  | Description                         |
| ----------------------- | ----------------------------------- |
| `--branch BRANCH`       | Specify branch name (default: NAME) |
| `--ref REF`             | Base ref (default: current HEAD)    |
| `--plan FILE`           | Create from plan file               |
| `--from-current-branch` | Move current branch to worktree     |
| `--from-branch BRANCH`  | Create from existing branch         |
| `--no-post`             | Skip post-create commands           |

### `list` / `ls` Options

| Option         | Description                                     |
| -------------- | ----------------------------------------------- |
| `-s, --stacks` | Show graphite stacks and PR status              |
| `-c, --checks` | Show CI check status (requires GitHub API call) |

### `move` Options

| Option            | Description                                 |
| ----------------- | ------------------------------------------- |
| `--current`       | Use current worktree as source              |
| `--branch BRANCH` | Auto-detect worktree containing this branch |
| `--worktree NAME` | Use specific worktree as source             |
| `--ref REF`       | Fallback branch for source (default: main)  |
| `-f, --force`     | Skip confirmation prompts                   |

### `delete` / `del` Options

| Option               | Description                               |
| -------------------- | ----------------------------------------- |
| `-f, --force`        | Do not prompt for confirmation            |
| `-s, --delete-stack` | Delete all branches in Graphite stack     |
| `--dry-run`          | Show what would be done without executing |

### `rename` Options

| Option      | Description                               |
| ----------- | ----------------------------------------- |
| `--dry-run` | Show what would be done without executing |

### `sync` Options

| Option        | Description                                    |
| ------------- | ---------------------------------------------- |
| `-f, --force` | Force gt sync and auto-remove merged worktrees |
| `--dry-run`   | Show what would be done without executing      |

### `init` Options

| Option           | Description                                |
| ---------------- | ------------------------------------------ |
| `--force`        | Overwrite existing repo config             |
| `--preset NAME`  | Config template (auto/generic/dagster/etc) |
| `--list-presets` | List available presets and exit            |
| `--repo`         | Initialize repo config only (skip global)  |
| `--shell`        | Show shell integration setup instructions  |

### Environment Variables

Always exported when switching:

- `WORKTREE_PATH` - Absolute path to current worktree
- `REPO_ROOT` - Absolute path to repository root
- `WORKTREE_NAME` - Name of current worktree

## Advanced Features

### Graphite Integration

If [Graphite CLI](https://graphite.com/) is installed, `erk` automatically uses `gt create` for proper stack tracking.

```bash
brew install withgraphite/tap/graphite
erk init  # Auto-detects gt
```

Disable in `~/.erk/config.toml`: `use_graphite = false`

### Repository Presets

**Dagster:**

```toml
[env]
DAGSTER_GIT_REPO_DIR = "{worktree_path}"

[post_create]
commands = ["uv venv", "uv run make dev_install"]
```

### Cleanup

Find and clean up merged/closed PR branches:

```bash
erk sync --dry-run
# Output:
#   feature-x [work/feature-x] - merged (PR #123)
#   feature-y [work/feature-y] - closed (PR #456)

erk sync -f  # Clean up automatically
```

Requires GitHub CLI (`gh`) installed and authenticated.

## FAQ

**Q: How is this different from `git worktree`?**
A: Adds centralized management, automatic environment setup, and seamless switching.

**Q: Does it work with non-Python projects?**
A: Yes! Configure `post_create` commands for any stack.

**Q: What if I don't use Graphite?**
A: Works perfectly with standard git commands.

## Documentation

### For Developers

Core documentation for contributors:

- **[AGENTS.md](AGENTS.md)** - Coding standards and conventions (required reading)
- **[tests/AGENTS.md](tests/AGENTS.md)** - Testing patterns and practices
- **[docs/PUBLISHING.md](docs/PUBLISHING.md)** - Publishing to PyPI guide

#### Shell Integration Output Pattern

Commands that generate activation scripts should use the self-documenting `ScriptResult` API:

```python
# Generate activation script
result = ctx.script_writer.write_activation_script(
    script_content,
    command_name="mycommand",
    comment="description",
)

# Output for shell integration (--script flag)
result.output_for_shell_integration()  # ✓ Routes to stdout

# OR output for user visibility (rarely needed)
if verbose:
    result.output_path_for_user()  # Routes to stderr

# OR defer output (advanced pattern)
script_result = result  # Save for later
# ... more logic ...
if should_output:
    script_result.output_for_shell_integration()
```

This prevents bugs where script paths are written to the wrong stream (stderr instead of stdout), causing shell integration to fail. See `src/erk/core/script_writer.py` for detailed documentation.

#### Workspace Structure

This project uses a uv workspace to organize the codebase:

```
erk/                    # Root workspace
├── src/erk/            # Main erk package
├── packages/
│   └── erk-dev/        # Development tools package
│       ├── src/erk_dev/ # Development CLI commands
│       ├── tests/            # Dev CLI tests
│       └── pyproject.toml    # Package metadata
└── pyproject.toml            # Workspace configuration
```

**erk-dev** is an independent package containing development tools for erk. It provides commands for publishing to PyPI, code review, cache management, and more. It is installed as a dev dependency.

### For AI Assistants

Comprehensive, agent-optimized documentation is available in the `.agent/` directory:

- **[Architecture](.agent/ARCHITECTURE.md)** - System design, patterns, and component relationships
- **[Feature Index](.agent/FEATURE_INDEX.md)** - Complete feature catalog with implementation locations
- **[Glossary](GLOSSARY.md)** - Terminology and concept definitions
- **[Module Map](.agent/docs/MODULE_MAP.md)** - Module structure and exports
- **[Coding Patterns](docs/PATTERNS.md)** - Detailed implementation patterns with examples
- **[Exception Handling](docs/EXCEPTION_HANDLING.md)** - Complete exception handling guide
- **[erk-dev CLI](docs/ERK_DEV.md)** - Development CLI architecture and design

See [`.agent/README.md`](.agent/README.md) for more details.

## Links

- **GitHub:** https://github.com/dagster-io/erk
- **Issues:** https://github.com/dagster-io/erk/issues

## License

MIT - Nick Schrock ([@schrockn](https://github.com/schrockn))

Originally developed by [@schrockn](https://github.com/schrockn), now maintained by [Dagster Labs](https://github.com/dagster-io).
