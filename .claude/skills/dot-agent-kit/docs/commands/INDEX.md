# commands/ - CLI Command Implementations

## Overview

This directory contains all CLI command implementations for dot-agent-kit, organized by domain.

## Directory Structure

```
commands/
├── artifact/      → Artifact management (list, install, remove)
├── hook/          → Hook management (list, install, remove)
├── kit/           → Kit operations (list, search, install, update)
├── md/            → Markdown utilities (generate, lint)
├── run/           → Run kit CLI commands
├── status.py      → Show managed/unmanaged status
├── check.py       → Check artifact installations
└── init.py        → Initialize dot-agent configuration
```

## List Commands

Four commands provide list functionality with consistent patterns:

| Command | Directory | Purpose | Key Features | Docs |
|---------|-----------|---------|--------------|------|
| `artifact list/ls` | artifact/ | List installed artifacts | Level, type, source filtering; two-section layout | [list.md](artifact/list.md) |
| `hook list/ls` | hook/ | List installed hooks | Groups by lifecycle event; shows matchers | [list.md](hook/list.md) |
| `kit list/ls` | kit/ | List installed kits | Shows versions, sources; optional artifact details | [list.md](kit/list.md) |
| `kit search` | kit/ | Search/list available kits | Searches registry; shows artifact counts | [search.md](kit/search.md) |

## Subdirectories

### artifact/ - Artifact Management
[→ Full index](artifact/INDEX.md)

Commands for managing Claude artifacts (skills, commands, agents, hooks, docs).

**Key files**:
- `list.py` / `ls.py` - List artifacts with extensive filtering - [docs](artifact/list.md)
- `formatting.py` - Artifact-specific output formatting (5 functions) - [docs](artifact/formatting.md)
- Install, remove, show operations

**Unique features**:
- Type filtering (skill, command, agent, hook, doc)
- Two-section layout: "Claude Artifacts" vs "Installed Items"
- Managed-only filter (--managed)

### hook/ - Hook Management
[→ Full index](hook/INDEX.md)

Commands for managing lifecycle hooks.

**Key files**:
- `list.py` / `ls.py` - List hooks grouped by lifecycle - [docs](hook/list.md)
- Install, remove operations

**Unique features**:
- Groups by lifecycle event (UserPromptSubmit, etc.)
- Shows matcher patterns in verbose mode
- Extracts kit_id, hook_id, version from command strings

### kit/ - Kit Operations
[→ Full index](kit/INDEX.md)

Commands for working with kits (collections of artifacts).

**Key files**:
- `list.py` / `ls.py` - List installed kits - [docs](kit/list.md)
- `search.py` - Search kit registry - [docs](kit/search.md)
- Install, update, remove operations

**Unique features**:
- Two display modes: kit-level (default) and artifact-detail (--artifacts)
- Search by name/description
- Shows bundled vs managed vs local kits

## Common Implementation Patterns

### Pattern 1: Reusable Implementation Function

All list commands use `_*_impl()` functions:

```python
# commands/{domain}/list.py

def _list_{domain}_impl(
    level: Level,
    verbose: bool,
    # domain-specific options...
) -> None:
    """Reusable implementation called by both list and ls"""

    # 1. Gather data
    items = gather_{domain}_data(level)

    # 2. Apply filters
    items = apply_filters(items, ...)

    # 3. Format output
    if verbose:
        output = format_verbose(items)
    else:
        output = format_compact(items)

    # 4. Output to stderr
    user_output(output)


# Both commands call same implementation
@click.command("list")
@click.option("--verbose", "-v", ...)
def list_cmd(verbose, ...):
    _list_{domain}_impl(verbose=verbose, ...)


@click.command("ls")
@click.option("--verbose", "-v", ...)
def ls_cmd(verbose, ...):
    _list_{domain}_impl(verbose=verbose, ...)  # Exact same call
```

**Why this pattern?**
- Code reuse between list and ls
- Easier testing (test the implementation)
- Consistent option handling

**Examples**:
- `_list_artifacts_impl()` in [artifact/list.py](artifact/list.md)
- `_list_hooks_impl()` in [hook/list.py](hook/list.md)
- `_list_kits_impl()` in [kit/list.py](kit/list.md)

### Pattern 2: Shared Formatting Utilities

All commands import from `cli.list_formatting`:

```python
from dot_agent_kit.cli.list_formatting import (
    format_level_indicator,      # [P] or [U] badges
    format_source_indicator,      # [kit@version] or [local]
    format_section_header,        # Bold section titles
    format_subsection_header,     # Bold subsection with counts
    format_item_name,             # Bold item names
    format_metadata,              # Dimmed secondary info
    format_kit_reference,         # Cyan kit references
    get_visible_length,           # For alignment
)
```

See [../cli/list_formatting.md](../cli/list_formatting.md) for complete API reference.

**Why shared utilities?**
- Consistent visual design across all commands
- Single source of truth for colors, formatting
- Easier to maintain standards

### Pattern 3: Output Routing

All commands use `user_output()` for human-readable output:

```python
from dot_agent_kit.cli.output import user_output

# Output goes to stderr
user_output(formatted_output)
```

**Why stderr?**
- Keeps stdout clean for machine-readable data
- Allows command composition: `dot-agent artifact list | grep foo`
- Separates human-facing from programmatic output

### Pattern 4: Compact and Verbose Views

All commands support two output modes:

**Compact (default)**:
- One line per item
- Essential info only
- Scannable format

```
Section:
  Subsection:
    [P] item-name [source]
    [U] another-item [local]
```

**Verbose (`-v` flag)**:
- Multi-line per item
- Adds descriptions, paths, metadata
- 6+ space indent for details

```
Section:
  Subsection:
    [P] item-name [source]
        → Description here
        Path: /path/to/item
        Kit: kit-name@1.0.0
```

## Option Patterns

### Level Filtering

Artifact and hook commands support level filtering:

```python
@click.option("--user", "-u", help="Show only user-level items")
@click.option("--project", "-p", help="Show only project-level items")
@click.option("--all", "-a", default=True, help="Show items from both levels")
```

Uses `ArtifactLevel` enum to manage filtering logic.

### Verbose Flag

All list commands support verbose mode:

```python
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
```

Verbose mode typically adds:
- Descriptions
- File paths
- Kit references
- Additional metadata

### Domain-Specific Filters

Each command adds filters relevant to its domain:

**artifact list**:
- `--type` - Filter by artifact type (skill, command, agent, hook, doc)
- `--managed` - Show only kit-managed artifacts

**hook list**:
- Groups by lifecycle event automatically
- Verbose shows matcher patterns

**kit list**:
- `--artifacts` - Show artifact details per kit

**kit search**:
- `[QUERY]` - Search term for name/description

## Shared Dependencies

All list commands depend on:

1. **cli/list_formatting.py** - 8 shared formatting functions
   - [→ API docs](../cli/list_formatting.md)

2. **cli/output.py** - Output routing
   - `user_output()` - Route to stderr for human-readable output

3. **Click** - CLI framework
   - Commands, options, arguments

4. **Domain-specific formatting** (where applicable)
   - `commands/artifact/formatting.py` - 5 artifact formatters
   - [→ API docs](artifact/formatting.md)

## Adding a New List Command

### Step 1: Study Existing Patterns

Review existing implementations to understand patterns:

1. **Most comprehensive example**: [artifact/list.md](artifact/list.md)
   - Type filtering
   - Two-section layout
   - Extensive options

2. **Simpler example**: [hook/list.md](hook/list.md)
   - Grouping by lifecycle
   - Matcher patterns in verbose

3. **Alternative view pattern**: [kit/list.md](kit/list.md)
   - Default vs detail views
   - Optional artifact breakdown

### Step 2: Use Shared Utilities

Import formatting functions from [../cli/list_formatting.md](../cli/list_formatting.md):

```python
from dot_agent_kit.cli.list_formatting import (
    format_level_indicator,
    format_source_indicator,
    format_section_header,
    format_subsection_header,
    format_item_name,
    format_metadata,
)
from dot_agent_kit.cli.output import user_output
```

### Step 3: Follow Design Standards

Adhere to formatting standards:
- **Colors**: Green [P], Blue [U], Cyan [kit@ver], Yellow [local]
- **Indentation**: 0 (sections), 2 (subsections), 4 (items), 6+ (details)
- **Badge format**: `[level] name [source]`
- **Output**: Use `user_output()` for stderr routing

### Step 4: Create Implementation Function

```python
def _list_newdomain_impl(options) -> None:
    """Reusable implementation"""
    # 1. Gather data
    # 2. Apply filters
    # 3. Format (compact vs verbose)
    # 4. Output via user_output()
```

### Step 5: Create Both Commands

```python
@click.command("list")
@click.option("--verbose", "-v", ...)
def list_cmd(...):
    _list_newdomain_impl(...)

@click.command("ls")
@click.option("--verbose", "-v", ...)
def ls_cmd(...):
    _list_newdomain_impl(...)  # Same implementation
```

### Step 6: Add Tests

Create tests in `tests/commands/{domain}/test_list.py`:
- Test filters (level, domain-specific)
- Test compact vs verbose output
- Test empty state handling
- Test formatting consistency

## Navigation

**Working in artifact/ directory?**
→ Load [artifact/INDEX.md](artifact/INDEX.md)

**Working in hook/ directory?**
→ Load [hook/INDEX.md](hook/INDEX.md)

**Working in kit/ directory?**
→ Load [kit/INDEX.md](kit/INDEX.md)

**Need formatting utilities?**
→ Load [../cli/list_formatting.md](../cli/list_formatting.md)

**Need package overview?**
→ Load [../INDEX.md](../INDEX.md)
