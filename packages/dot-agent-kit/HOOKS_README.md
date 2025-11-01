# dot-agent Hook Management

The `dot-agent` CLI extends Claude Code's native hook functionality with kit-based distribution and management capabilities. This document covers what dot-agent adds beyond the core Claude Code hooks feature.

> **Note**: For general hook concepts, writing hook scripts, and hook execution behavior, refer to the [Claude Code hooks documentation](https://docs.claude.com/claude-code/hooks).

## Overview

dot-agent provides:

- **Kit-based hook distribution**: Bundle hooks with kits for easy sharing
- **Hook management CLI**: List and inspect installed hooks
- **Metadata tracking**: Know which kit installed which hook
- **Atomic operations**: Safe installation/removal with file locking
- **Project-level only**: Hooks are only installed at the project level (`./.claude/`) for safety and source control

> **Why project-level only?** User-level settings (`~/.claude/settings.json`) affect every project on your machine and are typically not under source control. Programmatically modifying them is too risky. Project-level hooks are safer, trackable in git, and team-shareable.

## Hook Management Commands

### List Installed Hooks

```bash
# List hooks in the current project (.claude/settings.json)
dot-agent hook list
```

Output shows:

- Kit and hook IDs (format: `kit-id:hook-id`)
- Lifecycle and matcher pattern

Example:

```
python-kit:style-checker [PreToolUse / Edit|Write]
security-kit:command-validator [PreToolUse / Bash]
```

### View Hook Details

```bash
# Show detailed information about a specific hook
dot-agent hook show python-kit:style-checker
```

Output includes:

- Full hook configuration
- Command that will be executed
- Timeout settings

### Validate Configuration

```bash
# Validate project-level settings.json
dot-agent hook validate
```

Checks for:

- Valid JSON structure
- Required fields in hook entries
- Proper metadata format
- Hook entry integrity

## Installing Hooks via Kits

Hooks are distributed as part of kits. When you install a kit containing hooks, they are automatically configured.

### Kit Manifest with Hooks

In your kit's `kit.yaml`:

```yaml
name: python-toolkit
version: 1.0.0
description: Python development hooks and tools
artifacts:
  hook:
    - hook_id: style-checker
      lifecycle: PreToolUse
      matcher: "Edit|Write"
      script: hooks/check-style.py
      description: Check Python style before edits
      timeout: 30
    - hook_id: import-sorter
      lifecycle: PostToolUse
      matcher: "Edit|Write"
      script: hooks/sort-imports.py
      description: Sort Python imports after edits
      timeout: 15
```

### Installing a Kit with Hooks

```bash
# Install entire kit (includes all hooks) to current project
dot-agent install python-toolkit
```

When hooks are installed:

1. Hook scripts are copied to `.claude/hooks/{kit-id}/`
2. Entries are added to `settings.json` with metadata
3. Hooks are merged into appropriate lifecycle/matcher groups

## Hook Metadata

dot-agent adds a `_dot_agent` field to each hook entry for tracking:

```json
{
  "type": "command",
  "command": "python3 .claude/hooks/python-toolkit/check-style.py",
  "timeout": 30,
  "_dot_agent": {
    "kit_id": "python-toolkit",
    "hook_id": "style-checker"
  }
}
```

This metadata enables:

- Tracking which kit installed each hook
- Clean uninstallation when removing kits

## Removing Hooks

When you remove a kit, its hooks are automatically cleaned up:

```bash
# Remove a kit and all its hooks
dot-agent remove python-toolkit
```

This will:

1. Remove hook entries from `settings.json`
2. Delete hook scripts from `.claude/hooks/{kit-id}/`
3. Clean up empty matcher groups
4. Preserve hooks from other kits

## Best Practices for Kit Authors

### Hook Script Location

Place hook scripts in a `hooks/` directory within your kit:

```
my-kit/
├── kit.yaml
├── hooks/
│   ├── validator.py
│   └── formatter.sh
└── skills/
    └── ...
```

### Sensible Defaults

- Set reasonable timeout values (15-30 seconds typical)

### Clear Hook IDs

Use descriptive hook IDs that indicate purpose:

- ✓ `style-checker`, `import-validator`, `security-scan`
- ✗ `hook1`, `myhook`, `temp`

### Documentation

Document each hook in your kit README:

- What it does
- When it triggers
- How to configure/customize
- Any dependencies or requirements

## Atomic Operations

All hook operations are atomic and safe:

1. File locking prevents concurrent modifications
2. Settings are written to a temporary file first
3. Temporary file is atomically renamed to `settings.json`
4. Hooks are validated during installation

This ensures `settings.json` is never left in a corrupted state. Use git to track changes and revert if needed.

## Comparison with Native Claude Code Hooks

| Feature             | Claude Code Native | dot-agent Addition        |
| ------------------- | ------------------ | ------------------------- |
| Hook execution      | ✓                  | Uses native               |
| Manual JSON editing | ✓                  | ✓                         |
| CLI management      | ✗                  | ✓ (list, show, validate)  |
| Kit distribution    | ✗                  | ✓                         |
| Metadata tracking   | ✗                  | ✓                         |
| Atomic writes       | Manual             | ✓ (with file locking)     |
| Validation          | Manual             | `dot-agent hook validate` |

## Troubleshooting

### Hooks Not Appearing in List

Verify kit installation:

```bash
# Check if kit is installed
dot-agent status
```

### Hook Not Executing

1. Verify matcher pattern matches your tool

2. Check script exists and is executable:

   ```bash
   ls -la .claude/hooks/kit-id/
   ```

3. Check hook details:
   ```bash
   dot-agent hook show kit-id:hook-id
   ```

### Invalid settings.json

Run validation to identify issues:

```bash
dot-agent hook validate
```

If corrupted, use git to restore:

```bash
git restore .claude/settings.json
```

## Summary

dot-agent enhances Claude Code's hook system by providing:

- **Distribution**: Bundle and share hooks via kits
- **Management**: CLI commands for listing and inspecting hooks
- **Safety**: Atomic operations with file locking
- **Organization**: Metadata tracking for kit ownership
- **Validation**: Built-in integrity checking

For writing hook scripts and understanding hook execution, refer to the Claude Code documentation. Use dot-agent for distributing, installing, and managing hooks across projects and teams.
