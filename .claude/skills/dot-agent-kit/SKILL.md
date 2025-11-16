---
name: dot-agent-kit
description: Documentation for the dot-agent-kit package. Use when working in packages/dot-agent-kit/. Provides navigation to commands, CLI utilities, hooks, and data modules with progressive disclosure based on your current directory. Essential for working with list commands (artifact list, hook list, kit list, kit search) and CLI formatting utilities.
---

# dot-agent-kit Package Documentation

## Scope

This skill provides documentation for the **dot-agent-kit** package located at:
- `packages/dot-agent-kit/`

## Navigation Strategy

### 1. Start with the Root Index

Always begin by loading:
```
docs/INDEX.md
```

This provides the package overview and guides you to the relevant subpackage.

### 2. Load Directory Indexes as You Navigate

As you navigate deeper into the package structure:

```
Current Directory                → Load
----------------------------------------
commands/                        → docs/commands/INDEX.md
commands/artifact/               → docs/commands/artifact/INDEX.md
commands/artifact/list.py        → docs/commands/artifact/list.md
cli/                            → docs/cli/INDEX.md
cli/list_formatting.py          → docs/cli/list_formatting.md
```

**Pattern**: Replace `src/dot_agent_kit/` with `docs/` and file extensions `.py` → `.md`, directory → `INDEX.md`

### 3. Progressive Disclosure Strategy

```
Level 1: Package Overview
  ↓ Load: docs/INDEX.md (100-200 lines, ~1K tokens)

Level 2: Subpackage Overview
  ↓ Load: docs/{subpackage}/INDEX.md (150-300 lines, ~1.5K tokens)

Level 3: Directory Overview
  ↓ Load: docs/{subpackage}/{dir}/INDEX.md (100-200 lines, ~1K tokens)

Level 4: File Documentation
  ↓ Load: docs/{subpackage}/{dir}/{file}.md (200-500 lines, ~2.5K tokens)
```

**Token budget**:
- Level 1 only: ~1K tokens
- Level 1+2: ~2.5K tokens
- Level 1+2+3: ~3.5K tokens
- Full depth (1+2+3+4): ~6K tokens

Only load deeper levels when needed for the task.

## Quick Navigation by Task

**Working on a specific file?**
```python
# You're editing: src/dot_agent_kit/commands/artifact/list.py
# Load: docs/commands/artifact/list.md
```

**Adding new functionality to a module?**
```python
# You're in: src/dot_agent_kit/commands/artifact/
# Load: docs/commands/artifact/INDEX.md  # Directory overview
# Then: Individual .md files as needed
```

**Understanding the overall architecture?**
```python
# Load: docs/INDEX.md  # Package overview
# Then: Browse subpackage INDEXes as needed
```

**Cross-cutting concern (e.g., "all list commands")?**
```python
# Load: docs/INDEX.md
# Look for "List Commands" section which points to:
#   - docs/commands/artifact/list.md
#   - docs/commands/hook/list.md
#   - docs/commands/kit/list.md
#   - docs/commands/kit/search.md
```

## Index Hierarchy

```
docs/INDEX.md                      ← Package overview
├── docs/commands/INDEX.md         ← Commands subpackage
│   ├── docs/commands/artifact/INDEX.md
│   ├── docs/commands/hook/INDEX.md
│   └── docs/commands/kit/INDEX.md
└── docs/cli/INDEX.md              ← CLI utilities
```

## When to Load What

| Scenario | Load Order |
|----------|------------|
| "What commands exist?" | docs/INDEX.md → commands section |
| "How does artifact list work?" | docs/commands/artifact/INDEX.md → docs/commands/artifact/list.md |
| "What's in commands/artifact/?" | docs/commands/artifact/INDEX.md |
| "Adding new list command" | docs/commands/INDEX.md → multiple list.md files |
| "What formatting functions exist?" | docs/cli/INDEX.md → docs/cli/list_formatting.md |
| "How to format list output?" | docs/cli/list_formatting.md |

## Common Tasks

### Working with List Commands

The package has 4 list commands with consistent patterns:
1. Load `docs/INDEX.md` for overview
2. Navigate to specific command: `docs/commands/{domain}/list.md`
3. For formatting utilities: `docs/cli/list_formatting.md`

### Adding a New List Command

1. Load `docs/commands/INDEX.md` - Understand command patterns
2. Load `docs/commands/artifact/list.md` - Most comprehensive example
3. Load `docs/commands/hook/list.md` - Simpler example
4. Load `docs/cli/list_formatting.md` - Shared utilities to use

### Modifying List Output Formatting

1. Load `docs/cli/list_formatting.md` - API reference for formatting functions
2. Load specific command docs to see usage: `docs/commands/{domain}/list.md`

## Implementation Note

This skill uses **lazy loading** with spatial awareness:
1. Start with the INDEX that matches your current directory depth
2. Load deeper documentation only when you navigate or need specific details
3. Sibling directories stay unloaded until relevant
4. Token budget scales with your focus area, not entire package
