# cli/ - Shared CLI Utilities

## Overview

This directory contains shared utilities used by all CLI commands for consistent output formatting and behavior.

## Files

| File | Purpose | Key Functions | Docs |
|------|---------|---------------|------|
| `list_formatting.py` | Shared list output formatting | 8 functions for badges, headers, colors | [list_formatting.md](list_formatting.md) |
| `output.py` | Output routing (stdout/stderr) | `user_output()`, `machine_output()` | - |
| `colors.py` | Color definitions | ANSI color constants | - |

## list_formatting.py - Core Formatting Utilities

[→ Full API reference](list_formatting.md)

**Purpose**: Provides 8 shared formatting functions used by all list commands for consistent visual design.

**Functions**:
1. `format_level_indicator(level)` - [P]/[U] badges (green/blue)
2. `format_source_indicator(kit_id, version)` - [kit@version]/[local] badges (cyan/yellow)
3. `format_section_header(text)` - Section titles (bold white)
4. `format_subsection_header(text, count)` - Subsection titles with optional counts (bold white)
5. `format_item_name(name, bold)` - Item names (bold white)
6. `format_metadata(text, dim)` - Secondary information (dimmed white)
7. `format_kit_reference(kit_id, version)` - Kit references (cyan)
8. `get_visible_length(text)` - Calculate visible string length (strips ANSI codes)

**Used by**:
- `commands/artifact/list.py` - [docs](../commands/artifact/list.md)
- `commands/hook/list.py` - [docs](../commands/hook/list.md)
- `commands/kit/list.py` - [docs](../commands/kit/list.md)
- `commands/kit/search.py` - [docs](../commands/kit/search.md)

## output.py - Output Routing

**Purpose**: Routes output to appropriate streams (stdout vs stderr).

**Functions**:
- `user_output(message, nl=True, color=None)` - Routes to **stderr** for human-readable output
- `machine_output(message, nl=True, color=None)` - Routes to **stdout** for machine-readable data

**Why separate streams?**
- **stderr**: Human-facing output (list commands, status messages)
- **stdout**: Machine-readable data (allows command composition)
- Enables: `dot-agent artifact list | grep foo` to work correctly

## colors.py - Color Definitions

**Purpose**: Centralized ANSI color code definitions.

**Color constants used in list commands**:
- Green - Project-level items
- Blue - User-level items
- Cyan - Kit references and versions
- Yellow - Local sources
- White - Primary content
- White (dim) - Secondary metadata

## Design Standards

All utilities in this directory implement these standards:

### Color Scheme

| Color | Meaning | Usage |
|-------|---------|-------|
| **Green** (bold) | Project-level | `[P]` badges |
| **Blue** (bold) | User-level | `[U]` badges |
| **Cyan** | Kit sources/versions | `[kit@version]`, kit references |
| **Yellow** | Local sources | `[local]` badges |
| **White** (bold) | Primary content | Section headers, item names |
| **White** (dim) | Secondary metadata | Descriptions, paths |

### Indentation Levels

Consistent 2-space increments:
- **0 spaces**: Section headers
- **2 spaces**: Subsection headers
- **4 spaces**: List items
- **6 spaces**: Item details (verbose mode)
- **8 spaces**: Nested details (rare)

### Badge Format

Standard badge pattern: `[level] name [source]`

Example: `[P] workstack [workstack@0.1.0]`

Components:
- Level badge: `[P]` or `[U]`
- Spacing: One space between components
- Name: Item identifier
- Source badge: `[kit@version]` or `[local]`

## Usage Pattern

All list commands follow this import pattern:

```python
from dot_agent_kit.cli.list_formatting import (
    format_level_indicator,
    format_source_indicator,
    format_section_header,
    format_subsection_header,
    format_item_name,
    format_metadata,
    format_kit_reference,
    get_visible_length,
)
from dot_agent_kit.cli.output import user_output

# Use formatting functions to build output
level_badge = format_level_indicator(level)
source_badge = format_source_indicator(kit_id, version)
header = format_section_header("Claude Artifacts")

# Output to stderr
user_output(formatted_output)
```

## Design Decisions

### Why Centralized Formatting?

**Benefits**:
- Single source of truth for visual design
- Consistent output across all commands
- Easy to update colors/formatting globally
- Reduces code duplication

**Alternative considered**: Each command implements own formatting
**Rejected because**: Leads to inconsistency and maintenance burden

### Why Separate Output Streams?

**Problem**: List commands need to be both:
- Human-readable (for interactive use)
- Machine-parseable (for scripting)

**Solution**:
- Human output → stderr (via `user_output()`)
- Machine data → stdout (via `machine_output()`)

**Benefit**: Commands can be piped and composed without interference

### Why ANSI Color Codes?

**Benefits**:
- Terminal-native (no dependencies)
- Widely supported
- Fast (no rendering overhead)

**Fallback**: Colors are stripped in non-TTY contexts automatically

## Testing

**Test approach**:
- Test each formatting function independently
- Test ANSI code generation
- Test visible length calculation (strips codes correctly)
- Test output routing (stderr vs stdout)
- Integration tests in command tests verify correct usage

## Navigation

**Need complete API reference for list_formatting?**
→ Load [list_formatting.md](list_formatting.md)

**See usage in commands?**
- [commands/artifact/list.md](../commands/artifact/list.md)
- [commands/hook/list.md](../commands/hook/list.md)
- [commands/kit/list.md](../commands/kit/list.md)

**Back to package overview?**
→ Load [../INDEX.md](../INDEX.md)
