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

| Option      | Short | Values                           | Default | Description                                         |
| ----------- | ----- | -------------------------------- | ------- | --------------------------------------------------- |
| `--user`    | `-u`  | flag                             | -       | Show only user-level artifacts (~/.claude/)         |
| `--project` | `-p`  | flag                             | -       | Show only project-level artifacts (./.claude/)      |
| `--all`     | `-a`  | flag                             | ✓       | Show artifacts from both levels                     |
| `--type`    | -     | skill, command, agent, hook, doc | all     | Filter by artifact type                             |
| `--verbose` | `-v`  | flag                             | -       | Show detailed information (descriptions, paths)     |
| `--managed` | -     | flag                             | -       | Show only kit-managed artifacts (in dot-agent.toml) |

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

Both `list` and `ls` commands call the same implementation function `_list_artifacts_impl()`.

**Uses formatting from**:

- `artifact/formatting.py` - [formatting.md](formatting.md)
- `cli/list_formatting.py` - [../../cli/list_formatting.md](../../cli/list_formatting.md)
- `cli/output.py` - Routes to stderr

**Data flow**:

1. Gather artifacts from settings (`~/.claude/` and/or `./.claude/`)
2. Apply filters (level, type, managed)
3. Group into sections (Claude Artifacts vs Installed Items)
4. Format (compact or verbose)
5. Output to stderr

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

## Related Files

- [formatting.md](formatting.md) - Artifact-specific formatters
- [../hook/list.md](../hook/list.md) - Hook list command
- [../kit/list.md](../kit/list.md) - Kit list command
- [../../cli/list_formatting.md](../../cli/list_formatting.md) - Shared formatting utilities
