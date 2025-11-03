# Implementation Plan: `dot-agent kit list`

## Summary

Add a new `dot-agent kit list` command to display installed kits in the current project, keeping `search` for browsing available kits from the registry.

## Design Decisions

Based on user input:

- **Keep `search` as-is**: Shows available kits from registry/bundled sources
- **Add `list` for installed kits**: Shows kits actually installed in current project
- **No filtering on `list`**: Simple display of all installed kits
- **Display information**: Kit name, version, installation date, source location

## Changes Required

### 1. Create list command implementation

**File**: `packages/dot-agent-kit/src/dot_agent_kit/commands/kit/list.py` (new)

Create a new Click command that:

- Accepts no arguments (lists all installed kits)
- Loads project config from `./.claude/dot-agent.toml` using existing config functions
- Iterates through installed kits and displays:
  - Kit name and version
  - Installation date (from `installed_at` field in `InstalledKit`)
  - Source location (from `source` field)
- Handles edge cases:
  - No kits installed (friendly message)
  - Not in a project directory (no `.claude/` directory exists)
- Uses `click.echo()` for all output
- Follows formatting style similar to `search` command

**Key implementation details:**

- Use existing `load_project_config()` from `dot_agent_kit.io.config`
- Access installed kits via `config.kits` dictionary
- Format output consistently with other commands
- Follow LBYL pattern (check directory exists before loading config)

### 2. Register list command in CLI

**File**: `packages/dot-agent-kit/src/dot_agent_kit/cli.py`

Changes needed:

- Import the new `list_installed_kits` function from `dot_agent_kit.commands.kit.list`
- Add registration line: `kit.add_command(list_installed_kits, name="list")`
- Place after existing `kit.add_command()` calls (around line 46)

### 3. Write tests

**File**: `packages/dot-agent-kit/tests/commands/kit/test_list.py` (new)

Test scenarios:

1. **Test listing installed kits with sample data**
   - Mock project config with multiple installed kits
   - Verify output includes name, version, date, source for each kit

2. **Test behavior when no kits installed**
   - Mock empty project config
   - Verify friendly message displayed

3. **Test behavior when not in project directory**
   - Mock missing `.claude/` directory
   - Verify appropriate error message

4. **Test output format**
   - Verify each field (name, version, date, source) is displayed correctly
   - Check formatting consistency

## Implementation Sequence

### Phase 1: Core command (do this first)

1. Create `commands/kit/list.py` with basic Click command structure
2. Implement kit loading from project config using existing functions
3. Add output formatting for each installed kit
4. Handle edge cases (no kits, no project directory)

### Phase 2: CLI integration

1. Import and register command in `cli.py`
2. Verify command appears in `dot-agent kit --help` output

### Phase 3: Testing

1. Write unit tests for list command (all scenarios above)
2. Run tests to ensure they pass
3. Manual verification with actual installed kits in a test project

## Success Criteria

- `dot-agent kit list` displays all installed kits with required fields:
  - Kit name and version
  - Installation date
  - Source location
- `dot-agent kit search` continues to work unchanged for browsing available kits
- All tests pass
- Command follows existing code patterns:
  - LBYL exception handling
  - `click.echo()` for output
  - Consistent formatting with other commands
  - Proper error messages for edge cases

## Related Files for Reference

| Purpose                          | File Path                                                          |
| -------------------------------- | ------------------------------------------------------------------ |
| Search command (similar pattern) | `packages/dot-agent-kit/src/dot_agent_kit/commands/kit/search.py`  |
| Install command (config loading) | `packages/dot-agent-kit/src/dot_agent_kit/commands/kit/install.py` |
| Config models                    | `packages/dot-agent-kit/src/dot_agent_kit/io/config.py`            |
| CLI registration                 | `packages/dot-agent-kit/src/dot_agent_kit/cli.py`                  |
| Existing kit tests               | `packages/dot-agent-kit/tests/commands/kit/`                       |
