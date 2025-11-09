---
name: workstack
description: This skill should be used when working with workstack for git worktree management and parallel development. Use when users mention workstack commands, worktree workflows, parallel feature development, or when dealing with multiple branches simultaneously. Essential for understanding workstack's mental model, command structure, and integration with Graphite for stacked PRs.
---

# Workstack

## Overview

Workstack is a CLI tool that manages git worktrees in a centralized location with automatic environment setup and integration with Graphite. This skill provides comprehensive guidance for using workstack to enable parallel development without branch switching, including configuration, workflow patterns, and command reference.

## When to Use This Skill

Invoke this skill when users:

- Mention workstack commands or worktree management
- Ask about parallel feature development or working on multiple branches
- Need help with workstack configuration or setup
- Want to understand the workstack mental model or directory structure
- Ask about integrating workstack with Graphite for stacked diffs
- Need guidance on cleanup, syncing, or maintenance workflows
- Request help with environment isolation across worktrees

## Core Concepts

Before providing guidance, understand these key concepts:

**Worktree vs Workstack:**

- **Worktree**: Git's native feature for multiple working directories
- **Workstack**: A configured worktree with environment setup and tooling integration

**Directory Structure:**

```
~/worktrees/                    ← Workstacks root (configurable)
├── repo-name/                  ← Work dir (per repo)
│   ├── config.toml             ← Repo-specific config
│   ├── feature-a/              ← Individual workstack
│   │   ├── .env                ← Auto-generated env vars
│   │   └── .PLAN.md            ← Optional plan file (gitignored)
│   └── feature-b/              ← Another workstack
└── other-repo/                 ← Work dir for another repo
```

**Key Insight**: Worktrees are identified by **name** (directory), not branch name.

## Using the Reference Documentation

When providing workstack guidance, load the comprehensive reference documentation:

```
references/workstack.md
```

This reference contains:

- Complete mental model and terminology
- Full command reference with examples
- Configuration patterns and presets
- Workflow patterns for common scenarios
- Integration details (Git, Graphite, GitHub)
- Architecture insights for contributors
- Practical examples for daily development

**Loading Strategy:**

- Always load `references/workstack.md` when user asks workstack-related questions
- The reference is comprehensive (~1200 lines) but optimized for progressive reading
- Use grep patterns to find specific sections when needed:
  - `workstack create` - Creating worktrees
  - `workstack switch` - Switching worktrees
  - `workstack list` - Listing worktrees
  - `Pattern [0-9]:` - Workflow patterns
  - `Graphite Integration` - Graphite-specific features
  - `Configuration` - Setup and config

## Common Operations

When users ask for help with workstack, guide them using these patterns:

### First-Time Setup

1. Check if workstack is initialized: `workstack config list`
2. If not initialized: `workstack init` (sets up global + repo config)
3. Consider using presets: `workstack init --preset dagster` or `--preset auto`
4. Set up shell integration: `workstack init --shell` (enables `ws` command)

### Creating Worktrees

Load `references/workstack.md` and search for "workstack create" section to provide:

- Syntax options (basic, custom branch, from existing branch, with plan file)
- Environment setup details
- Post-create command execution

### Switching Between Worktrees

Load `references/workstack.md` and search for "workstack switch" section to provide:

- Basic switching: `workstack switch <name>`
- Stack navigation: `workstack up` and `workstack down` for Graphite stacks
- Jump to branch: `workstack jump <branch>` to find and switch to a branch
- Return to root: `workstack switch root`
- Environment activation details

### Listing and Viewing

Load `references/workstack.md` and search for "workstack list" section to provide:

- Basic listing: `workstack ls`
- With stacks: `workstack ls --stacks` (shows Graphite structure)
- With checks: `workstack ls --checks` (shows CI status)
- Tree view: `workstack tree` (dependency visualization)

### Cleanup and Maintenance

Load `references/workstack.md` and search for "workstack sync" section to provide:

- Finding merged worktrees: `workstack sync --dry-run`
- Syncing and cleaning with Graphite: `workstack sync -f`
- Manual removal: `workstack rm <name>`

## Workflow Guidance

When users describe their workflow needs, map them to patterns in the reference:

**Pattern 1: Basic Feature Development** - Standard parallel development
**Pattern 2: Plan-Based Development** - Separation of planning and implementation with `.PLAN.md`
**Pattern 3: Existing Branches** - Creating worktrees from existing work
**Pattern 4: Stacked Development** - Using Graphite for dependent features
**Pattern 5: Parallel Development** - Managing multiple concurrent features
**Pattern 7: Cleanup After Merging** - Post-PR maintenance
**Pattern 8: Environment-Specific** - Unique environments per worktree

Load the appropriate pattern sections from `references/workstack.md` based on user needs.

## Configuration Guidance

When users need configuration help:

1. Load the Configuration section from `references/workstack.md`
2. Distinguish between global config (`~/.workstack/config.toml`) and repo config (`{work_dir}/config.toml`)
3. Explain template variables: `{worktree_path}`, `{repo_root}`, `{name}`
4. Guide through environment variables and post-create commands
5. Suggest appropriate presets if applicable

## Integration Guidance

### Graphite Integration

When users mention Graphite or stacked diffs:

- Load the Graphite Integration section from `references/workstack.md`
- Explain stack navigation: `workstack up`, `workstack down`, `workstack jump <branch>`
- Show stack visualization: `workstack list --stacks`, `workstack tree`
- Reference the separate Graphite (gt) documentation for deeper gt concepts

### GitHub Integration

When users need PR status information:

- Load the GitHub Integration section from `references/workstack.md`
- Explain PR status indicators in listings
- Show `workstack sync --dry-run` for finding merged worktrees
- Note requirement for `gh` CLI

## Architecture for Contributors

When users want to contribute to workstack or understand its internals:

- Load the "Key Insights for AI Agents" section from `references/workstack.md`
- Explain the 3-layer architecture (Commands → Core Logic → Operations)
- Cover dependency injection pattern with ABC interfaces
- Show testing guidelines with fakes
- Reference additional internal documentation files mentioned in the reference

## Resources

### references/

- `workstack.md` - Comprehensive workstack mental model and command reference (~1200 lines)

This reference should be loaded whenever providing workstack guidance to ensure accurate, detailed information.
