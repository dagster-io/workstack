# `workstack`

**Effortless `git` worktree management for parallel development.**

Create, switch, and manage multiple worktrees from a centralized location with automatic environment setup.

## Installation

```bash
# With uv (recommended)
uv tool install workstack

# From source
uv tool install git+https://github.com/dagster-io/workstack.git
```

## Quick Start

```bash
# Initialize in your repo
cd /path/to/your/repo
workstack init
source ~/.zshrc  # or ~/.bashrc

# Create and switch to a worktree
workstack create user-auth
workstack switch user-auth

# Switch back and clean up
workstack switch root
workstack rm user-auth
```

## Overview

`workstack` solves the pain of managing multiple `git` worktrees for parallel agenetic coding sessions.

**Key features:**

- Centralized worktrees in `~/worktrees/<repo>/<feature>/`
- Automatic environment setup (`.env`, virtual environments, activation scripts)
- Simple CLI: `create`, `switch`, `rm`, `ls`
- Plan-based development workflow
- Optional Graphite integration for stacked diffs

## Core Commands

### Creating Worktrees

```bash
# New feature branch
workstack create feature-x                          # Creates worktree 'feature-x' with branch 'feature-x'
workstack create fix --branch hotfix/bug           # Creates worktree 'fix' with branch 'hotfix/bug'

# From existing branch
workstack create --from-branch feature/login       # Creates worktree from existing branch 'feature/login'
workstack create login --from-branch feature/login # Creates worktree 'login' from branch 'feature/login'

# Move current work
workstack create --from-current-branch             # Move current branch to new worktree

# From a plan file
workstack create --plan Add_Auth.md                # Creates worktree, moves plan to .PLAN.md
```

### Managing Worktrees

```bash
workstack switch NAME            # Switch between worktrees (or 'root' for repo root)
workstack switch --up            # Navigate to child branch in Graphite stack
workstack switch --down          # Navigate to parent branch in Graphite stack
workstack jump BRANCH            # Jump to branch (finds worktree automatically)
workstack status                 # Show status of current worktree
workstack list                   # List all worktrees (alias: ls)
workstack list --stacks          # List with graphite stacks and PR status
workstack tree                   # Show tree of worktrees with dependencies
workstack rename OLD NEW         # Rename a worktree
workstack rm NAME                # Remove worktree
workstack sync                   # Sync with Graphite, show cleanup candidates
workstack sync --dry-run         # Show safe-to-delete worktrees (merged PRs)
workstack sync -f                # Sync and auto-remove merged workstacks
```

### Stack Navigation

With Graphite enabled, navigate your stacks directly:

```bash
workstack switch --up       # Move to child branch in stack
workstack switch --down     # Move to parent branch in stack
workstack jump BRANCH       # Jump to any branch in a stack (finds worktree automatically)
```

#### Jump to Branch

Find and switch to a worktree by branch name:

```bash
workstack jump feature/user-auth    # Finds worktree containing this branch
workstack jump hotfix/critical-bug  # Works with any branch in your stacks
```

**How it works:**

- Searches all worktrees to find which one contains the target branch in its Graphite stack
- Automatically switches to that worktree and checks out the branch
- No need to remember which worktree has which branch

**Requirements:**

- Graphite must be enabled (`workstack config set use_graphite true`)
- Branch must exist in at least one worktree's stack

**Behavior:**

- **One match**: Switches to the worktree and checks out the branch
- **Multiple matches**: Shows all worktrees containing the branch (choose manually with `workstack switch`)
- **No match**: Shows error with suggestion to create worktree

Example workflow:

```bash
# You have multiple worktrees with different stacks:
# - worktree "feature-work": main -> feature-1 -> feature-2 -> feature-3
# - worktree "bugfix-work": main -> bugfix-1 -> bugfix-2

workstack jump feature-2    # → Switches to "feature-work" and checks out feature-2
workstack jump bugfix-1     # → Switches to "bugfix-work" and checks out bugfix-1
```

#### Stack Navigation with Switch

Example workflow:

```bash
# Current stack: main -> feature-1 -> feature-2 -> feature-3
# You are in: feature-2

workstack switch --up       # → feature-3
workstack switch --down     # → feature-2
workstack switch --down     # → feature-1
workstack switch --down     # → root (main)
```

**Requirements:**

- Graphite must be enabled (`workstack config set use_graphite true`)
- Target branch must have an existing worktree
- If no worktree exists, shows helpful message: `workstack create <branch>`

**Behavior:**

- `--up`: Navigates to child branch (up the stack)
- `--down`: Navigates to parent branch (down toward trunk)
- At stack boundaries, shows clear error messages
- Cannot be combined with NAME argument

### Moving Branches

Move or swap branches between worktrees:

```bash
workstack move target-wt                      # Move from current to new worktree
workstack move --worktree old-wt new-wt       # Move from specific source to target
workstack move --current existing-wt          # Swap branches between worktrees
workstack move --branch feature-x new-wt      # Auto-detect source from branch name
```

Example output:

```bash
$ workstack list
root [master]
feature-a [feature-a]
feature-b [work/feature-b]

$ workstack list --stacks
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

Note: The repository root is displayed as `root` and can be accessed with `workstack switch root`.

### Visualizing Worktrees

```bash
workstack tree               # Show tree of worktrees with dependencies
```

Example output:

```bash
$ workstack tree
main [@root]
├─ feature-a [@feature-a]
│  └─ feature-a-2 [@feature-a-2]
└─ feature-b [@feature-b]
```

The `tree` command shows:

- **Only branches with active worktrees** (not all branches)
- **Dependency relationships** from Graphite stacks
- **Current worktree** highlighted in bright green
- **Worktree names** in brackets `[@name]`

**Note:** Requires Graphite to be enabled.

### Configuration

```bash
workstack init                   # Initialize in repository
workstack init --shell           # Show shell integration setup instructions
workstack init --list-presets    # List available config presets
workstack init --repo            # Initialize repo config only (skip global)
workstack config list            # Show all configuration
workstack config get KEY         # Get config value
workstack config set KEY VALUE   # Set config value
workstack completion bash/zsh/fish  # Generate shell completion script
```

## Configuration Files

**Global** (`~/.workstack/config.toml`):

```toml
workstacks_root = "/Users/you/worktrees"
use_graphite = true     # Auto-detected if gt CLI installed
show_pr_info = true     # Display PR status in list --stacks (requires gh CLI)
```

**Per-Repository** (`~/worktrees/<repo>/config.toml`):

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
workstack create feature-a
workstack switch feature-a
# ... work on feature A ...

workstack create feature-b
workstack switch feature-b
# ... work on feature B ...

workstack switch feature-a  # Instantly back to feature A
```

### Plan-Based Development

`workstack` promotes an opinionated workflow that separates planning from implementation:

**Core principles:**

- **Plan in main/master** - Keep your main branch "read-only" for planning. Since planning doesn't modify code, you can create multiple plans in parallel without worktrees.
- **Execute in worktrees** - All code changes happen in dedicated worktrees, keeping work isolated and switchable.
- **Plans as artifacts** - Each plan is a markdown file that travels with its worktree.

**Workflow:**

```bash
# 1. Stay in root repo for planning
workstack switch root

# 2. Create your plan and save it to disk (e.g. Add_User_Auth.md)

# 3. Create worktree from plan
workstack create --plan Add_User_Auth.md
# This automatically:
#   - Creates worktree named 'add-user-auth'
#   - Moves Add_User_Auth.md to worktree as .PLAN.md
#   - .PLAN.md is already in .gitignore (added by workstack init)

# 4. Switch and execute
workstack switch add-user-auth
# Your plan is now at .PLAN.md for reference during implementation
```

**Why this works:**

- Plans don't clutter PR reviews (`.PLAN.md` in `.gitignore`)
- Each worktree has its own plan context
- Clean separation between thinking and doing
- Workflow guides user to start implementation with clean context with just the .PLAN.md.

This workflow emerged from experience - checking in planning documents created noise in reviews and maintenance overhead without clear benefits.

### Moving Current Work

```bash
# Started work on main by accident?
workstack create --from-current-branch
# Creates worktree with current branch, switches you back to root
```

### Syncing and Cleanup

After merging PRs, sync your local branches and clean up:

```bash
workstack sync
# This will:
# 1. Switch to root (avoiding git conflicts)
# 2. Run gt sync to update branch tracking
# 3. Identify merged/closed PR workstacks
# 4. Prompt for confirmation before removing them
# 5. Switch back to your original worktree

# Or use -f to skip confirmation:
workstack sync -f
```

Options:

```bash
workstack sync                   # Sync and show cleanup candidates
workstack sync -f                # Force gt sync and auto-remove merged workstacks
workstack sync --dry-run         # Preview without executing
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

### `remove` / `rm` Options

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

| Option        | Description                                     |
| ------------- | ----------------------------------------------- |
| `-f, --force` | Force gt sync and auto-remove merged workstacks |
| `--dry-run`   | Show what would be done without executing       |

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

If [Graphite CLI](https://graphite.com/) is installed, `workstack` automatically uses `gt create` for proper stack tracking.

```bash
brew install withgraphite/tap/graphite
workstack init  # Auto-detects gt
```

Disable in `~/.workstack/config.toml`: `use_graphite = false`

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
workstack sync --dry-run
# Output:
#   feature-x [work/feature-x] - merged (PR #123)
#   feature-y [work/feature-y] - closed (PR #456)

workstack sync -f  # Clean up automatically
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

#### Workspace Structure

This project uses a uv workspace to organize the codebase:

```
workstack/                    # Root workspace
├── src/workstack/            # Main workstack package
├── packages/
│   └── workstack-dev/        # Development tools package
│       ├── src/workstack_dev/ # Development CLI commands
│       ├── tests/            # Dev CLI tests
│       └── pyproject.toml    # Package metadata
└── pyproject.toml            # Workspace configuration
```

**workstack-dev** is an independent package containing development tools for workstack. It provides commands for publishing to PyPI, code review, cache management, and more. It is installed as a dev dependency.

### For AI Assistants

Comprehensive, agent-optimized documentation is available in the `.agent/` directory:

- **[Architecture](.agent/ARCHITECTURE.md)** - System design, patterns, and component relationships
- **[Feature Index](.agent/FEATURE_INDEX.md)** - Complete feature catalog with implementation locations
- **[Glossary](GLOSSARY.md)** - Terminology and concept definitions
- **[Module Map](.agent/docs/MODULE_MAP.md)** - Module structure and exports
- **[Coding Patterns](docs/PATTERNS.md)** - Detailed implementation patterns with examples
- **[Exception Handling](docs/EXCEPTION_HANDLING.md)** - Complete exception handling guide
- **[workstack-dev CLI](docs/WORKSTACK_DEV.md)** - Development CLI architecture and design

See [`.agent/README.md`](.agent/README.md) for more details.

## Links

- **GitHub:** https://github.com/dagster-io/workstack
- **Issues:** https://github.com/dagster-io/workstack/issues

## License

MIT - Nick Schrock ([@schrockn](https://github.com/schrockn))

Originally developed by [@schrockn](https://github.com/schrockn), now maintained by [Dagster Labs](https://github.com/dagster-io).
