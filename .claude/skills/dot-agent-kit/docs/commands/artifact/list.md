# commands/artifact/list.py

## Command: artifact list / artifact ls

Lists installed Claude artifacts (skills, commands, agents, hooks, docs) with extensive filtering and formatting options.

**File location**: `packages/dot-agent-kit/src/dot_agent_kit/commands/artifact/list.py`

## CLI Interface

```bash
dot-agent artifact list [OPTIONS]
dot-agent artifact ls [OPTIONS]  # Alias
```

## Options

| Option | Short | Values | Default | Description |
|--------|-------|--------|---------|-------------|
| `--user` | `-u` | flag | - | Show only user-level artifacts (~/.claude/) |
| `--project` | `-p` | flag | - | Show only project-level artifacts (./.claude/) |
| `--all` | `-a` | flag | ✓ | Show artifacts from both levels |
| `--type` | - | skill, command, agent, hook, doc | all | Filter by artifact type |
| `--verbose` | `-v` | flag | - | Show detailed information (descriptions, paths) |
| `--managed` | - | flag | - | Show only kit-managed artifacts (in dot-agent.toml) |

## Output Format

### Compact View (Default)

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

**Structure**:
- Two main sections: "Claude Artifacts" and "Installed Items"
- Subsections grouped by artifact type
- One line per artifact: `[level] name [source]`
- 0-space indent for sections (bold)
- 2-space indent for subsections (bold)
- 4-space indent for items

**Badge meanings**:
- `[P]` - Project-level (green, bold) - Located in `./.claude/`
- `[U]` - User-level (blue, bold) - Located in `~/.claude/`
- `[kit@version]` - Managed by kit (cyan) - Tracked in dot-agent.toml
- `[local]` - Locally created (yellow) - Not tracked by kit system

### Verbose View (`-v`)

```
Claude Artifacts:
  Skills:
    [P] workstack [workstack@0.1.0]
        → Use workstack for git worktree management
        Kit: workstack@0.1.0
        Path: .claude/skills/workstack/SKILL.md

    [U] custom-skill [local]
        → My custom development utilities
        Path: ~/.claude/skills/custom-skill/SKILL.md
```

**Additions in verbose mode**:
- Description line with `→` prefix (6-space indent)
- Kit reference line (if managed by kit)
- File path line (absolute path)
- Blank line between artifacts for readability

## Implementation

### File Structure

```python
# Location: packages/dot-agent-kit/src/dot_agent_kit/commands/artifact/list.py

def _list_artifacts_impl(
    level: ArtifactLevel,
    artifact_type: str | None,
    verbose: bool,
    managed_only: bool
) -> None:
    """Reusable list implementation called by both list and ls commands"""

    # 1. Gather artifacts from settings
    artifacts = gather_artifacts(level)

    # 2. Apply filters
    if artifact_type:
        artifacts = filter_by_type(artifacts, artifact_type)
    if managed_only:
        artifacts = filter_managed(artifacts)

    # 3. Format output
    if verbose:
        output = format_verbose_list(artifacts, bundled_kits, user_path, project_path)
    else:
        output = format_compact_list(artifacts, bundled_kits)

    # 4. Output to stderr
    user_output(output)


# CLI command definitions (both call same implementation)
@click.command("list")
@click.option("--user", "-u", "level", flag_value=ArtifactLevel.USER)
@click.option("--project", "-p", "level", flag_value=ArtifactLevel.PROJECT)
@click.option("--all", "-a", "level", flag_value=ArtifactLevel.ALL, default=True)
@click.option("--type", type=click.Choice(["skill", "command", "agent", "hook", "doc"]))
@click.option("--verbose", "-v", is_flag=True)
@click.option("--managed", is_flag=True)
def list_cmd(level, artifact_type, verbose, managed):
    """List installed artifacts"""
    _list_artifacts_impl(level, artifact_type, verbose, managed)


@click.command("ls")
@click.option("--user", "-u", "level", flag_value=ArtifactLevel.USER)
@click.option("--project", "-p", "level", flag_value=ArtifactLevel.PROJECT)
@click.option("--all", "-a", "level", flag_value=ArtifactLevel.ALL, default=True)
@click.option("--type", type=click.Choice(["skill", "command", "agent", "hook", "doc"]))
@click.option("--verbose", "-v", is_flag=True)
@click.option("--managed", is_flag=True)
def ls_cmd(level, artifact_type, verbose, managed):
    """Alias for list command"""
    _list_artifacts_impl(level, artifact_type, verbose, managed)  # Exact same call
```

### Formatting Functions Used

#### From artifact/formatting.py (this directory)

```python
from dot_agent_kit.commands.artifact.formatting import (
    format_compact_list,
    format_verbose_list,
)
```

- `format_compact_list(artifacts, bundled_kits)` - Generates compact view output
- `format_verbose_list(artifacts, bundled_kits, user_path, project_path)` - Generates verbose view with details

[→ See formatting.md for complete API](formatting.md)

#### From cli/list_formatting.py (shared utilities)

```python
from dot_agent_kit.cli.list_formatting import (
    format_level_indicator,
    format_source_indicator,
    format_section_header,
    format_subsection_header,
    format_item_name,
    format_metadata,
)
```

These shared functions are used internally by `format_compact_list()` and `format_verbose_list()`:
- `format_level_indicator(level)` - Returns `[P]` or `[U]` with colors
- `format_source_indicator(kit_id, version)` - Returns `[kit@version]` or `[local]` with colors
- `format_section_header(text)` - Bold white text for sections
- `format_subsection_header(text, count)` - Bold white text with optional count
- `format_item_name(name, bold=True)` - Bold white text for artifact names
- `format_metadata(text, dim=True)` - Dimmed white text for secondary info

[→ See cli/list_formatting.md for complete API](../../cli/list_formatting.md)

#### From cli/output.py (output routing)

```python
from dot_agent_kit.cli.output import user_output

user_output(formatted_text)  # Routes to stderr
```

## Data Flow

### 1. Artifact Discovery

```python
def gather_artifacts(level: ArtifactLevel) -> list[InstalledArtifact]:
    """Gather artifacts from settings based on level filter"""

    artifacts = []

    if level in (ArtifactLevel.USER, ArtifactLevel.ALL):
        # Read from ~/.claude/settings.json
        artifacts.extend(load_user_artifacts())

    if level in (ArtifactLevel.PROJECT, ArtifactLevel.ALL):
        # Read from ./.claude/settings.json
        artifacts.extend(load_project_artifacts())

    return artifacts
```

### 2. Filtering

```python
def filter_by_type(artifacts, artifact_type):
    """Filter artifacts by type (skill, command, agent, hook, doc)"""
    return [a for a in artifacts if a.type == artifact_type]


def filter_managed(artifacts):
    """Filter to only kit-managed artifacts"""
    return [a for a in artifacts if a.kit_id is not None]
```

### 3. Grouping

Artifacts are grouped into two main sections:

**Claude Artifacts**: skills, commands, agents, hooks
**Installed Items**: docs, kit_cli_commands

Within each section, artifacts are further grouped by type.

### 4. Formatting

Formatting differs based on view mode:

**Compact**: Uses `format_compact_list()`
- One line per artifact
- Shows level badge, name, source badge
- No blank lines between items

**Verbose**: Uses `format_verbose_list()`
- Multi-line per artifact
- Adds description (→ prefix)
- Adds kit reference (if applicable)
- Adds file path
- Blank line between artifacts

### 5. Output

All output goes to stderr via `user_output()`:
```python
user_output(formatted_output)  # stderr, not stdout
```

## Design Decisions

### Why Two Main Sections?

**Claude Artifacts** (skills, commands, agents, hooks):
- First-class extensions that modify Claude's behavior
- Invoked by Claude during conversations
- Define new capabilities

**Installed Items** (docs, kit CLI commands):
- Supporting resources
- Referenced but don't extend Claude directly
- Provide context and tooling

This separation helps users understand which artifacts actively extend Claude vs provide supporting materials.

### Why Extensive Filtering?

Users need to filter artifacts by:
- **Level** (user vs project) - Understand scope and precedence
- **Type** (skill, command, etc.) - Focus on specific artifact category
- **Source** (managed vs local) - See what's tracked by kit system

Multiple independent filters provide flexibility without overwhelming output.

### Why stderr for Output?

Routing to stderr keeps stdout clean for:
- Machine-readable data
- Command composition in scripts
- Piping to other tools

This allows: `dot-agent artifact list | grep foo` to work as expected.

### Why Both list and ls?

Provides flexibility:
- `list` - Explicit, clear intent
- `ls` - Shorter, familiar to Unix users

Both call identical implementation, so no code duplication.

## Usage Examples

### Basic Usage

```bash
# List all artifacts (default)
dot-agent artifact list

# Use shorter alias
dot-agent artifact ls
```

### Level Filtering

```bash
# Show only project-level artifacts
dot-agent artifact list --project
dot-agent artifact list -p

# Show only user-level artifacts
dot-agent artifact list --user
dot-agent artifact list -u

# Show all (explicit, but this is default)
dot-agent artifact list --all
dot-agent artifact list -a
```

### Type Filtering

```bash
# Show only skills
dot-agent artifact list --type skill

# Show only commands
dot-agent artifact list --type command

# Show only agents
dot-agent artifact list --type agent

# Show only hooks
dot-agent artifact list --type hook

# Show only docs
dot-agent artifact list --type doc
```

### Combined Filtering

```bash
# Show only project-level skills
dot-agent artifact list --project --type skill

# Show only user-level commands with details
dot-agent artifact list --user --type command --verbose

# Show only kit-managed agents at project level
dot-agent artifact list --project --type agent --managed
```

### Verbose Output

```bash
# Show detailed information
dot-agent artifact list --verbose
dot-agent artifact list -v

# Verbose with filtering
dot-agent artifact list -v --type skill
```

### Managed-Only

```bash
# Show only kit-managed artifacts
dot-agent artifact list --managed

# Combine with type filter
dot-agent artifact list --managed --type skill
```

## Testing

**Test file**: `tests/commands/artifact/test_list.py`

**Key test scenarios**:
1. Level filtering (--user, --project, --all)
2. Type filtering (each artifact type individually)
3. Managed-only filtering
4. Compact vs verbose formatting
5. Empty state (no artifacts installed)
6. Mixed levels and sources
7. Output format consistency (badges, indentation, colors)
8. Both list and ls commands produce identical output

## Related Files

**Same directory**:
- [formatting.md](formatting.md) - Artifact-specific formatters (5 functions)

**Similar commands**:
- [../hook/list.md](../hook/list.md) - Groups by lifecycle event instead of type
- [../kit/list.md](../kit/list.md) - Lists kits with optional artifact details

**Shared utilities**:
- [../../cli/list_formatting.md](../../cli/list_formatting.md) - 8 shared formatting functions

**Parent context**:
- [INDEX.md](INDEX.md) - Artifact commands overview
- [../INDEX.md](../INDEX.md) - All commands overview
- [../../INDEX.md](../../INDEX.md) - Package overview

## See Also

- Design standards: `/docs/agent/cli-list-formatting.md` (repository root)
- ArtifactLevel enum: `dot_agent_kit/core.py`
- Settings management: `dot_agent_kit/settings.py`
