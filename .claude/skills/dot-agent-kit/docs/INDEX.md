# dot-agent-kit Package

## Overview

The dot-agent-kit package provides CLI commands and utilities for managing Claude Code artifacts (skills, commands, agents, hooks) through a kit system.

## Package Structure

```
dot-agent-kit/
├── commands/          → CLI command implementations
├── cli/               → Shared CLI utilities (formatting, output)
├── hooks/             → Hook system infrastructure
├── data/              → Bundled kits and artifact data
└── core.py            → Core logic and interfaces
```

## Key Subsystems

### Commands (`commands/`)
[→ Full docs](commands/INDEX.md)

CLI command implementations organized by domain:
- **artifact**: List and manage artifacts (skills, commands, agents, hooks, docs)
- **hook**: List and manage lifecycle hooks
- **kit**: List, search, install kits
- **md**: Markdown utilities (generate, lint)
- **run**: Run kit CLI commands
- Root-level: `status.py`, `check.py`, `init.py`

**Quick reference - List Commands** (4 total):
- `artifact list/ls` - Lists installed artifacts with filtering by level, type, source - [docs](commands/artifact/list.md)
- `hook list/ls` - Lists hooks grouped by lifecycle event - [docs](commands/hook/list.md)
- `kit list/ls` - Lists installed kits with optional artifact details - [docs](commands/kit/list.md)
- `kit search` - Searches/lists available kits in registry - [docs](commands/kit/search.md)

### CLI Utilities (`cli/`)
[→ Full docs](cli/INDEX.md)

Shared utilities for consistent CLI experience:
- **list_formatting.py**: 8 shared formatting functions - [docs](cli/list_formatting.md)
  - `format_level_indicator()` - [P]/[U] badges
  - `format_source_indicator()` - [kit@version]/[local] badges
  - `format_section_header()` - Section titles
  - `format_subsection_header()` - Subsection titles with counts
  - `format_item_name()` - Item names (bold)
  - `format_metadata()` - Secondary info (dimmed)
  - `format_kit_reference()` - Kit references (cyan)
  - `get_visible_length()` - Calculate visible length (strips ANSI)

## Common Tasks

### Adding a New List Command

**Steps**:
1. Review [commands/INDEX.md](commands/INDEX.md) for overall structure and patterns
2. Study existing examples:
   - [commands/artifact/list.md](commands/artifact/list.md) - Most comprehensive (type filtering, two sections)
   - [commands/hook/list.md](commands/hook/list.md) - Simpler example (grouping by lifecycle)
   - [commands/kit/list.md](commands/kit/list.md) - Optional detail view pattern
3. Use shared formatting utilities: [cli/list_formatting.md](cli/list_formatting.md)
4. Follow the implementation pattern (see below)

**Implementation Pattern**:
```python
# 1. Create _*_impl() function for reusable logic
def _list_{domain}_impl(options):
    # Gather data
    # Format using cli.list_formatting functions
    # Output via user_output()

# 2. Create both list and ls commands calling same impl
@click.command("list")
def list_cmd(): ...

@click.command("ls")
def ls_cmd(): ...  # Same implementation
```

### Modifying List Output Formatting

**Steps**:
1. Review shared utilities: [cli/list_formatting.md](cli/list_formatting.md)
2. Check current usage in specific command (e.g., [commands/artifact/list.md](commands/artifact/list.md))
3. Understand design standards (see Cross-Cutting Patterns below)

### Understanding the Kit System

**Steps**:
1. Start with [commands/kit/INDEX.md](commands/kit/INDEX.md) for kit operations overview
2. See kit list command: [commands/kit/list.md](commands/kit/list.md)
3. See kit search command: [commands/kit/search.md](commands/kit/search.md)

## Cross-Cutting Patterns

### List Command Pattern

All 4 list commands share these characteristics:

**Implementation**:
- Core logic in `_*_impl()` functions (reusable)
- Both `list` and `ls` commands call same implementation
- Import shared utilities from `cli.list_formatting`
- Output via `user_output()` to stderr (keeps stdout clean)

**Options**:
- Compact view (default) and verbose view (`-v` flag)
- Level filtering where applicable (`--user`, `--project`, `--all`)
- Domain-specific filtering (artifact type, lifecycle event, etc.)

**Dependencies**:
- `cli/list_formatting.py` - 8 shared formatting functions
- `cli/output.py` - Output routing (stderr vs stdout)
- Click framework for CLI

See [commands/INDEX.md](commands/INDEX.md) for detailed pattern documentation.

### Formatting Standards

All list output follows consistent design standards:

**Color Scheme**:
- **Green** `[P]` - Project-level items (./.claude/)
- **Blue** `[U]` - User-level items (~/.claude/)
- **Cyan** `[kit@version]` - Kit references
- **Yellow** `[local]` - Local sources

**Indentation Hierarchy**:
- 0 spaces: Section headers (bold)
- 2 spaces: Subsection headers (bold)
- 4 spaces: List items
- 6+ spaces: Item details (in verbose mode)

**Badge Format**:
- `[level] name [source]` - Consistent across all commands

**View Modes**:
- Compact: Essential info only, one line per item
- Verbose: Adds descriptions, paths, metadata (6+ space indent)

**Output Routing**:
- Human-readable output → stderr (via `user_output()`)
- Machine-readable data → stdout
- This allows commands to be composed in scripts

See [cli/list_formatting.md](cli/list_formatting.md) for API reference.

## Design Decisions

### Why Separate List Commands by Domain?

Each domain (artifact, hook, kit) has distinct:
- Data models and sources
- Filtering needs (type vs lifecycle vs registry)
- Display requirements (grouping strategies)

Separate commands provide focused interfaces while sharing formatting utilities.

### Why `_*_impl()` Pattern?

The `_list_{domain}_impl()` pattern enables:
- Code reuse between `list` and `ls` commands
- Easier testing (test the implementation, not CLI plumbing)
- Consistent option handling across aliases

### Why stderr for Output?

List commands output to stderr via `user_output()` to:
- Keep stdout clean for machine-readable data
- Allow command composition in scripts
- Separate human-facing output from programmatic output

## Navigation Tips

**Working in commands/?**
→ Load [commands/INDEX.md](commands/INDEX.md) for command structure overview

**Working on artifact commands?**
→ Load [commands/artifact/INDEX.md](commands/artifact/INDEX.md) for artifact-specific details

**Working on hook commands?**
→ Load [commands/hook/INDEX.md](commands/hook/INDEX.md) for hook-specific details

**Working on kit commands?**
→ Load [commands/kit/INDEX.md](commands/kit/INDEX.md) for kit-specific details

**Need formatting utilities?**
→ Load [cli/list_formatting.md](cli/list_formatting.md) for complete API reference

**Working on specific file?**
→ Navigate to that file's .md doc (e.g., `commands/artifact/list.md`)
