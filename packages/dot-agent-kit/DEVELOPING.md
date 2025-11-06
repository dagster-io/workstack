# Kit Development Workflow

Guide for workstack repository developers editing bundled kits.

## Overview

This document describes the workflow for editing kit files that are bundled with dot-agent-kit. This workflow is **only relevant for developers working in the workstack repository** who are modifying the kits in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`.

For creating new kits from scratch, see [README.md](README.md).

## Quick Reference

| Step | Action                                          | Notes                             |
| ---- | ----------------------------------------------- | --------------------------------- |
| 1    | Enable dev_mode in pyproject.toml               | One-time setup                    |
| 2    | Install kits (creates symlinks)                 | `dot-agent kit install --all`     |
| 3    | Edit `.claude/` files directly in your worktree | Changes immediately affect source |
| 4    | Test and iterate on changes                     | No sync needed - changes are live |
| 5    | Commit your changes                             | `git add . && git commit`         |

✅ **No more sync-back needed!** Edits to `.claude/` immediately affect the source files via symlinks.

## The Development Workflow

When editing bundled kits in the workstack repository, follow this symlink-based workflow:

### 1. Enable Dev Mode (One-Time Setup)

Add the following to your `pyproject.toml` in the workstack repository root:

```toml
[tool.dot-agent]
dev_mode = true
```

This enables symlink-based kit installation for development.

### 2. Install Kits with Symlinks

Run the kit install command to create symlinks:

```bash
dot-agent kit install --all --overwrite
```

With `dev_mode = true`, this creates symlinks from `.claude/` to the kit source files in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`. You'll see output like:

```
  Using symlinks (dev_mode enabled)
  Installed skill: gt-graphite -> source
  Installed agent: devrun -> source
```

### 3. Edit .claude Files Directly

Edit the kit files in `.claude/` within your worktree. **Because these are symlinks, your edits immediately affect the source files:**

```bash
# Example: Edit a skill file
vim .claude/skills/gt-graphite/SKILL.md

# This actually edits:
# packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/skills/gt-graphite/SKILL.md
```

### 4. Test and Iterate

Use the artifacts normally to test your changes. Claude Code reads from `.claude/`, and since these are symlinks, your edits take effect immediately in both locations.

### 5. Commit Your Changes

Commit the source files (not `.claude/`, which should be in .gitignore):

```bash
git add packages/dot-agent-kit/src/dot_agent_kit/data/kits/
git commit -m "Update gt-graphite skill with new examples"
```

**Important**: The `.claude/` directory should be in your `.gitignore`. Only commit the actual source files in `packages/`.

## How Symlinks Work

When `dev_mode` is enabled:

```
.claude/skills/gt-graphite/SKILL.md  →  packages/dot-agent-kit/src/.../kits/gt/skills/gt-graphite/SKILL.md
   (symlink in working directory)           (actual source file)
```

Editing either path affects the same file. This eliminates the need for sync-back operations.

## Symlink Protection

The system automatically protects symlinks:

- **During sync**: `dot-agent kit sync` skips symlinked artifacts and reports:

  ```
  Skipping symlinked artifacts in dev mode:
    .claude/skills/gt-graphite
  ```

- **During install**: Installing with `--overwrite` preserves the symlink behavior

## Fallback Behavior

If symlink creation fails (e.g., on Windows without administrator privileges, or unsupported filesystems), the system automatically falls back to copying files:

```
  Warning: Could not create symlink for gt-graphite (Operation not supported)
  Falling back to file copy
```

In this case, you would need to manually sync changes between `.claude/` and the source.

## Disabling Dev Mode

To switch back to copy-based installation:

1. Remove or set `dev_mode = false` in pyproject.toml:

   ```toml
   [tool.dot-agent]
   dev_mode = false
   ```

2. Reinstall kits:
   ```bash
   dot-agent kit install --all --overwrite
   ```

This reverts to copying files instead of creating symlinks.

## When This Workflow Matters

This workflow is **only necessary for workstack repository developers** editing bundled kits.

**You need this workflow if:**

- You're working in the workstack repository
- You're editing kits in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`
- You're modifying bundled skills, agents, or commands

**You don't need this workflow if:**

- You're a user installing kits from packages
- You're creating new kits from scratch (see [README.md](README.md))
- You're editing project-local `.claude/` files that aren't from kits

## Related Documentation

- [README.md](README.md) - Kit structure and creation guide
- [../../docs/WORKSTACK_DEV.md](../../docs/WORKSTACK_DEV.md) - workstack-dev CLI architecture
