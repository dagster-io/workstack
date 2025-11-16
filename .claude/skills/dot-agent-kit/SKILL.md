---
name: dot-agent-kit
description: Documentation for the dot-agent-kit package. Use when working in packages/dot-agent-kit/. Provides navigation to commands, CLI utilities, hooks, and data modules with progressive disclosure based on your current directory. Essential for working with list commands (artifact list, hook list, kit list, kit search) and CLI formatting utilities.
---

# dot-agent-kit Package Documentation

## Scope

This skill provides documentation for the **dot-agent-kit** package located at:

- `packages/dot-agent-kit/`

## How to Use This Skill

**Always start by loading the root index:**

```
@docs/INDEX.md
```

The root index shows the immediate package structure and points to subdirectory indexes. Follow the navigation links recursively as you drill down into specific areas.

## Navigation Pattern

```
1. Start:     docs/INDEX.md           (package overview, immediate children)
2. Drill in:  docs/commands/INDEX.md  (commands overview, immediate children)
3. Drill in:  docs/commands/artifact/INDEX.md (artifact commands, files)
4. File doc:  docs/commands/artifact/list.md  (specific file documentation)
```

**Key principle**: Each INDEX.md only describes its immediate children and points to their INDEX.md files. This ensures code changes only require updating one index.

## File Path Mapping

```
Source code path              → Documentation path
---------------------------------------------------
packages/dot-agent-kit/       → docs/INDEX.md
  commands/                   → docs/commands/INDEX.md
    artifact/                 → docs/commands/artifact/INDEX.md
      list.py                 → docs/commands/artifact/list.md
  cli/                        → docs/cli/INDEX.md
    list_formatting.py        → docs/cli/list_formatting.md
```

**Pattern**: Replace `src/dot_agent_kit/` with `docs/`, `.py` → `.md`, directories → `INDEX.md`
