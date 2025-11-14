---
description: "Worktree management and parallel development"
url: "https://github.com/dagster-io/workstack"
---

# Workstack Mental Model

**Last Updated**: 2025-10-13

A comprehensive guide to understanding workstack's mental model, command structure, and workflow patterns for managing git worktrees.

---

## Table of Contents

- [What is Workstack?](#what-is-workstack)
- [Core Mental Model](#core-mental-model)
- [Terminology](#terminology)
- [Configuration](#configuration)
- [Command Reference](#command-reference)
- [Workflow Patterns](#workflow-patterns)
- [Integration Points](#integration-points)
- [Practical Examples](#practical-examples)
- [Key Insights for AI Agents](#key-insights-for-ai-agents)
- [Additional Resources](#additional-resources)

---

## What is Workstack?

Workstack is a CLI tool that manages git worktrees in a centralized location with automatic environment setup and integration with modern development tools.

### The Problem It Solves

Without workstack, parallel feature development requires:

1. Constant branch switching in a single directory
2. Manual environment reconfiguration per branch
3. Lost context when switching between features
4. Risk of accidental commits to wrong branch
5. Slow context switching (IDE reindexing, etc.)

With workstack, you can:

- Work on multiple features simultaneously without branch switching
- Each feature has its own isolated directory with configured environment
- Instant switching between features
- Track PR status alongside worktrees
- Integrate with Graphite for stacked diffs

### Core Philosophy

**Separate workspaces for separate work.** Each feature branch gets its own directory (worktree) with proper environment configuration, eliminating the cognitive overhead of branch switching.

---

## Core Mental Model

### The Four-Layer Directory Structure

Workstack organizes worktrees in a predictable hierarchy:

```
~/.workstack/
└── config.toml                          ← Global config

~/worktrees/                             ← Workstacks root (configurable)
├── workstack/                           ← Work dir (per repo)
│   ├── config.toml                      ← Repo-specific config
│   ├── feature-a/                       ← Individual workstack
│   │   ├── .env                         ← Auto-generated env vars
│   │   ├── .PLAN.md                     ← Optional plan file (gitignored)
│   │   └── ... (source code)
│   └── feature-b/                       ← Another workstack
└── other-repo/                          ← Work dir for another repo
    └── ...

/Users/you/projects/workstack/           ← Repo root (original clone)
└── .git/                                ← Git metadata (shared by all worktrees)
```

**Key Insight**: The repo root stays clean for planning and reference, while all active development happens in isolated workstacks.

### The Resource Model

Workstack operates on these core resources:

```
Repository Root
├── Repo Context
│   ├── root: Path to original .git directory
│   ├── repo_name: Repository name
│   └── work_dir: Directory containing all workstacks for this repo
└── Workstacks (in work_dir)
    ├── Worktree 1 (name → branch)
    ├── Worktree 2 (name → branch)
    └── ...
```

**Naming Convention**: Worktrees are identified by _name_ (directory), not branch:

```bash
# Create worktree named "auth" with branch "feature/user-auth"
workstack create auth --branch feature/user-auth

# Switch using the worktree name
workstack switch auth
```

### Context Resolution

Workstack is **location-aware**. It automatically detects:

1. **Repository**: Walks up from current directory to find `.git`
2. **Current worktree**: Determines which workstack you're in (or root)
3. **Work directory**: Based on repo name and global config
4. **Configuration**: Combines global + repo-specific settings

This means commands adapt based on where you run them:

```bash
# In repo root
workstack status    # Shows: "Currently in root worktree"

# In a workstack
cd ~/worktrees/workstack/feature-a
workstack status    # Shows: "feature-a [feature-a]"
```

---

## Terminology

### Core Concepts

| Term                | Definition                                              | Example                              |
| ------------------- | ------------------------------------------------------- | ------------------------------------ |
| **Worktree**        | Git's native feature for multiple working directories   | Created by `git worktree add`        |
| **Workstack**       | A configured worktree with environment setup            | Created by `workstack create`        |
| **Repo Root**       | Original git repository directory containing `.git/`    | `/Users/you/projects/workstack`      |
| **Work Dir**        | Directory containing all workstacks for a specific repo | `~/worktrees/workstack/`             |
| **Workstacks Root** | Top-level directory for all configured repos            | `~/worktrees/`                       |
| **Worktree Path**   | Absolute path to a specific workstack                   | `~/worktrees/workstack/my-feature/`  |
| **Trunk Branch**    | Default branch of the repository (main/master)          | `main`                               |
| **Stack**           | Graphite concept: linear chain of dependent branches    | main → feature-1 → feature-1-part-2  |
| **Plan File**       | Markdown file containing implementation plans           | `.PLAN.md` (gitignored)              |
| **Root Worktree**   | Special name for the original repo root directory       | Accessed via `workstack switch root` |

### Resource Identifiers

Worktrees are identified by **name** (not branch):

```bash
# Create worktree with custom name and branch
workstack create auth --branch feature/user-authentication

# Operations use worktree name
workstack switch auth
workstack rm auth
workstack rename auth user-auth
```

**Branch detection:**

```bash
# Worktree name = branch name by default
workstack create my-feature           # Creates worktree "my-feature" with branch "my-feature"

# Explicit branch name
workstack create feat --branch my-feature  # Worktree "feat", branch "my-feature"
```

### Configuration Hierarchy

Configuration flows from global to repo-specific:

```
~/.workstack/config.toml (global)
  ↓ (defines workstacks_root, use_graphite, etc.)
~/worktrees/<repo>/config.toml (repo-specific)
  ↓ (defines env vars, post_create commands)
Individual worktrees inherit combined config
```

---

## Configuration

### Global Configuration

**Location**: `~/.workstack/config.toml`

**Created by**: `workstack init`

```toml
workstacks_root = "/Users/you/worktrees"
use_graphite = true              # Auto-detected if gt CLI installed
show_pr_info = true              # Display PR status (requires gh CLI)
shell_setup_complete = true      # Shell integration configured
```

### Repo Configuration

**Location**: `{workstacks_root}/{repo_name}/config.toml`

**Created by**: `workstack init` (when run inside a repo)

```toml
[env]
# Template variables: {worktree_path}, {repo_root}, {name}
DATABASE_URL = "postgresql://localhost/{name}_db"
API_KEY = "${SECRET_API_KEY}"
WORKTREE_PATH = "{worktree_path}"  # Auto-provided
REPO_ROOT = "{repo_root}"          # Auto-provided

[[post_create]]
command = ["uv", "venv"]
working_dir = "."

[[post_create]]
command = ["uv", "pip", "install", "-e", "."]
working_dir = "."
```

### Environment Variables

Automatically exported when switching worktrees:

- `WORKTREE_PATH` - Absolute path to current worktree
- `REPO_ROOT` - Absolute path to repository root
- `WORKTREE_NAME` - Name of current worktree

Plus any variables defined in `[env]` section.

### Configuration Presets

Use presets for common project types:

```bash
# List available presets
workstack init --list-presets

# Use a preset
workstack init --preset dagster

# Common presets:
# - auto: Auto-detect project type
# - generic: Minimal setup
# - dagster: Dagster-specific setup
```

**Dagster preset example:**

```toml
[env]
DAGSTER_GIT_REPO_DIR = "{worktree_path}"

[[post_create]]
command = ["uv", "venv"]
[[post_create]]
command = ["uv", "run", "make", "dev_install"]
```

---

## Command Reference

### Initialization & Configuration

#### `workstack init`

Initialize workstack for a repository.

```bash
# Full setup (global + repo + shell integration)
workstack init

# Repo config only
workstack init --repo

# Shell integration only
workstack init --shell

# With preset
workstack init --preset dagster

# List available presets
workstack init --list-presets

# Force overwrite existing config
workstack init --force
```

**What it does:**

1. Creates `~/.workstack/config.toml` (if not exists)
2. Creates `{work_dir}/config.toml` (repo-specific)
3. Sets up shell integration (optional)
4. Adds `.PLAN.md` to `.gitignore`

#### `workstack config`

Manage configuration.

```bash
# List all configuration
workstack config list

# Get specific value
workstack config get workstacks_root
workstack config get use_graphite

# Set value
workstack config set workstacks_root /custom/path
workstack config set use_graphite false
workstack config set show_pr_info true
```

#### `workstack completion`

Generate shell completion scripts.

```bash
# Bash
workstack completion bash > ~/.workstack-completion.bash
source ~/.workstack-completion.bash

# Zsh
workstack completion zsh > ~/.workstack-completion.zsh
source ~/.workstack-completion.zsh

# Fish
workstack completion fish > ~/.config/fish/completions/workstack.fish
```

### Creating Worktrees

#### `workstack create`

Create a new worktree.

```bash
# Basic creation (name = branch)
workstack create my-feature

# Custom branch name
workstack create feat --branch feature/my-feature

# From existing branch
workstack create --from-branch existing-feature
workstack create my-work --from-branch feature/existing

# Move current branch to new worktree
workstack create --from-current-branch

# Create from plan file
workstack create --plan implementation-plan.md
workstack create auth --plan add-auth.md

# Skip post-create commands
workstack create my-feature --no-post

# Custom base ref
workstack create my-feature --ref develop
```

**Branch creation logic:**

- `create NAME`: Creates new branch `NAME` from current HEAD
- `create NAME --branch BRANCH`: Creates new branch `BRANCH`
- `create --from-branch BRANCH`: Uses existing branch `BRANCH`
- `create --from-current-branch`: Moves current branch to worktree

**Plan file behavior:**

```bash
workstack create --plan plan.md my-feature
# 1. Creates worktree ~/worktrees/repo/my-feature/
# 2. Moves plan.md → ~/worktrees/repo/my-feature/.PLAN.md
# 3. .PLAN.md is gitignored (not committed)
```

#### `workstack jump`

Jump to a branch by finding which worktree contains it.

```bash
# Jump to a branch (finds the worktree containing it)
workstack jump feature/user-auth

# With script output for shell integration
workstack jump my-feature --script
```

**How it works:**

1. Searches all worktrees for the specified branch in their Graphite stack lineage
2. If exactly one worktree contains the branch, switches to it and checks out the branch
3. If multiple worktrees contain the branch:
   - If exactly one has it directly checked out, uses that one
   - Otherwise, shows disambiguation error

**Requirements:**

- Graphite must be enabled
- Branch must exist in at least one worktree's stack

**Use cases:**

- "I know the branch name, find me the right worktree"
- Quick navigation when you don't remember which worktree has a branch
- Switching between features by branch name rather than worktree name

**Note:** If the branch exists in the stack lineage of multiple worktrees and none have it checked out, you'll need to use `workstack switch <worktree-name>` to disambiguate first.

### Listing & Viewing

#### `workstack list` / `workstack ls`

List all worktrees.

```bash
# Basic list
workstack list
# Output:
# root [main]
# feature-a [feature-a]
# feature-b [feature/bug-fix]

# With Graphite stacks and PR info
workstack list --stacks
# Output:
# root [main]
#   ◉  main
#
# feature-a [feature-a]
#   ◯  main
#   ◉  feature-a ✅ #123
#
# feature-b [feature/bug-fix]
#   ◯  main
#   ◉  feature/bug-fix 🚧 #456

# With detailed CI checks
workstack list --checks
```

**PR Status Indicators:**

- ✅ All checks passing
- ❌ Some checks failing
- 🟣 Merged
- 🚧 Draft
- ⭕ Closed
- ◯ Open (no checks)

**Stack Indicators:**

- ◉ Current branch
- ◯ Parent branch
- ├─ Stack relationship

#### `workstack status`

Show current worktree status.

```bash
workstack status

# Output (in root):
# Currently in root worktree

# Output (in workstack):
# feature-a [feature-a]
# PR: #123 ✅
```

#### `workstack tree`

Show tree visualization of worktrees with dependencies.

```bash
workstack tree

# Output:
# main [@root]
# ├─ feature-a [@feature-a]
# │  └─ feature-a-2 [@feature-a-2]
# └─ feature-b [@feature-b]
```

**Note**: Requires Graphite to be enabled. Shows only branches with active worktrees.

### Switching Worktrees

#### `workstack switch`

Switch to a different worktree by name.

```bash
# Switch to named worktree
workstack switch my-feature

# Switch to repo root
workstack switch root
```

**What happens on switch:**

1. Outputs shell commands to change directory
2. Activates environment (sources `.env` if exists)
3. Exports `WORKTREE_PATH`, `REPO_ROOT`, `WORKTREE_NAME`
4. Runs activation script if configured

**Shell integration required**: `workstack init --shell` sets up shell function that evaluates output.

#### `workstack up`

Move to child branch in Graphite stack.

```bash
# Navigate to child branch's worktree
workstack up

# With script output for shell integration
workstack up --script
```

**How it works:**

1. Determines the child branch of your current branch in the Graphite stack
2. Finds the worktree containing that child branch
3. Switches to that worktree and activates its environment

**Requirements:**

- Graphite must be enabled
- Current branch must have a child in the stack
- Child branch must have an existing worktree

**Example:**

```bash
# Current stack: main -> feature-1 -> feature-2 -> feature-3
# You are in: feature-2

workstack up       # → Switches to feature-3's worktree
```

**Use case:** Navigate up the dependency chain when working on stacked PRs.

#### `workstack down`

Move to parent branch in Graphite stack.

```bash
# Navigate to parent branch's worktree
workstack down

# With script output for shell integration
workstack down --script
```

**How it works:**

1. Determines the parent branch of your current branch in the Graphite stack
2. Finds the worktree containing that parent branch
3. Switches to that worktree and activates its environment

**Requirements:**

- Graphite must be enabled
- Current branch must have a parent in the stack
- Parent branch must have an existing worktree (or navigates to root for trunk)

**Example:**

```bash
# Current stack: main -> feature-1 -> feature-2 -> feature-3
# You are in: feature-2

workstack down     # → Switches to feature-1's worktree
workstack down     # → Switches to root (main)
```

**Use case:** Navigate down the dependency chain or return to earlier work in a stack.

### Managing Worktrees

#### `workstack move`

Move or swap branches between worktrees.

```bash
# Move current branch to target worktree
workstack move target-wt

# Move from specific worktree to target
workstack move --worktree source-wt target-wt

# Swap branches (current ↔ target)
workstack move --current target-wt

# Auto-detect source from branch name
workstack move --branch feature-x target-wt

# Force without confirmation
workstack move source-wt target-wt --force
```

**Use cases:**

- Move branch to different worktree
- Swap branches between two worktrees
- Consolidate work from multiple worktrees

#### `workstack rename`

Rename a worktree (move directory).

```bash
# Rename worktree
workstack rename old-name new-name

# Dry run
workstack rename old-name new-name --dry-run
```

**Note**: Renames the worktree directory, not the branch.

#### `workstack rm` / `workstack remove`

Remove a worktree.

```bash
# Remove single worktree
workstack rm my-feature

# Force removal (skip confirmation)
workstack rm my-feature --force

# Remove worktree and entire Graphite stack
workstack rm my-feature --delete-stack

# Dry run
workstack rm my-feature --dry-run
```

**Safety checks:**

- Prompts for confirmation (unless `--force`)
- Warns if branch has unpushed changes
- Offers to delete local branch
- With `--delete-stack`: Deletes all dependent branches in Graphite stack

### Cleanup & Maintenance

#### `workstack sync`

Sync with Graphite and clean up merged worktrees.

```bash
# Sync and show cleanup candidates
workstack sync

# Force sync and auto-remove merged workstacks
workstack sync --force

# Preview without executing
workstack sync --dry-run
```

**What it does:**

1. Switches to root worktree (avoiding conflicts)
2. Runs `gt repo sync` to update branch tracking
3. Identifies worktrees with merged/closed PRs
4. Prompts for confirmation before removal (unless `--force`)
5. Switches back to original worktree

**Requirements**: Graphite CLI (`gt`) and GitHub CLI (`gh`) installed.

---

## Workflow Patterns

### Pattern 1: Basic Feature Development

**Standard workflow:**

```bash
# Create new feature
workstack create user-auth
workstack switch user-auth

# Work on feature
# ... make changes, commit ...

# Switch to another feature without losing context
workstack create bug-fix
workstack switch bug-fix

# Switch back instantly
workstack switch user-auth
```

### Pattern 2: Plan-Based Development

**Opinionated workflow separating planning from implementation:**

```bash
# 1. Plan in repo root
workstack switch root
# Create plan file: Add_User_Auth.md

# 2. Create worktree from plan
workstack create --plan Add_User_Auth.md
# Creates worktree "add-user-auth"
# Moves plan to ~/worktrees/repo/add-user-auth/.PLAN.md

# 3. Switch and implement
workstack switch add-user-auth
# Your plan is at .PLAN.md for reference during implementation

# 4. Commit only code (not plan)
git add .
git commit -m "Implement user authentication"
# .PLAN.md stays local (gitignored)
```

**Why this works:**

- Plans don't clutter PR reviews
- Each worktree has its own planning context
- Clean separation between thinking and doing
- No maintenance burden for planning artifacts

### Pattern 3: Working with Existing Branches

```bash
# Create worktree from existing branch
workstack create --from-branch feature/existing-work

# Or with custom name
workstack create my-work --from-branch feature/existing-work
```

### Pattern 4: Stacked Development with Graphite

```bash
# Create base feature
workstack create feature-base

# Create dependent feature
workstack switch feature-base
gt create feature-base-part-2
workstack create feature-base-part-2 --from-current-branch

# Navigate stack
workstack switch feature-base
workstack up                 # Move to feature-base-part-2
workstack down               # Back to feature-base

# View stack structure
workstack list --stacks
workstack tree
```

### Pattern 5: Parallel Development

```bash
# Start multiple features
workstack create feature-a
workstack create feature-b
workstack create feature-c

# List all worktrees
workstack ls

# Switch between them instantly
workstack switch feature-a   # Work on A
workstack switch feature-b   # Switch to B
workstack switch feature-a   # Back to A
```

### Pattern 6: Moving Work Between Worktrees

```bash
# Started work in wrong worktree
workstack switch wrong-worktree

# Move current branch to correct worktree
workstack move correct-worktree

# Or create new worktree from current branch
workstack create --from-current-branch
```

### Pattern 7: Cleanup After Merging

```bash
# Find merged worktrees
workstack sync --dry-run

# Auto-cleanup with sync
workstack sync --force

# Manual removal
workstack rm merged-feature
```

### Pattern 8: Environment-Specific Worktrees

```bash
# Configure repo with environment variables
cat > ~/worktrees/myrepo/config.toml << 'EOF'
[env]
DATABASE_URL = "postgresql://localhost/{name}_db"
API_PORT = "808{name}"
LOG_LEVEL = "debug"
EOF

# Each worktree gets unique environment
workstack create feature-a   # DATABASE_URL=postgresql://localhost/feature-a_db
workstack create feature-b   # DATABASE_URL=postgresql://localhost/feature-b_db
```

### Pattern 9: Custom Post-Create Setup

```bash
# Configure repo with post-create commands
cat > ~/worktrees/myrepo/config.toml << 'EOF'
[[post_create]]
command = ["npm", "install"]

[[post_create]]
command = ["npm", "run", "db:migrate"]
EOF

# Commands run automatically on worktree creation
workstack create my-feature
# Automatically runs: npm install && npm run db:migrate
```

---

## Integration Points

### Git Integration

Workstack uses git's native worktree feature:

```bash
# Workstack commands map to git commands:
workstack create feature     # → git worktree add -b feature path
workstack rm feature         # → git worktree remove path
```

**Git operations workstack uses:**

- `git worktree list --porcelain` - List all worktrees
- `git worktree add` - Create new worktree
- `git worktree remove` - Remove worktree
- `git worktree move` - Move worktree directory
- `git symbolic-ref refs/remotes/origin/HEAD` - Detect default branch
- `git rev-parse --git-common-dir` - Find repo root from worktree

### Graphite Integration

**For comprehensive Graphite documentation**: See `.agent/tools/gt.md`

When `use_graphite = true`, workstack integrates with Graphite:

```bash
# Stack navigation
workstack up                 # Navigate to child branch
workstack down               # Navigate to parent branch
workstack jump <branch>      # Jump to specific branch

# Stack visualization
workstack list --stacks      # Show stack structure
workstack tree              # Tree view with dependencies

# Sync and cleanup
workstack sync              # Run gt repo sync + cleanup
```

**Graphite commands used:**

- `gt parent` - Get parent branch
- `gt children` - Get child branches
- `gt branch info` - Get complete branch metadata
- `gt repo sync` - Sync with remote
- `gt ls` - List tracked branches

**Auto-detection**: Workstack automatically detects if `gt` CLI is installed and enables Graphite features.

#### `workstack graphite` - Machine-Readable Metadata

**Purpose**: Provide structured access to Graphite metadata for scripting and automation.

**Important**: Use native `gt` commands for interactive workflows. Use `workstack graphite` only when you need machine-readable output.

```bash
# List branches (text format - one per line)
workstack graphite branches

# List branches with full metadata (JSON)
workstack graphite branches --format json

# Tree visualization of branch hierarchy
workstack graphite branches --format tree

# Show specific stack subtree
workstack graphite branches --format tree --stack feature-a
```

**Output formats:**

1. **Text** (default): Simple list of branch names, one per line

   ```
   main
   feature-a
   feature-b
   ```

2. **JSON**: Full structured metadata for scripting

   ```json
   {
     "branches": [
       {
         "name": "main",
         "parent": null,
         "children": ["feature-a"],
         "is_trunk": true,
         "commit_sha": "abc123..."
       }
     ]
   }
   ```

3. **Tree**: Hierarchical visualization with commit info
   ```
   main (abc123f) "Initial commit"
   ├─ feature-a (def456g) "Add user authentication"
   │  └─ feature-a-tests (789hij0) "Add tests for auth"
   └─ feature-b (klm123n) "Refactor database layer"
   ```

**When to use:**

- Need JSON output for scripts or tools
- Need full branch metadata across ALL branches simultaneously
- Building automation that consumes Graphite data

**When NOT to use:**

- Getting parent/child for a single branch → Use `gt parent`, `gt children`, or `gt branch info`
- Interactive terminal work → Use native `gt` commands instead
- Creating branches → Use `gt create`
- Submitting PRs → Use `gt submit`

**Recommended practice**: For parent/child relationships, always prefer `gt parent`, `gt children`, and `gt branch info` over parsing `workstack graphite branches` output. They are faster, simpler, and more reliable.

### GitHub Integration

Requires GitHub CLI (`gh`) installed and authenticated:

```bash
# PR status in listings
workstack list --stacks
# Shows: ✅ #123, 🚧 #456, 🟣 #789

# Find merged worktrees
workstack sync --dry-run
# Identifies worktrees with merged/closed PRs
```

**GitHub commands used:**

- `gh pr list --state all --json number,headRefName,url,state,isDraft,statusCheckRollup` - Get PR info

**Graceful degradation**: If `gh` is not available, workstack continues without PR info.

### Shell Integration

Shell integration enables directory switching:

```bash
# Set up shell integration
workstack init --shell

# Adds function to ~/.zshrc or ~/.bashrc:
ws() {
    eval "$(workstack switch "$@")"
}
```

**What it provides:**

- `ws` command that actually changes directory
- Environment activation on switch
- Tab completion for worktree names

**Without shell integration**: `workstack switch` only prints commands, doesn't execute them.

---

## Practical Examples

### Example 1: Daily Development Flow

```bash
# Morning: Check current worktrees
workstack ls --stacks

# Work on feature A
ws feature-a
# ... make changes, commit ...

# Switch to urgent bug fix
ws root
workstack create hotfix-urgent
ws hotfix-urgent
# ... fix bug, commit, push ...

# Back to feature A
ws feature-a

# Check status
workstack status
```

### Example 2: Plan → Implement → PR

```bash
# 1. Plan in root
ws root
# Create plan: Add_Authentication.md

# 2. Create worktree from plan
workstack create --plan Add_Authentication.md

# 3. Implement
ws add-authentication
cat .PLAN.md              # Reference plan
# ... implement ...
git commit -m "Add authentication"

# 4. Create PR
git push -u origin add-authentication
gh pr create --fill

# 5. Check status
workstack ls --stacks     # See PR #123 ✅
```

### Example 3: Stacked Features

```bash
# Base feature
workstack create api-v2
ws api-v2
# ... implement base API ...
git commit -m "Add API v2 base"

# Dependent feature
gt create api-v2-auth
workstack create api-v2-auth --from-current-branch
ws api-v2-auth
# ... implement auth on top of API v2 ...
git commit -m "Add authentication to API v2"

# Navigate stack
workstack tree
# api-v2 [@api-v2]
# └─ api-v2-auth [@api-v2-auth]

ws api-v2              # Base
workstack up           # → api-v2-auth
```

### Example 4: Environment Isolation

```bash
# Configure repo for environment isolation
cat > ~/worktrees/myapp/config.toml << 'EOF'
[env]
DATABASE_URL = "postgresql://localhost/{name}_db"
REDIS_URL = "redis://localhost/{name}"
API_PORT = "300{name}"
EOF

# Each worktree gets unique environment
workstack create user-service
ws user-service
echo $DATABASE_URL  # postgresql://localhost/user-service_db
echo $API_PORT      # 300user-service (would need numeric hashing in real use)

workstack create payment-service
ws payment-service
echo $DATABASE_URL  # postgresql://localhost/payment-service_db
```

### Example 5: Cleanup Workflow

```bash
# After merging several PRs on GitHub

# Find merged worktrees
workstack sync --dry-run
# Output:
# feature-a [feature-a] - merged (PR #123)
# feature-b [feature-b] - merged (PR #124)

# Manual cleanup
workstack rm feature-a
workstack rm feature-b

# Or automatic cleanup
workstack sync --force
# Syncs with Graphite and removes all merged worktrees
```

### Example 6: Moving Work

```bash
# Started feature in wrong worktree
ws old-feature
# ... did work ...
git status  # Uncommitted changes

# Oops, should be in different worktree
git add .
git commit -m "WIP"

# Move to correct worktree
workstack move correct-feature
ws correct-feature
# Branch is now here
```

### Example 7: Custom Setup

```bash
# Configure Python project
cat > ~/worktrees/myproject/config.toml << 'EOF'
[[post_create]]
command = ["uv", "venv"]

[[post_create]]
command = ["uv", "pip", "install", "-e", ".[dev]"]

[[post_create]]
command = ["pre-commit", "install"]

[env]
PYTHONPATH = "{worktree_path}/src"
ENV = "dev"
EOF

# New worktrees automatically set up
workstack create new-feature
# Runs: uv venv && uv pip install -e .[dev] && pre-commit install
ws new-feature
# Environment already configured
```

---

## Key Insights for AI Agents

### Architecture Understanding

**3-Layer Architecture:**

```
CLI Commands (commands/*.py)
    ↓ uses
Core Business Logic (core.py, config.py, tree.py)
    ↓ uses
Operations Layer (gitops.py, github_ops.py, graphite_ops.py)
```

**Key Principle**: Commands never directly execute subprocess or filesystem operations. All external I/O goes through injected operations interfaces.

### Dependency Injection Pattern

Workstack uses ABC-based dependency injection:

```python
@dataclass(frozen=True)
class WorkstackContext:
    git_ops: GitOps                  # ABC interface
    github_ops: GitHubOps            # ABC interface
    graphite_ops: GraphiteOps        # ABC interface
    global_config_ops: GlobalConfigOps
    dry_run: bool

# Real implementations
ctx = WorkstackContext(
    git_ops=RealGitOps(),
    github_ops=RealGitHubOps(),
    # ...
)

# Test implementations
ctx = WorkstackContext(
    git_ops=FakeGitOps(worktrees=[...]),
    github_ops=FakeGitHubOps(prs=[...]),
    # ...
)
```

**For testing**: Use `FakeGitOps`, `FakeGitHubOps`, etc. from `tests/fakes/`.

### Key Design Patterns

1. **LBYL (Look Before You Leap)**: Check conditions before operations

   ```python
   # ✅ CORRECT
   if key in mapping:
       value = mapping[key]

   # ❌ WRONG
   try:
       value = mapping[key]
   except KeyError:
       pass
   ```

2. **Frozen Dataclasses**: All contexts and data structures are immutable

   ```python
   @dataclass(frozen=True)
   class RepoContext:
       root: Path
       repo_name: str
       work_dir: Path
   ```

3. **Pure Functions**: Core logic has no side effects

   ```python
   def discover_repo_context(ctx: WorkstackContext, start: Path) -> RepoContext:
       # Pure function - takes inputs, returns output
       # All side effects through ctx
   ```

### Common Operations

**Discover repository context:**

```python
from workstack.cli.core import discover_repo_context

repo = discover_repo_context(ctx, Path.cwd())
# Returns: RepoContext(root, repo_name, work_dir)
```

**List worktrees:**

```python
worktrees = ctx.git_ops.list_worktrees(repo.root)
# Returns: list[WorktreeInfo]
```

**Load configuration:**

```python
from workstack.config import load_config

config = load_config(repo.work_dir)
# Returns: Config with env vars and post_create commands
```

### Error Handling

Exceptions bubble up to CLI boundary:

```python
# In operations layer
def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
    result = subprocess.run([...], check=True)  # May raise
    return parse_worktrees(result.stdout)

# No try/except in business logic
# Errors caught by Click at CLI boundary
```

### Testing Guidelines

1. **Use fakes for unit tests**: `FakeGitOps`, `FakeGitHubOps`
2. **Use isolated filesystem**: `CliRunner().isolated_filesystem()`
3. **Configure fakes via constructor**: No setup methods
4. **Integration tests**: Use real git in temporary repos

**Example test:**

```python
from tests.fakes.gitops import FakeGitOps
from workstack.core.context import WorkstackContext

def test_list_worktrees():
    git_ops = FakeGitOps(
        worktrees=[
            WorktreeInfo(path=Path("/repo/main"), branch="main", ...),
            WorktreeInfo(path=Path("/repo/feature"), branch="feature", ...),
        ]
    )
    ctx = WorkstackContext(git_ops=git_ops, ...)

    worktrees = ctx.git_ops.list_worktrees(Path("/repo"))
    assert len(worktrees) == 2
```

### Location-Aware Commands

Commands behave differently based on current directory:

```python
# Discover current context
repo = discover_repo_context(ctx, Path.cwd())

# Different behavior in root vs worktree
current_branch = ctx.git_ops.get_current_branch(Path.cwd())
if current_branch == repo.default_branch:
    # In root worktree
else:
    # In feature worktree
```

### Graphite Integration

Check if Graphite is available:

```python
if ctx.global_config and ctx.global_config.use_graphite:
    # Use Graphite features
    parent = ctx.graphite_ops.get_parent_branch(branch)
```

### GitHub Integration

PR status gracefully degrades:

```python
prs = ctx.github_ops.get_prs(repo.root)
if prs is None:
    # gh not available or not authenticated
    # Continue without PR info
else:
    # Show PR status
```

---

## Additional Resources

- **GitHub Repository**: https://github.com/dagster-io/workstack
- **Issues**: https://github.com/dagster-io/workstack/issues
- **Git Worktree Docs**: https://git-scm.com/docs/git-worktree
- **Graphite CLI**: https://graphite.com/
- **GitHub CLI**: https://cli.github.com/

### Internal Documentation (for contributors)

- **[ARCHITECTURE.md](.agent/ARCHITECTURE.md)** - System design and patterns
- **[GLOSSARY.md](GLOSSARY.md)** - Terminology reference
- **[FEATURE_INDEX.md](.agent/FEATURE_INDEX.md)** - Feature → file mapping
- **[AGENTS.md](AGENTS.md)** - Coding standards
- **[tests/AGENTS.md](tests/AGENTS.md)** - Testing guidelines
