# dot-agent-kit

Kit management system for Claude Code.

## Installation

```bash
pip install dot-agent-kit
```

## Usage

```bash
dot-agent --help
```

## Creating Kits

### Kit Structure

A kit is a collection of Claude Code artifacts (agents, skills, commands) distributed as a package. Each kit requires:

1. **kit.yaml** - Manifest file with kit metadata and artifact paths
2. **Artifacts** - The actual agent, skill, and command files

### Namespace Pattern (Required)

**All bundled kits** must follow the namespace pattern:

```
{artifact_type}s/{kit_name}/...
```

This organizational pattern:

- Prevents naming conflicts when multiple kits are installed
- Makes it clear which kit an artifact belongs to
- Enables clean uninstallation of kit artifacts
- Keeps the `.claude/` directory organized

**Example structure:**

```
my-kit/
├── kit.yaml
├── agents/
│   └── my-kit/
│       └── my-agent.md
└── skills/
    └── my-kit/
        ├── tool-a/
        │   └── SKILL.md
        └── tool-b/
            └── SKILL.md
```

**Example kit.yaml:**

```yaml
name: my-kit
version: 1.0.0
description: My awesome Claude Code kit
artifacts:
  agent:
    - agents/my-kit/my-agent.md
  skill:
    - skills/my-kit/tool-a/SKILL.md
    - skills/my-kit/tool-b/SKILL.md
```

### Invocation Names vs File Paths

**Important**: Claude Code discovers artifacts by their filename/directory name, not the full path:

- **Agents**: Discovered by filename (e.g., `agents/my-kit/helper.md` → invoked as "helper")
- **Skills**: Discovered by directory name (e.g., `skills/my-kit/pytest/SKILL.md` → invoked as "pytest")
- **Commands**: Discovered by filename (e.g., `commands/my-kit/build.md` → invoked as "/build")

The namespace directory (`my-kit/`) is **organizational only** - it doesn't become part of the invocation name.

**Hyphenated naming convention**: Artifacts should use hyphenated naming that combines the kit name with the artifact purpose (e.g., `skills/devrun-make/SKILL.md` → invoked as "devrun-make"). This is the standard pattern for bundled kits as it keeps the directory structure flat while maintaining clear namespacing. The directory name determines the invocation name.

### Namespace Standards for Kit Types

**Bundled kits** (distributed with packages): Should follow hyphenated naming convention (e.g., `skills/kit-name-tool/`) to avoid naming conflicts and maintain clear organization.

**Project-local artifacts** (in `.claude/` not from kits): Can use any naming structure. These are project-specific and not distributed.

### Adopting Hyphenated Naming

To align with the standard hyphenated naming convention:

1. **Flatten directory structure with hyphenated names:**

   ```bash
   # Example: Convert skills/devrun/make/ to skills/devrun-make/
   mv skills/devrun/make skills/devrun-make
   mv skills/devrun/pytest skills/devrun-pytest
   ```

2. **Update kit.yaml artifact paths:**

   ```yaml
   artifacts:
     skill:
       - skills/devrun-make/SKILL.md # Was: skills/devrun/make/SKILL.md
       - skills/devrun-pytest/SKILL.md # Was: skills/devrun/pytest/SKILL.md
   ```

3. **Test installation** to verify paths are correct

## Hook System

Kits can include hooks that execute in response to Claude Code lifecycle events. Hooks enable automated workflows, validation, logging, and custom integrations.

### Architecture Overview

The hook system uses a **router pattern**:

1. **Router Script**: `~/.claude/.dot-agent/router.py` - Central dispatcher installed during first `dot-agent init`
2. **Hook Directories**: `~/.claude/.dot-agent/hooks/<kit-name>/` - Each kit gets its own directory
3. **Hook Manifests**: `hooks.toml` files define hook configurations
4. **Settings Registration**: Router is registered ONCE in `~/.claude/settings.json` during init
5. **Runtime Discovery**: Router scans hook directories when Claude Code triggers lifecycle events

**Key principle**: Settings.json is modified only once. All subsequent hook management is file-based, avoiding configuration corruption.

### Creating a Kit with Hooks

#### 1. Add Hook Directory Structure

```
my-kit/
├── kit.yaml
├── agents/
│   └── ...
└── hooks/
    ├── hooks.toml
    └── my_hook.py
```

#### 2. Define Hook Artifact in kit.yaml

```yaml
name: my-kit
version: 1.0.0
description: My kit with hooks
artifacts:
  agent:
    - agents/my-kit/my-agent.md
  hook:
    - hooks # Points to hooks directory
```

**Note**: Unlike other artifacts, hooks reference a directory, not individual files.

#### 3. Create hooks.toml Manifest

```toml
kit_id = "my-kit"
kit_version = "1.0.0"

[[hooks]]
name = "validate-bash"
lifecycle = "PreToolUse"
matcher = "Bash.*rm -rf"
script = "validate_bash.py"
enabled = true
description = "Prevent dangerous Bash commands"

[[hooks]]
name = "log-writes"
lifecycle = "PostToolUse"
matcher = "Write"
script = "log_writes.py"
enabled = false
description = "Log all file writes (disabled by default)"
```

**Required fields**:

- `kit_id`: Must match kit name
- `kit_version`: Must match kit version
- `name`: Unique hook name within kit
- `lifecycle`: One of PreToolUse, PostToolUse, PreUserMessage, PostUserMessage
- `matcher`: Regex pattern (empty string = always match)
- `script`: Python script filename in hooks/ directory

**Optional fields**:

- `enabled`: Default enabled state (default: true)
- `description`: Human-readable description

#### 4. Write Hook Scripts

```python
#!/usr/bin/env python3
"""Example hook script."""

import json
import sys


def main() -> int:
    """Main entry point for the hook."""
    try:
        # Read context from stdin
        context = json.loads(sys.stdin.read())

        # Your hook logic
        tool_name = context.get("tool", "unknown")
        print(f"[Hook] Executing for tool: {tool_name}", file=sys.stderr)

        # Return 0 for success
        return 0

    except Exception as e:
        print(f"[Hook] Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Hook script requirements**:

- Read context JSON from stdin
- Write output to stdout (displayed to user)
- Write logs/errors to stderr
- Return 0 for success, non-zero for failure
- Handle exceptions gracefully
- Be fast (<100ms recommended)

### Lifecycle Events

- **PreToolUse**: Before Claude Code uses a tool (Read, Write, Bash, etc.)
- **PostToolUse**: After tool execution completes
- **PreUserMessage**: Before processing user input
- **PostUserMessage**: After responding to user

### Matchers

Matchers are regex patterns applied to the JSON-serialized context:

```toml
# Match any Bash tool use
matcher = "Bash"

# Match specific commands
matcher = "rm -rf"

# Match Write tool with paths
matcher = "Write.*config\\.json"

# Always run (empty matcher)
matcher = ""
```

### Hook Installation Flow

When a user installs a kit with hooks:

1. `dot-agent init my-kit` runs
2. Router infrastructure setup (first time only):
   - Creates `~/.claude/.dot-agent/` directory
   - Copies `router.py` template
   - Registers router in `settings.json` (idempotent)
3. Kit installation:
   - Copies `hooks/` directory to `~/.claude/.dot-agent/hooks/my-kit/`
   - Tracks installation in `dot-agent.toml`
4. Runtime:
   - Claude Code triggers lifecycle event
   - Calls router with lifecycle name
   - Router scans `hooks/` directories
   - Loads matching `hooks.toml` files
   - Executes enabled hooks with matching patterns

### Hook Removal

Hooks are automatically removed when the kit is uninstalled:

```bash
dot-agent remove my-kit
```

This deletes the entire `~/.claude/.dot-agent/hooks/my-kit/` directory.

### Testing Hooks Locally

Before distributing your kit:

1. **Create test context**:

   ```json
   {
     "tool": "Bash",
     "command": "ls -la"
   }
   ```

2. **Test hook script**:

   ```bash
   cat test_context.json | python3 hooks/my_hook.py
   ```

3. **Install locally**:

   ```bash
   dot-agent init ./my-kit
   ```

4. **Verify installation**:

   ```bash
   dot-agent hooks list
   ```

5. **Test with Claude Code** by triggering the lifecycle event

### Hook Management Commands

Users can manage hooks after installation:

```bash
# List all hooks
dot-agent hooks list

# Enable a hook
dot-agent hooks enable my-kit/my-hook

# Disable a hook
dot-agent hooks disable my-kit/my-hook
```

### Best Practices

**Performance**:

- Keep hooks fast (<100ms)
- Use async operations for I/O
- Cache expensive computations

**Error Handling**:

- Always catch exceptions
- Log errors to stderr
- Return appropriate exit codes
- Don't crash Claude Code

**Security**:

- Validate context input
- Don't execute arbitrary code
- Be careful with file operations
- Sanitize subprocess inputs

**Maintainability**:

- Use descriptive names and descriptions
- Document matcher patterns
- Version hooks with kit
- Test in isolation

### Example Hooks

See `packages/dot-agent-kit/src/dot_agent_kit/data/kits/example-hooks/` for a complete example kit with hooks.

### Debugging

Add debug output:

```python
import os
import sys

DEBUG = os.environ.get("DOT_AGENT_HOOK_DEBUG") == "true"

if DEBUG:
    print(f"[Debug] Context: {context}", file=sys.stderr)
```

Run Claude Code with debug enabled:

```bash
DOT_AGENT_HOOK_DEBUG=true claude-code
```

### Hook Limitations

- Hooks are observers - they cannot modify tool execution or block operations
- Hooks cannot modify context for other hooks
- Hooks share the same Python environment as Claude Code
- Slow hooks may introduce latency
- Hook failures don't block Claude Code execution

### Documentation

For detailed hook documentation, see [.agent/docs/HOOKS.md](../../.agent/docs/HOOKS.md)
