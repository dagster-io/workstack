# commands/artifact/ - Artifact Management Commands

## Overview

This directory implements commands for managing Claude Code artifacts (skills, commands, agents, hooks, docs).

## Files

| File | Purpose | Key Features | Docs |
|------|---------|--------------|------|
| `list.py` | List installed artifacts | Level, type, source filtering; two-section layout | [list.md](list.md) |
| `ls.py` | Alias for list command | Calls same implementation as list.py | [list.md](list.md) |
| `formatting.py` | Artifact-specific output formatting | 5 formatting functions for artifact display | [formatting.md](formatting.md) |

## artifact list/ls Command

[→ Full documentation](list.md)

**Purpose**: List installed Claude artifacts with extensive filtering options.

**Key features**:
- **Level filtering**: `--user`, `--project`, `--all` (default)
- **Type filtering**: `--type` (skill, command, agent, hook, doc)
- **Source filtering**: `--managed` (kit-tracked artifacts only)
- **Two views**: Compact (default) and verbose (`-v`)
- **Two-section layout**: "Claude Artifacts" vs "Installed Items"

**Options**:
```bash
--user, -u          # Show only user-level artifacts (~/.claude/)
--project, -p       # Show only project-level artifacts (./.claude/)
--all, -a           # Show artifacts from both levels (default)
--type TYPE         # Filter by: skill, command, agent, hook, doc
--verbose, -v       # Show detailed information (descriptions, paths)
--managed           # Show only kit-managed artifacts (in dot-agent.toml)
```

**Example output** (compact):
```
Claude Artifacts:
  Skills:
    [P] workstack [workstack@0.1.0]
    [U] custom-skill [local]

  Agents:
    [P] code-reviewer [ai-toolkit@1.2.0]

Installed Items:
  Docs:
    [P] api-guide [workstack@0.1.0]
```

**Example output** (verbose with `-v`):
```
Claude Artifacts:
  Skills:
    [P] workstack [workstack@0.1.0]
        → Use workstack for git worktree management
        Kit: workstack@0.1.0
        Path: .claude/skills/workstack/SKILL.md
```

## Formatting Module

[→ Full API reference](formatting.md)

**Purpose**: Artifact-specific output formatting functions.

**Functions** (5 total):
- `format_compact_list()` - Compact view formatter
- `format_verbose_list()` - Verbose view formatter with descriptions/paths
- `format_compact_artifact_line()` - Single-line format for one artifact
- `format_artifact_header()` - Multi-line metadata header
- `format_bundled_kit_item()` - Format bundled kit items

These functions use shared utilities from `cli/list_formatting` for consistent badges and colors.

## Implementation Pattern

### List Command Flow

```
1. Parse CLI options
   ↓ (level, type, managed filters)

2. Gather artifacts from settings
   ↓ Read from ~/.claude/ and ./.claude/

3. Apply filters
   ↓ Filter by level, type, managed status

4. Format output
   ↓ Compact: format_compact_list()
   ↓ Verbose: format_verbose_list()

5. Output to stderr
   ↓ via user_output()
```

### Reusable Implementation

Both `list` and `ls` commands call the same implementation:

```python
def _list_artifacts_impl(
    level: ArtifactLevel,
    artifact_type: str | None,
    verbose: bool,
    managed_only: bool
) -> None:
    # Implementation here
    pass

@click.command("list")
def list_cmd(...):
    _list_artifacts_impl(...)

@click.command("ls")
def ls_cmd(...):
    _list_artifacts_impl(...)  # Same call
```

### Shared Utilities Used

**From `cli/list_formatting` (shared across all commands)**:
- `format_level_indicator()` - [P]/[U] badges
- `format_source_indicator()` - [kit@version]/[local] badges
- `format_section_header()` - Section titles (bold)
- `format_subsection_header()` - Subsection titles with counts
- `format_item_name()` - Item names (bold)
- `format_metadata()` - Secondary info (dimmed)

[→ Shared utilities docs](../../cli/list_formatting.md)

**From `formatting.py` (artifact-specific)**:
- `format_compact_list()` - Full compact view
- `format_verbose_list()` - Full verbose view

[→ Artifact formatting docs](formatting.md)

## Design Decisions

### Why Two Sections?

The two-section layout separates:
1. **Claude Artifacts** (skills, commands, agents, hooks) - First-class extensions that modify Claude's behavior
2. **Installed Items** (docs, kit CLI commands) - Supporting resources

This helps users understand the functional difference between artifact types.

### Why Type Filtering?

Artifacts serve different purposes:
- **Skills**: Add domain knowledge
- **Commands**: Add reusable workflows
- **Agents**: Add specialized AI behaviors
- **Hooks**: Add lifecycle extensions
- **Docs**: Add reference materials

Type filtering allows users to focus on the artifact category they care about.

### Why Managed-Only Filter?

The `--managed` flag shows only artifacts tracked in `dot-agent.toml` (managed by kits). This helps users:
- See what's tracked by the kit system
- Identify unmanaged (local) artifacts
- Understand their kit dependencies

### Why Level Filtering?

Artifacts can be installed at two levels:
- **Project** (`./.claude/`) - Project-specific, versioned with code
- **User** (`~/.claude/`) - Global, shared across projects

Level filtering allows users to:
- See what's specific to this project
- See what's globally available
- Understand scope and precedence

## Design Standards

Follows all list formatting standards:
- **Colors**: Green [P] (project), Blue [U] (user), Cyan [kit@ver], Yellow [local]
- **Indentation**: 0 (sections), 2 (subsections), 4 (items), 6+ (details)
- **Badge format**: `[level] name [source]`

## Testing

Tests located in: `tests/commands/artifact/test_list.py`

**Key test scenarios**:
- Level filtering (--user, --project, --all)
- Type filtering (each artifact type)
- Managed-only filtering
- Compact vs verbose formatting
- Empty state handling (no artifacts installed)
- Mixed levels and sources

## Related Files

**Similar list commands**:
- [../hook/list.md](../hook/list.md) - Groups by lifecycle event
- [../kit/list.md](../kit/list.md) - Optional artifact detail view

**Shared utilities**:
- [../../cli/list_formatting.md](../../cli/list_formatting.md) - 8 shared formatting functions

**Parent context**:
- [../INDEX.md](../INDEX.md) - All commands overview

## Quick Actions

**Modifying list output?**
→ Load [list.md](list.md) for implementation details

**Adding new artifact formatter?**
→ Load [formatting.md](formatting.md) for API reference

**Understanding overall command patterns?**
→ Load [../INDEX.md](../INDEX.md) for cross-command patterns

**Need shared formatting utilities?**
→ Load [../../cli/list_formatting.md](../../cli/list_formatting.md)
