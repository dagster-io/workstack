# Hook System

The dot-agent-kit hook system allows kits to execute custom scripts in response to Claude Code lifecycle events. This enables automated workflows, validation, logging, and custom integrations without modifying Claude Code settings directly.

## Overview

### Key Concepts

- **Hook**: A Python script that runs in response to a lifecycle event
- **Lifecycle Event**: A specific point in Claude Code execution (PreToolUse, PostToolUse, etc.)
- **Matcher**: A regex pattern that determines when a hook should execute
- **Router**: A central dispatcher that discovers and executes hooks
- **Hook Manifest**: A `hooks.toml` file that defines hooks for a kit

### Architecture

```
~/.claude/
├── settings.json           # Claude Code settings (router registered here once)
└── .dot-agent/
    ├── router.py           # Hook router script
    └── hooks/
        ├── my-kit/
        │   ├── hooks.toml  # Hook configuration
        │   └── script.py   # Hook script
        └── other-kit/
            └── ...
```

**Key principle**: Settings.json is modified ONCE during `dot-agent init` to register the router. After that, all hook management is file-based - no settings.json changes needed.

## Lifecycle Events

Hooks can respond to these Claude Code lifecycle events:

- **PreToolUse**: Before Claude Code uses a tool (Read, Write, Bash, etc.)
- **PostToolUse**: After Claude Code completes a tool use
- **PreUserMessage**: Before processing a user message
- **PostUserMessage**: After processing a user message

## Using Hooks

### Installing a Kit with Hooks

Hooks are installed automatically when you install a kit:

```bash
dot-agent init example-hooks
```

This will:

1. Setup router infrastructure (if first time)
2. Install the kit
3. Copy hooks to `~/.claude/.dot-agent/hooks/example-hooks/`

### Listing Installed Hooks

```bash
dot-agent hooks list
```

Output:

```
example-hooks (v0.1.0)
  ✓ pre-tool-example [enabled]
      Lifecycle: PreToolUse
      Matcher:   Bash
      Example hook that runs before Bash tool use

Total: 1 hooks (1 enabled, 0 disabled)
```

### Enabling/Disabling Hooks

Disable a hook:

```bash
dot-agent hooks disable example-hooks/pre-tool-example
```

Enable a hook:

```bash
dot-agent hooks enable example-hooks/pre-tool-example
```

**Note**: Hook path format is `kit-name/hook-name`

### Removing Hooks

Hooks are removed when you remove the kit:

```bash
dot-agent remove example-hooks
```

This deletes the entire `~/.claude/.dot-agent/hooks/example-hooks/` directory.

## Creating Hooks for Your Kit

### 1. Create Hook Directory Structure

```
your-kit/
├── kit.yaml
└── hooks/
    ├── hooks.toml
    └── my_hook.py
```

### 2. Define Kit Manifest (kit.yaml)

```yaml
name: your-kit
version: 1.0.0
description: Your kit with hooks
artifacts:
  hook:
    - hooks
```

### 3. Create Hook Manifest (hooks/hooks.toml)

```toml
kit_id = "your-kit"
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
enabled = true
description = "Log all file writes"
```

**Fields**:

- `name` (required): Unique hook name within the kit
- `lifecycle` (required): One of PreToolUse, PostToolUse, PreUserMessage, PostUserMessage
- `matcher` (required): Regex pattern matching context JSON (empty string = always match)
- `script` (required): Python script filename (must exist in hooks/ directory)
- `enabled` (optional): Default enabled state (default: true)
- `description` (optional): Human-readable description

### 4. Write Hook Script

```python
#!/usr/bin/env python3
"""Example hook script."""

import json
import sys


def main() -> int:
    """Main entry point."""
    try:
        # Read context from stdin
        context = json.loads(sys.stdin.read())

        # Your hook logic here
        tool_name = context.get("tool", "unknown")
        print(f"Hook executed for tool: {tool_name}", file=sys.stderr)

        # Return 0 for success, 1 for error
        return 0

    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Context Format**: The context JSON structure depends on the lifecycle event and is provided by Claude Code. Common fields:

- `tool`: Tool name (for ToolUse events)
- `user_message`: User message content (for UserMessage events)
- Additional event-specific fields

**Important**:

- Read context from stdin
- Write output to stdout (will be displayed)
- Write logs/errors to stderr
- Return 0 for success, non-zero for failure
- Hook failures don't block Claude Code execution

### 5. Test Locally

Create a test context file:

```json
{
  "tool": "Bash",
  "command": "ls -la"
}
```

Test your hook:

```bash
cat test_context.json | python3 hooks/my_hook.py
```

## Matcher Patterns

Matchers are regex patterns applied to the JSON-serialized context.

### Common Patterns

```toml
# Match any Bash tool use
matcher = "Bash"

# Match specific commands
matcher = "rm -rf"

# Match Write tool with specific paths
matcher = "Write.*config\\.json"

# Always run (empty matcher)
matcher = ""

# Complex pattern
matcher = "(Bash.*dangerous)|(Write.*secret)"
```

### Tips

- Context is serialized as JSON string before matching
- Use `.*` for wildcards
- Escape special regex characters (`\.`, `\*`, etc.)
- Test patterns with regex tools before deploying

## Local (Non-Kit) Hooks

You can create hooks outside of kits by manually creating directories in `~/.claude/.dot-agent/hooks/`:

```bash
mkdir -p ~/.claude/.dot-agent/hooks/my-local-hooks
```

Create `hooks.toml` and scripts following the same format. These hooks won't be tracked in dot-agent.toml but will be discovered by the router.

**Note**: Local hooks are not managed by dot-agent commands (install/remove). You must create and delete them manually.

## Troubleshooting

### Hooks Not Executing

1. **Check router setup**:

   ```bash
   ls ~/.claude/.dot-agent/router.py
   cat ~/.claude/settings.json | grep router
   ```

2. **Verify hook installation**:

   ```bash
   ls ~/.claude/.dot-agent/hooks/
   dot-agent hooks list
   ```

3. **Check hook is enabled**:

   ```bash
   dot-agent hooks list
   # Look for ✓ (enabled) vs ✗ (disabled)
   ```

4. **Test matcher**:
   - Check if matcher pattern is too specific
   - Try empty matcher `""` to always run
   - Verify regex syntax

### Hook Errors

Hook errors are logged to stderr but don't block Claude Code execution. Check Claude Code output for hook error messages:

```
[Hook Error] my-kit/my-hook: <error message>
```

### Router Not Registered

If router isn't in settings.json, run init again:

```bash
dot-agent init <any-kit>
```

The router setup is idempotent - it won't break existing hooks.

## Best Practices

### Performance

- Keep hooks fast (<100ms) to avoid slowing Claude Code
- Use async operations for network calls
- Cache expensive computations

### Error Handling

- Always catch exceptions
- Log errors to stderr
- Return non-zero exit codes on failure
- Don't crash Claude Code with uncaught exceptions

### Security

- Validate all input from context
- Don't execute arbitrary code from context
- Be careful with file operations
- Use subprocess with `check=True` and proper escaping

### Maintainability

- Write descriptive hook names and descriptions
- Document matcher patterns
- Version your hooks with kit version
- Test hooks in isolation before deploying

### Debugging

Add debug logging:

```python
import os

DEBUG = os.environ.get("DOT_AGENT_HOOK_DEBUG", "false") == "true"

if DEBUG:
    print(f"Debug: {context}", file=sys.stderr)
```

Run with debug:

```bash
DOT_AGENT_HOOK_DEBUG=true claude-code
```

## Examples

### Pre-Commit Validation

```toml
[[hooks]]
name = "pre-commit-check"
lifecycle = "PreToolUse"
matcher = "Bash.*git commit"
script = "pre_commit.py"
description = "Run checks before git commit"
```

### File Write Logger

```toml
[[hooks]]
name = "write-logger"
lifecycle = "PostToolUse"
matcher = "Write"
script = "log_writes.py"
description = "Log all file modifications"
```

### Custom Notifications

```toml
[[hooks]]
name = "notify"
lifecycle = "PostUserMessage"
matcher = ""
script = "notify.py"
description = "Send notifications after processing"
```

## Advanced Topics

### Multiple Hooks per Event

Multiple hooks can match the same lifecycle and context. They execute in discovery order (alphabetical by kit name).

### Hook Chaining

Hooks run sequentially. Earlier hooks cannot modify context for later hooks (context is read-only per execution).

### Hook Dependencies

Hooks cannot depend on other hooks. Each hook should be self-contained.

### Hook State

Hooks are stateless - each execution is independent. Use external storage (files, databases) if you need persistent state.

## FAQ

**Q: Can hooks modify Claude Code behavior?**
A: No. Hooks are observers - they can log, validate, and notify, but cannot modify tool execution or block operations.

**Q: Do hooks slow down Claude Code?**
A: Minimal impact if hooks are fast (<100ms). Slow hooks may introduce latency.

**Q: Can I use hooks without kits?**
A: Yes. Create directories manually in `~/.claude/.dot-agent/hooks/` with `hooks.toml` and scripts.

**Q: What happens if a hook crashes?**
A: The router catches errors, logs them, and continues. Claude Code execution is not affected.

**Q: Can hooks use third-party libraries?**
A: Yes, but you must ensure libraries are installed in the environment where Claude Code runs.

**Q: How do I update hooks?**
A: Reinstall the kit with `--force`:

```bash
dot-agent init your-kit --force
```

**Q: Can I have hooks in both user and project directories?**
A: Hooks are global (`~/.claude/.dot-agent/hooks/`), not project-specific. All projects share the same hooks.
