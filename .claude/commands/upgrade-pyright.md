---
description: Upgrade Pyright to the latest version and sync dependencies
---

# Upgrade Pyright

This command automatically upgrades Pyright to the latest available version by checking PyPI, updating pyproject.toml, and syncing dependencies with uv.

## What This Command Does

1. **Check current version**: Read pyproject.toml to find the current Pyright version constraint
2. **Query latest version**: Search PyPI for the latest Pyright release
3. **Update pyproject.toml**: Replace the old version constraint with the new version
4. **Sync dependencies**: Run `uv sync` to install the new version
5. **Report results**: Show the version upgrade (old → new)

## Usage

```bash
/upgrade-pyright
```

## Implementation Steps

When this command is invoked:

### 1. Check Current Version

Read the current Pyright version constraint from pyproject.toml:

```bash
# Check the current installed version
uv pip list | grep pyright
```

Also read pyproject.toml to find the version constraint in the `[dependency-groups]` dev section.

### 2. Query Latest Version

Use WebSearch to find the latest Pyright version:

```markdown
Use WebSearch tool with query: "pyright latest version 2025 site:pypi.org OR site:github.com"
```

Parse the search results to identify the latest version number (format: `1.1.XXX`).

### 3. Update pyproject.toml

Use the Edit tool to update the Pyright version constraint:

- **Old string**: `"pyright>=1.1.XXX",` (where XXX is the current version)
- **New string**: `"pyright>=1.1.YYY",` (where YYY is the latest version)

**IMPORTANT**: Ensure the exact string match includes the quotes and comma as shown in the file.

### 4. Sync Dependencies

Run `uv sync` to install the new version:

```bash
uv sync
```

**Expected output**: Should show package resolution and installation progress. May show "Installed X packages" or "Uninstalled X packages" if versions changed.

### 5. Verify Installation

Confirm the new version is installed:

```bash
uv pip list | grep pyright
```

**Expected output**: Should show `pyright            1.1.YYY` (the new version).

### 6. Report Results

Output a summary showing:

- Old version → New version
- Sync status (success/failure)
- Any relevant release notes or changes from the search results

## Important Notes

- **NEVER use raw `pip install`** - always use `uv` for package management
- **DO NOT run pyright** after installing - this command only upgrades the tool
- **If already on latest version** - report "Already on latest version X.X.X" and exit
- **Read before editing** - always read pyproject.toml before using Edit tool

## Error Handling

If any step fails:

### WebSearch Fails

- Report: "Could not determine latest Pyright version from web search"
- Suggest: Ask user to manually specify version

### Edit Fails

- Report: "Could not update pyproject.toml - version constraint may have changed format"
- Show: The current line format from pyproject.toml
- Ask: User to verify the file format

### uv sync Fails

- Report: The full error message from uv sync
- Show: The exit code and any relevant stderr output
- Ask: User how to proceed (may need to resolve dependency conflicts)

### Version Already Latest

- Report: "Pyright is already at version X.X.X (latest)"
- Exit: Successfully without making changes

## Expected Output Format

After command completes:

```
## Pyright Upgrade Results

**Status**: SUCCESS

**Version Change**: 1.1.406 → 1.1.407

**Actions Taken**:
1. Found latest version: 1.1.407
2. Updated pyproject.toml dependency constraint
3. Ran uv sync successfully
4. Verified installation

**Notable Changes in 1.1.407**:
- Fixed bug with Python 3.14 compatibility
- Updated typeshed stubs
- Fixed partial function handling

**Next Steps**: Run `/fast-ci` or `/all-ci` to ensure the new version works with your codebase.
```

## Success Criteria

**SUCCESS**: Stop when:

- pyproject.toml is updated with new version
- `uv sync` exits with code 0
- `uv pip list` shows the new version installed

**SKIP**: Exit early if:

- Current version matches latest version (already up to date)

**ERROR**: Stop and report if:

- Cannot determine latest version
- Edit tool fails to update file
- uv sync fails with non-zero exit code
