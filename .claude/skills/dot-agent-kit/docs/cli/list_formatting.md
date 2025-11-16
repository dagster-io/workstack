# cli/list_formatting.py

## Overview

Shared formatting utilities used by all list commands to ensure consistent visual design across the dot-agent-kit CLI.

**File location**: `packages/dot-agent-kit/src/dot_agent_kit/cli/list_formatting.py`

## Functions

### format_level_indicator

```python
def format_level_indicator(level: str) -> str
```

Returns a colored badge indicating the artifact level.

**Parameters**:

- `level` (str): Level identifier - "user" or "project"

**Returns**:

- `str`: Formatted badge string with ANSI color codes

**Output**:

- `[U]` - Blue, bold (user-level, ~/.claude/)
- `[P]` - Green, bold (project-level, ./.claude/)

**Example**:

```python
format_level_indicator("project")  # → "[P]" (green, bold)
format_level_indicator("user")     # → "[U]" (blue, bold)
```

**Usage in commands**:

```python
level_badge = format_level_indicator(artifact.level)
line = f"    {level_badge} {artifact.name} {source_badge}"
```

---

### format_source_indicator

```python
def format_source_indicator(kit_id: str, version: str) -> str
```

Returns a colored badge indicating the artifact source.

**Parameters**:

- `kit_id` (str): Kit identifier (or None for local)
- `version` (str): Kit version (or None for local)

**Returns**:

- `str`: Formatted badge string with ANSI color codes

**Output**:

- `[kit-id@version]` - Cyan (managed by kit)
- `[local]` - Yellow (locally created)

**Example**:

```python
format_source_indicator("workstack", "0.1.0")  # → "[workstack@0.1.0]" (cyan)
format_source_indicator(None, None)            # → "[local]" (yellow)
```

**Usage in commands**:

```python
source_badge = format_source_indicator(artifact.kit_id, artifact.version)
line = f"    {level_badge} {artifact.name} {source_badge}"
```

---

### format_section_header

```python
def format_section_header(text: str) -> str
```

Returns a formatted section header.

**Parameters**:

- `text` (str): Header text

**Returns**:

- `str`: Bold, white text (0-space indent)

**Example**:

```python
format_section_header("Claude Artifacts")  # → "Claude Artifacts" (bold, white)
format_section_header("Installed Items")   # → "Installed Items" (bold, white)
```

**Usage in commands**:

```python
output = []
output.append(format_section_header("Claude Artifacts"))
output.append("")  # Blank line after header
# ... add subsections and items
```

**Design notes**:

- Always at 0-space indent (left-aligned)
- Bold for visual hierarchy
- Typically followed by blank line

---

### format_subsection_header

```python
def format_subsection_header(text: str, count: int = None) -> str
```

Returns a formatted subsection header with optional count.

**Parameters**:

- `text` (str): Subsection text (e.g., "Skills", "Commands")
- `count` (int, optional): Number of items in subsection

**Returns**:

- `str`: Bold, white text with 2-space indent and optional count

**Example**:

```python
format_subsection_header("Skills")        # → "  Skills" (bold, white)
format_subsection_header("Skills", 3)     # → "  Skills (3)" (bold, white)
format_subsection_header("Commands", 0)   # → "  Commands (0)" (bold, white)
```

**Usage in commands**:

```python
output.append(format_section_header("Claude Artifacts"))
output.append(format_subsection_header("Skills", len(skills)))
for skill in skills:
    output.append(format_item_line(skill))
```

**Design notes**:

- 2-space indent under section headers
- Count in parentheses helps users understand section size
- Bold for visual hierarchy

---

### format_item_name

```python
def format_item_name(name: str, bold: bool = True) -> str
```

Returns a formatted item name.

**Parameters**:

- `name` (str): Item name
- `bold` (bool, optional): Whether to bold the text (default: True)

**Returns**:

- `str`: Formatted name with optional bold styling

**Example**:

```python
format_item_name("workstack")              # → "workstack" (bold, white)
format_item_name("custom-skill", bold=False)  # → "custom-skill" (white, no bold)
```

**Usage in commands**:

```python
level_badge = format_level_indicator(artifact.level)
item_name = format_item_name(artifact.name)
source_badge = format_source_indicator(artifact.kit_id, artifact.version)

line = f"    {level_badge} {item_name} {source_badge}"
```

**Design notes**:

- Typically bold for emphasis
- Can be non-bold for de-emphasized items
- White color for primary content

---

### format_metadata

```python
def format_metadata(text: str, dim: bool = True) -> str
```

Returns formatted metadata text (secondary information).

**Parameters**:

- `text` (str): Metadata text
- `dim` (bool, optional): Whether to dim the text (default: True)

**Returns**:

- `str`: Formatted text with optional dimming

**Example**:

```python
format_metadata("Path: /path/to/file")              # → "Path: /path/to/file" (dimmed, white)
format_metadata("Description text", dim=False)      # → "Description text" (white, no dim)
```

**Usage in commands** (verbose mode):

```python
if verbose:
    output.append(f"    {level_badge} {item_name} {source_badge}")
    output.append(f"        → {format_metadata(artifact.description)}")
    output.append(f"        {format_metadata(f'Path: {artifact.path}')}")
```

**Design notes**:

- Dimmed to de-emphasize secondary information
- Used for descriptions, paths, additional metadata
- Typically 6+ space indent in verbose mode

---

### format_kit_reference

```python
def format_kit_reference(kit_id: str, version: str) -> str
```

Returns a formatted kit reference (without brackets).

**Parameters**:

- `kit_id` (str): Kit identifier
- `version` (str): Kit version

**Returns**:

- `str`: Formatted kit reference in cyan

**Example**:

```python
format_kit_reference("workstack", "0.1.0")  # → "workstack@0.1.0" (cyan)
format_kit_reference("ai-toolkit", "1.2.0")  # → "ai-toolkit@1.2.0" (cyan)
```

**Usage in commands** (verbose mode):

```python
if artifact.kit_id:
    kit_ref = format_kit_reference(artifact.kit_id, artifact.version)
    output.append(f"        Kit: {kit_ref}")
```

**Design notes**:

- No brackets (unlike `format_source_indicator`)
- Used in verbose mode to show kit provenance
- Cyan color for kit references

---

### get_visible_length

```python
def get_visible_length(text: str) -> int
```

Calculates the visible length of a string by stripping ANSI color codes.

**Parameters**:

- `text` (str): Text with potential ANSI codes

**Returns**:

- `int`: Visible character count

**Example**:

```python
text_with_color = "\033[1m\033[32m[P]\033[0m workstack"
get_visible_length(text_with_color)  # → 13 (strips ANSI codes)

plain_text = "[P] workstack"
get_visible_length(plain_text)  # → 13 (no codes to strip)
```

**Usage in commands** (alignment):

```python
# Calculate padding for column alignment
items = [...]
max_name_length = max(get_visible_length(item.name) for item in items)

for item in items:
    name_padded = item.name.ljust(max_name_length - get_visible_length(item.name))
    line = f"{name_padded} {source_badge}"
```

**Design notes**:

- Essential for proper text alignment when using colors
- ANSI codes add invisible characters that affect string length
- Use this instead of `len()` when calculating display width

---

## Color Scheme Reference

| Element           | Color        | ANSI Code         | Usage                         |
| ----------------- | ------------ | ----------------- | ----------------------------- |
| Project level [P] | Green (bold) | `\033[1m\033[32m` | Project-level artifacts       |
| User level [U]    | Blue (bold)  | `\033[1m\033[34m` | User-level artifacts          |
| Kit references    | Cyan         | `\033[36m`        | [kit@version], kit references |
| Local sources     | Yellow       | `\033[33m`        | [local] badges                |
| Primary content   | White (bold) | `\033[1m\033[37m` | Headers, item names           |
| Secondary content | White (dim)  | `\033[2m\033[37m` | Metadata, descriptions        |

## Implementation Pattern

All list commands follow this pattern:

```python
from dot_agent_kit.cli.list_formatting import (
    format_level_indicator,
    format_source_indicator,
    format_section_header,
    format_subsection_header,
    format_item_name,
    format_metadata,
)

def format_compact_list(items):
    """Format items in compact view"""
    output = []

    # Section header
    output.append(format_section_header("Section Name"))

    # Subsection with count
    output.append(format_subsection_header("Subsection", len(items)))

    # Items
    for item in items:
        level_badge = format_level_indicator(item.level)
        name = format_item_name(item.name)
        source_badge = format_source_indicator(item.kit_id, item.version)
        output.append(f"    {level_badge} {name} {source_badge}")

    return "\n".join(output)


def format_verbose_list(items):
    """Format items in verbose view"""
    output = []

    output.append(format_section_header("Section Name"))
    output.append(format_subsection_header("Subsection", len(items)))

    for item in items:
        # Item line (same as compact)
        level_badge = format_level_indicator(item.level)
        name = format_item_name(item.name)
        source_badge = format_source_indicator(item.kit_id, item.version)
        output.append(f"    {level_badge} {name} {source_badge}")

        # Details (verbose-specific)
        output.append(f"        → {format_metadata(item.description)}")
        output.append(f"        {format_metadata(f'Path: {item.path}')}")

        if item.kit_id:
            kit_ref = format_kit_reference(item.kit_id, item.version)
            output.append(f"        Kit: {kit_ref}")

        # Blank line between items
        output.append("")

    return "\n".join(output)
```

## Design Principles

### Single Source of Truth

All formatting decisions live in this module:

- Colors are defined once
- Badge formats are consistent
- Indentation levels are standard

**Benefit**: Change formatting globally by updating one file

### Composability

Functions are small and focused:

- Each does one thing well
- Can be combined in different ways
- Easy to test independently

### Terminal-Native

Uses ANSI codes for colors:

- No external dependencies
- Works in all modern terminals
- Automatically stripped in non-TTY contexts

## Usage Examples

### Basic Item Line (Compact)

```python
level_badge = format_level_indicator("project")
name = format_item_name("workstack")
source_badge = format_source_indicator("workstack", "0.1.0")

line = f"    {level_badge} {name} {source_badge}"
# Output: "    [P] workstack [workstack@0.1.0]"
#         (green P, cyan kit@version)
```

### Item with Details (Verbose)

```python
# Item line
level_badge = format_level_indicator("project")
name = format_item_name("workstack")
source_badge = format_source_indicator("workstack", "0.1.0")
print(f"    {level_badge} {name} {source_badge}")

# Description
desc = format_metadata("Use workstack for git worktree management")
print(f"        → {desc}")

# Kit reference
kit_ref = format_kit_reference("workstack", "0.1.0")
print(f"        Kit: {kit_ref}")

# Path
path = format_metadata("Path: .claude/skills/workstack/SKILL.md")
print(f"        {path}")
```

### Section with Subsections

```python
output = []

# Section header
output.append(format_section_header("Claude Artifacts"))
output.append("")  # Blank line

# Skills subsection
output.append(format_subsection_header("Skills", 2))
# ... add skill items ...

# Agents subsection
output.append(format_subsection_header("Agents", 1))
# ... add agent items ...

print("\n".join(output))
```

## Testing

**Test file**: `tests/cli/test_list_formatting.py`

**Key test scenarios**:

1. Each function produces correct output
2. ANSI codes are included in terminal context
3. Colors match specification
4. Badge formats are consistent
5. `get_visible_length()` correctly strips ANSI codes
6. Indentation levels are correct

## Related Files

**Used by**:

- [commands/artifact/list.md](../commands/artifact/list.md)
- [commands/artifact/formatting.md](../commands/artifact/formatting.md)
- [commands/hook/list.md](../commands/hook/list.md)
- [commands/kit/list.md](../commands/kit/list.md)
- [commands/kit/search.md](../commands/kit/search.md)

**Related utilities**:

- `cli/output.py` - Output routing (stderr vs stdout)
- `cli/colors.py` - Color constant definitions

**Parent context**:

- [INDEX.md](INDEX.md) - CLI utilities overview
- [../INDEX.md](../INDEX.md) - Package overview

## See Also

- Design standards: `/docs/agent/cli-list-formatting.md` (repository root)
- ANSI color codes: https://en.wikipedia.org/wiki/ANSI_escape_code
