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

**Output**:

- `[U]` - Blue, bold (user-level, ~/.claude/)
- `[P]` - Green, bold (project-level, ./.claude/)

---

### format_source_indicator

```python
def format_source_indicator(kit_id: str, version: str) -> str
```

Returns a colored badge indicating the artifact source.

**Output**:

- `[kit-id@version]` - Cyan (managed by kit)
- `[local]` - Yellow (locally created)

---

### format_section_header

```python
def format_section_header(text: str) -> str
```

Returns a formatted section header (bold, white, 0-space indent).

---

### format_subsection_header

```python
def format_subsection_header(text: str, count: int = None) -> str
```

Returns a formatted subsection header with optional count (bold, white, 2-space indent).

---

### format_item_name

```python
def format_item_name(name: str, bold: bool = True) -> str
```

Returns a formatted item name with optional bold styling.

---

### format_metadata

```python
def format_metadata(text: str, dim: bool = True) -> str
```

Returns formatted metadata text (secondary information, typically dimmed).

---

### format_kit_reference

```python
def format_kit_reference(kit_id: str, version: str) -> str
```

Returns a formatted kit reference in cyan (without brackets, used in verbose mode).

---

### get_visible_length

```python
def get_visible_length(text: str) -> int
```

Calculates the visible length of a string by stripping ANSI color codes. Essential for proper text alignment when using colors.

---

## Color Scheme Reference

| Element           | Color        | Usage                         |
| ----------------- | ------------ | ----------------------------- |
| Project level [P] | Green (bold) | Project-level artifacts       |
| User level [U]    | Blue (bold)  | User-level artifacts          |
| Kit references    | Cyan         | [kit@version], kit references |
| Local sources     | Yellow       | [local] badges                |
| Primary content   | White (bold) | Headers, item names           |
| Secondary content | White (dim)  | Metadata, descriptions        |

## Design Principles

- **Single Source of Truth**: All formatting decisions centralized in this module
- **Composability**: Small, focused functions that combine in different ways
- **Terminal-Native**: Uses ANSI codes (no external dependencies, auto-stripped in non-TTY)

## Related Files

**Used by**: artifact/list.md, hook/list.md, kit/list.md, kit/search.md

**Related utilities**: cli/output.py, cli/colors.py
