# `erk`

**Git worktree manager designed for parallelized, plan-oriented, agentic engineering workflows.**

`erk` enables true parallel development by giving each branch its own isolated workspace with preserved state. Built specifically for modern engineering workflows where AI agents and developers collaborate on multiple workstreams simultaneously, each following structured implementation plans.

## Core Design Principles

- **Parallel execution**: Multiple agents or developers can work on separate features simultaneously without environment conflicts or context pollution
- **State isolation**: Each worktree maintains complete environment independence - dependencies, build artifacts, env vars, and file system state
- **Context preservation**: Implementation context, API constraints, and design decisions persist in plan artifacts, enabling AI agents to maintain full context across sessions
- **Plan-first development**: Each worktree can be created from a structured plan (`.plan/`) that travels with the workspace, providing persistent context for both human and AI implementers
- **Agentic optimization**: Seamless integration with Claude Code for AI-driven implementation (`/erk:save-context-enriched-plan`, `/erk:implement-plan`, `/erk:create-wt-from-plan-file`)

## Why Parallel Worktrees Matter for AI-Native Engineering

Traditional git workflows assume serial development - one working directory, one active context. This breaks down when working with AI agents that can pursue multiple implementation paths simultaneously or when plans need to be executed in isolation to prevent cross-contamination of dependencies and state.

`erk` inverts the traditional model: branches contain valuable work product, while worktrees are disposable execution contexts that can be created and destroyed as needed. This enables workflows like:

```bash
# Create multiple planned implementations in parallel
erk create feat-1 # Create a branch feat-1 on worktree feat-1

erk checkout master # navigates back to root worktree, where master is checked out

erk delete feat-1 # Deletes feat-1 *worktree*. Branch remains untouched.

erk checkout feat-1 # Recreates feat-1 *worktree* checked out to feat-1 *branch*.
```

Notice that `cd` was never used while navigating between worktrees, nor was `uv sync` or `source .venv/bin/activate`. `erk` handles all of that bookkeeping.

This architecture ensures that whether you're working with AI agents, managing multiple contractors, or simply juggling several features yourself, each workstream maintains perfect isolation and context.

Note: `erk` was designed to work with `gt` (graphite) for managing stacks of branches (it uses `gt create` instead of `git co -b` when `gt` is available) and `uv` for ultrafast Python environment management. It could be generalized to other languages and tools fairly easily.

## Plan Orientation

`erk` has first-class support for planning workflows. You can create plan documents and then use the `--plan` flag on `create` to create new worktrees that contain planning documents in `.plan`, which by default is in `.gitignore`. There are also bundled claude code commands (installable via `dot-agent`) that facilitate the creation, enrichement, and implementation of these plans.

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
erk goto WORKTREE          # Jump directly to worktree by name
erk up                     # Navigate to child branch in Graphite stack
erk down                   # Navigate to parent branch in Graphite stack
erk status                 # Show status of current worktree
erk list                   # List all worktrees (alias: ls)
erk list --ci              # Fetch CI check status from GitHub (slower)
erk rename OLD NEW         # Rename a worktree
erk delete NAME            # Delete worktree
erk submit                 # Submit plan for remote AI implementation (GitHub Actions)
```

### Stack Navigation

With Graphite enabled, navigate your stacks directly:

```bash
erk goto WORKTREE     # Jump directly to worktree by name
erk up                # Move to child branch in stack
erk down              # Move to parent branch in stack
erk checkout BRANCH   # Checkout any branch in a stack (finds worktree automatically)
```

#### Checkout Branch

Find and switch to a worktree by branch name:

```bash
erk checkout feature/user-auth    # Finds worktree containing this branch
erk checkout hotfix/critical-bug  # Works with any branch in your stacks
erk checkout origin-branch        # Auto-creates from remote if not local
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
- **Branch checked out in multiple worktrees**: Shows all worktrees (choose manually with `erk checkout`)
- **Branch exists locally but not checked out**: Auto-creates worktree for the branch
- **Branch exists on origin but not locally**: Auto-creates tracking branch and worktree
- **Branch doesn't exist anywhere**: Shows error with suggestion to create new branch

Example workflow:

```bash
# You have multiple worktrees with different stacks:
# - worktree "feature-work": main -> feature-1 -> feature-2 -> feature-3
# - worktree "bugfix-work": main -> bugfix-1 -> bugfix-2

# Checkout existing branch in worktree
erk checkout feature-2    # → Switches to "feature-work" and checks out feature-2
erk checkout bugfix-1     # → Switches to "bugfix-work" and checks out bugfix-1

# Checkout unchecked local branch
erk checkout feature-4    # → Auto-creates worktree for feature-4

# Checkout remote-only branch (like git checkout origin/branch)
erk checkout hotfix-123   # → Creates tracking branch + worktree from origin/hotfix-123
```

#### Stack Navigation Commands

Navigate up and down your Graphite stack with dedicated commands:

```bash
# Current stack: main -> feature-1 -> feature-2 -> feature-3
# You are in: feature-2

erk up       # → feature-3
erk down     # → feature-1
erk down     # → root (main)
```

**Requirements:**

- Graphite must be enabled (`erk config set use_graphite true`)
- Target branch must have an existing worktree
- If no worktree exists, shows helpful message: `erk create <branch>`

**Behavior:**

- `erk up`: Navigates to child branch (up the stack toward leaves)
- `erk down`: Navigates to parent branch (down toward trunk)
- At stack boundaries, shows clear error messages

#### Direct Worktree Navigation

Jump directly to a worktree by name without needing to know which branch is checked out:

```bash
erk goto feature-work    # Jump to worktree named "feature-work"
erk goto root            # Jump to root repository
```

**How it works:**

- Switches directly to the specified worktree by name
- Works with or without Graphite enabled
- Useful when you know the worktree name but not the current branch

**Requirements:**

- Worktree must already exist (use `erk list` to see all worktrees)

**Behavior:**

- Activates the worktree and loads its environment (.env, venv)
- Shows current branch in the worktree
- Shows error with available worktree names if not found
- If you provide a branch name by mistake, suggests using `erk checkout`

**Example workflow:**

```bash
# See available worktrees
erk list
# root [master]
# feature-work [feature-1]
# bugfix-stack [bugfix-2]

# Jump directly by name
erk goto feature-work    # → Switches to feature-work worktree [feature-1]
erk goto root            # → Switches back to root [master]
```

### Consolidating Stacks

Consolidate stack branches into a single worktree by removing other worktrees containing branches from the current stack:

```bash
erk consolidate                        # Consolidate full stack (trunk to leaf)
erk consolidate --down                 # Consolidate only downstack (trunk to current)
erk consolidate feat-2                 # Consolidate trunk → feat-2 only
erk consolidate --name my-stack        # Create new worktree and consolidate into it
erk consolidate --dry-run              # Preview what would be removed
```

**How it works:**

- Removes other worktrees that contain branches from your stack
- Ensures each branch exists in only one worktree
- Useful before stack-wide operations like `gt restack`
- By default, consolidates entire stack (trunk to leaf)

**Options:**

- `BRANCH` - Optional branch name for partial consolidation (trunk → BRANCH)
- `--name NAME` - Create and consolidate into new worktree with this name
- `-f, --force` - Skip confirmation prompt
- `--dry-run` - Show what would be removed without executing
- `--down` - Only consolidate downstack (trunk to current). Cannot combine with BRANCH.
- `--script` - Output shell script for directory change

**Example workflow:**

```bash
# Current state: branches spread across multiple worktrees
# - worktree "feat-1-wt": main -> feat-1
# - worktree "feat-2-wt": main -> feat-1 -> feat-2
# - worktree "feat-3-wt": main -> feat-1 -> feat-2 -> feat-3

# Consolidate all stack branches into current worktree
erk consolidate
# Result: Only feat-3-wt remains with full stack: main -> feat-1 -> feat-2 -> feat-3
```

**Requirements:**

- Graphite must be enabled (`erk config set use_graphite true`)

### Splitting Stacks

Split a consolidated stack into individual worktrees per branch (inverse of consolidate):

```bash
erk split                              # Split entire stack
erk split --up                         # Split only upstack branches
erk split --down                       # Split only downstack branches
erk split --dry-run                    # Preview what would be created
```

**How it works:**

- Creates individual worktrees for each branch in the stack
- Inverse operation of `consolidate`
- Useful when you want to work on stack branches in parallel

**Options:**

- `-f, --force` - Skip confirmation prompts
- `--dry-run` - Show what would be created without executing
- `--up` - Only split upstack branches
- `--down` - Only split downstack branches

**Example workflow:**

```bash
# Current state: all branches in one worktree
# - worktree "feat-wt": main -> feat-1 -> feat-2 -> feat-3

# Split into individual worktrees
erk split
# Result: Three worktrees created:
# - worktree "feat-1": main -> feat-1
# - worktree "feat-2": main -> feat-1 -> feat-2
# - worktree "feat-3": main -> feat-1 -> feat-2 -> feat-3
```

**Requirements:**

- Graphite must be enabled (`erk config set use_graphite true`)

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

$ erk list
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

Note: The repository root is displayed as `root` and can be accessed with `erk checkout root`.

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
erk checkout feature-a
# ... work on feature A ...

erk create feature-b
erk checkout feature-b
# ... work on feature B ...

erk checkout feature-a  # Instantly back to feature A
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
erk checkout root

# 2. Create your plan and save it to disk (e.g. Add_User_Auth.md)

# 3. Create worktree from plan
erk create --plan Add_User_Auth.md
# This automatically:
#   - Creates worktree named 'add-user-auth'
#   - Creates .plan/ folder with plan.md (immutable) and progress.md (mutable)
#   - .plan/ is already in .gitignore (added by erk init)

# 4. Switch and execute
erk checkout add-user-auth
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

**AI-Augmented Planning:**

The manual workflow above can be fully automated using kit-installed Claude Code commands. See [Claude Code Integration](#claude-code-integration) for `/erk:save-context-enriched-plan`, `/erk:create-plan-issue-from-plan-file`, `/erk:create-wt-from-plan-file`, `/erk:implement-plan`, and `/erk:implement-planned-issue` commands that automate plan extraction, enhancement, GitHub issue creation, worktree creation, and implementation execution.

### Remote Implementation via GitHub Actions

For teams using GitHub Actions, `erk` supports **remote AI implementation** where GitHub Actions runners execute plans automatically.

#### The Submission Workflow

```bash
# 1. Create a worktree with a plan (locally)
/erk:create-wt-from-plan-file

# 2. Submit plan for remote implementation
erk submit
# This copies .plan/ → .submission/, commits, and pushes
# GitHub Actions automatically detects the push and begins implementation

# 3. Monitor progress
gh run watch --branch <your-branch>
```

**How it works:**

1. **Client-side (`erk submit`):**
   - Copies `.plan/` folder to `.submission/`
   - Commits `.submission/` folder to git
   - Pushes branch to remote
   - GitHub Actions workflow triggers automatically on push

2. **Server-side (GitHub Actions):**
   - Workflow detects `.submission/**` path in push event
   - Copies `.submission/` → `.plan/` on runner
   - Executes `/erk:implement-plan` with CI checks
   - Commits implementation changes
   - Deletes `.submission/` folder (cleanup)
   - Pushes all changes back to branch

**Key differences: `.plan/` vs `.submission/`**

| Folder         | Purpose                       | Git Tracked | When Used              |
| -------------- | ----------------------------- | ----------- | ---------------------- |
| `.plan/`       | Local implementation tracking | ❌ No       | Manual implementation  |
| `.submission/` | Remote submission signal      | ✅ Yes      | GitHub Actions trigger |

**Why two folders?**

- `.plan/` is in `.gitignore` for local work (keeps PRs clean)
- `.submission/` is committed as a signal to GitHub Actions
- This separation allows other workflows to trigger remote implementation

**Workflow configuration:**

The GitHub Actions workflow (`.github/workflows/implement-plan.yml`) triggers on:

```yaml
on:
  push:
    branches:
      - "**"
    paths:
      - ".submission/**"
```

This means any workflow or tool can create a `.submission/` folder to trigger remote AI implementation - not just `erk submit`.

**Benefits of remote implementation:**

- ✅ No local compute usage - runs on GitHub Actions runners
- ✅ Parallel implementations - multiple branches can run simultaneously
- ✅ Consistent environment - same setup across all implementations
- ✅ CI integration - automatic testing before push
- ✅ Flexible triggering - any workflow can create `.submission/` folders

## Claude Code Integration

Erk includes bundled kits that provide Claude Code artifacts for AI-assisted development workflows.

### What Are Kits?

Kits are collections of Claude Code artifacts (slash commands, agents, skills) that augment erk's core functionality. The erk and gt kits are bundled with the tool and provide automation for planning and Graphite workflows.

### AI-Augmented Planning Workflow

The traditional erk planning workflow can be fully automated with kit-installed commands:

**Traditional Approach (Manual):**

1. Discuss and plan with Claude in conversation
2. Manually copy/save plan to a markdown file
3. Run `erk create --plan <file>.md`
4. Manually track implementation progress

**AI-Augmented Approach (With Kits):**

1. Discuss and plan with Claude in conversation
2. `/erk:save-context-enriched-plan` - Automatically extracts, enhances, and saves plan
3. `/erk:create-wt-from-plan-file` - Creates worktree from saved plan
4. `/erk:implement-plan` - Executes plan with automated progress tracking

### Planning Workflow Commands

#### `/erk:save-context-enriched-plan` - Save Enhanced Plan

Extracts the implementation plan from your conversation with Claude, interactively enhances it, and saves to disk.

**What it does:**

- Extracts plan from conversation context
- Preserves semantic understanding (API quirks, architectural insights, known pitfalls)
- Asks clarifying questions to resolve ambiguities
- Suggests phase decomposition for complex plans
- Saves to `<repo-root>/<kebab-case-title>-plan.md`

**Usage:**

```bash
# In conversation with Claude after planning
/erk:save-context-enriched-plan

# With optional guidance corrections
/erk:save-context-enriched-plan "Focus on security validation in authentication phase"
```

**Why context preservation matters:**

Plans include expensive discoveries made during planning so implementing agents don't have to re-learn them. For example:

- **API quirks**: "Stripe webhooks often arrive BEFORE API response returns to client"
- **Known pitfalls**: "DO NOT use payment_intent.succeeded event alone - fires even for zero-amount test payments"

This prevents bugs and speeds up implementation. See [Context Preservation Examples](.claude/docs/erk/EXAMPLES.md) for comprehensive details.

#### `/erk:create-wt-from-plan-file` - Create Worktree from Plan

Creates a new erk worktree from a saved plan file.

**What it does:**

- Auto-detects most recent `*-plan.md` at repo root
- Runs `erk create --plan <file>`
- Moves plan to `.plan/plan.md` in new worktree
- Creates `.plan/progress.md` for tracking step completion
- Displays plan content and next steps

**Usage:**

```bash
# After running /erk:save-context-enriched-plan
/erk:create-wt-from-plan-file
```

#### `/erk:implement-plan` - Execute Implementation Plan

Executes the implementation plan in the current worktree with automated progress tracking.

**What it does:**

- Reads `.plan/plan.md` in current directory
- Creates TodoWrite entries for progress tracking
- Executes each phase sequentially following coding standards
- Updates `.plan/progress.md` with step completions
- Updates YAML front matter for `erk status` progress indicators
- Reports progress after each phase
- Runs final verification (CI checks if documented)

**Usage:**

```bash
# After switching to planned worktree
erk checkout <branch>
claude --permission-mode acceptEdits "/erk:implement-plan"
```

#### `/erk:create-plan-issue-from-plan-file` - Create GitHub Issue from Plan

Creates a GitHub issue from a persisted plan file and optionally links it to a worktree.

**What it does:**

- Auto-detects most recent `*-plan.md` at repo root (or uses plan in `.plan/` if present)
- Extracts title from plan front matter or H1 heading
- Ensures `erk-plan` label exists (creates if needed)
- Creates GitHub issue with plan content as body
- Saves issue reference to `.plan/issue.json` (if worktree exists)
- Enables progress tracking via issue comments

**Usage:**

```bash
# Create new issue from plan
/erk:create-plan-issue-from-plan-file

# Link existing issue to worktree
/erk:create-plan-issue-from-plan-file --link 123
```

#### `/erk:implement-planned-issue` - Execute Plan from GitHub Issue

Fetches a GitHub issue body and executes it as an implementation plan.

**What it does:**

- Reads `.plan/issue.json` to get issue number
- Fetches issue body from GitHub
- Saves issue body to `.plan/plan.md`
- Delegates to `/erk:implement-plan` for execution
- Posts progress comments back to the issue

**Usage:**

```bash
# After switching to planned worktree with linked issue
erk checkout <branch>
claude --permission-mode acceptEdits "/erk:implement-planned-issue"
```

### Complete Workflow Example

```bash
# 1. Plan in conversation (in root repo)
erk checkout root
# ... discuss with Claude, create implementation plan ...

# 2. Save enhanced plan to disk
/erk:save-context-enriched-plan
# Output: Saved plan to: Add_User_Auth-plan.md

# 3. Create worktree from plan
/erk:create-wt-from-plan-file
# Output: Created worktree 'add-user-auth' from plan

# 4. Switch to worktree
erk checkout add-user-auth

# 5. Execute implementation
claude --permission-mode acceptEdits "/erk:implement-plan"
# Claude implements the plan, updates progress.md, runs CI

# 6. Submit PR (optional)
/gt:submit-branch
```

### Graphite Workflow Commands

The gt kit provides commands for streamlined Graphite integration:

#### `/gt:submit-branch` - Create Commit and Submit PR

Automatically creates a git commit with AI-generated message and submits the current branch as a pull request.

**What it does:**

- Checks for uncommitted changes and commits them
- Analyzes all changes in the branch
- Generates detailed commit message
- Submits branch to Graphite and creates PR
- Updates PR metadata with structured documentation

**Usage:**

```bash
/gt:submit-branch
# Or with description hint
/gt:submit-branch "Add user authentication feature"
```

#### `/gt:update-pr` - Update Existing PR

Updates an existing PR by staging changes, committing, restacking, and submitting.

**What it does:**

- Stages all changes
- Creates commit with AI-generated message
- Runs `gt stack submit`
- Returns to original worktree

**Usage:**

```bash
/gt:update-pr
```

### Progress Tracking System

The `.plan/` folder structure enables automated progress tracking:

```
.plan/
├── plan.md       # Immutable reference (never edited during implementation)
└── progress.md   # Mutable tracking (checkboxes + YAML front matter)
```

Progress files include YAML front matter for `erk status` indicators:

```yaml
---
completed_steps: 3
total_steps: 10
---
# Progress Tracking
- [x] 1. First step
- [x] 2. Second step
- [x] 3. Third step
- [ ] 4. Fourth step
```

The `erk status` command shows:

- ⚪ Not started (0%)
- 🟡 In progress (1-99%)
- 🟢 Complete (100%)

### Available Kits

Erk bundles several kits that provide Claude Code artifacts:

- **erk** - Planning workflow commands (`/erk:save-context-enriched-plan`, `/erk:create-plan-issue-from-plan-file`, `/erk:create-wt-from-plan-file`, `/erk:implement-plan`, `/erk:implement-planned-issue`, `/erk:fix-merge-conflicts`)
- **gt** - Graphite integration (`/gt:submit-branch`, `/gt:update-pr`, `gt-graphite` skill)
- **devrun** - Development tool execution (pytest, pyright, ruff, prettier, make, gt)
- **dignified-python-313** - Python 3.13+ coding standards
- **fake-driven-testing** - Testing architecture patterns
- **fix-merge-conflicts** - Merge conflict resolution

For detailed documentation of all installed kits and their artifacts, see `.claude/docs/kit-registry.md`.

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

### Landing Stacks

Land all PRs in a Graphite stack in the correct order:

```bash
erk land-stack                         # Land full stack (trunk to leaf)
erk land-stack --down                  # Land only downstack PRs (trunk to current)
erk land-stack --dry-run               # Preview landing plan
erk land-stack -f                      # Skip confirmation prompts
erk land-stack --verbose               # Show detailed output
```

**How it works:**

- Merges all PRs sequentially from bottom of stack (first branch above trunk) upward
- After each merge, runs `gt sync -f` to rebase upstack branches onto updated trunk
- PRs are landed bottom-up because each PR depends on the ones below it
- With `--down`, lands only downstack PRs and skips rebase of upstack branches

**Options:**

- `-f, --force` - Skip confirmation prompt and proceed immediately
- `--verbose` - Show detailed output for merge and sync operations
- `--dry-run` - Show what would be done without executing merge operations
- `--down` - Only land downstack PRs (trunk to current). Skips upstack rebase.
- `--script` - Output shell script for directory change

**Use --down when:**

- You have uncommitted changes in upstack branches
- Work-in-progress in upstack branches you don't want to rebase yet

**Example workflow:**

```bash
# Stack: main -> feat-1 -> feat-2 -> feat-3 (all have open PRs)
# You are in: feat-3

# Land all PRs in order
erk land-stack
# Merges: feat-1 PR → feat-2 PR → feat-3 PR
# Each merge triggers gt sync to rebase remaining upstack branches

# Or land only downstack PRs
erk land-stack --down
# Merges: feat-1 PR → feat-2 PR
# Skips rebase of feat-3 (your current branch with WIP)
```

**Requirements:**

- Graphite must be enabled (`erk config set use_graphite true`)
- GitHub CLI (`gh`) must be installed and authenticated
- All PRs must be in mergeable state
- No uncommitted changes (unless using `--down`)

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

| Option | Description                                |
| ------ | ------------------------------------------ |
| `--ci` | Fetch CI check status from GitHub (slower) |

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

### `submit` Options

| Option      | Description                               |
| ----------- | ----------------------------------------- |
| `--dry-run` | Show what would be done without executing |

**Requirements:**

- Current directory must contain a `.plan/` folder
- Must be on a branch (not detached HEAD)
- Remote `origin` must be configured

**See also:** [Remote Implementation via GitHub Actions](#remote-implementation-via-github-actions) for complete workflow documentation.

### `consolidate` Options

| Option        | Description                                                               |
| ------------- | ------------------------------------------------------------------------- |
| `BRANCH`      | Optional branch for partial consolidation (trunk → BRANCH)                |
| `--name NAME` | Create and consolidate into new worktree with this name                   |
| `-f, --force` | Skip confirmation prompt                                                  |
| `--dry-run`   | Show what would be removed without executing                              |
| `--down`      | Only consolidate downstack (trunk to current). Cannot combine with BRANCH |
| `--script`    | Output shell script for directory change                                  |

### `split` Options

| Option        | Description                                  |
| ------------- | -------------------------------------------- |
| `-f, --force` | Skip confirmation prompts                    |
| `--dry-run`   | Show what would be created without executing |
| `--up`        | Only split upstack branches                  |
| `--down`      | Only split downstack branches                |

### `land-stack` Options

| Option          | Description                                                      |
| --------------- | ---------------------------------------------------------------- |
| `-f, --force`   | Skip confirmation prompt and proceed immediately                 |
| `-v, --verbose` | Show detailed output for merge and sync operations               |
| `--dry-run`     | Show what would be done without executing merge operations       |
| `--down`        | Only land downstack PRs (trunk to current). Skips upstack rebase |
| `--script`      | Output shell script for directory change                         |

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

**Kit-Installed Artifacts:**

Erk includes bundled kits that provide slash commands, agents, and skills for AI-assisted workflows. For comprehensive documentation of all installed kits and their artifacts, see:

- **[Kit Registry](.claude/docs/kit-registry.md)** - Complete catalog of installed kits, commands, agents, and skills
- **[Planning Workflow Commands](#claude-code-integration)** - `/erk:save-context-enriched-plan`, `/erk:create-plan-issue-from-plan-file`, `/erk:create-wt-from-plan-file`, `/erk:implement-plan`, `/erk:implement-planned-issue`
- **[Graphite Workflow Commands](#claude-code-integration)** - `/gt:submit-branch`, `/gt:update-pr`

## Links

- **GitHub:** https://github.com/dagster-io/erk
- **Issues:** https://github.com/dagster-io/erk/issues

## License

MIT - Nick Schrock ([@schrockn](https://github.com/schrockn))

Originally developed by [@schrockn](https://github.com/schrockn), now maintained by [Dagster Labs](https://github.com/dagster-io).
