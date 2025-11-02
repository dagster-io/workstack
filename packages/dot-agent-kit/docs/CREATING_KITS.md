# Creating Kits with Hooks and Skills

This guide explains how to create dot-agent kits that bundle hooks and skills together for distribution. We'll use the `dignified-python` kit as a working example throughout.

## Table of Contents

1. [What is a Kit?](#what-is-a-kit)
2. [Kit Structure](#kit-structure)
3. [Creating a Kit](#creating-a-kit)
4. [Hook Configuration](#hook-configuration)
5. [Installation and Usage](#installation-and-usage)
6. [Troubleshooting](#troubleshooting)

## What is a Kit?

A kit is a bundled collection of dot-agent artifacts (hooks, skills, commands, agents) that can be installed as a single unit. Kits allow you to:

- **Package related functionality together** - Bundle hooks that suggest skills, along with the skills themselves
- **Share conventions across projects** - Distribute coding standards, best practices, and workflows
- **Simplify installation** - Users run one command instead of manually copying multiple files
- **Track installation state** - dot-agent knows which artifacts came from which kit for easy removal

## Kit Structure

A kit is a directory containing:

```
kits/dignified-python/
├── kit.toml                           # Kit manifest with metadata and hooks
├── hooks/
│   └── suggest_dignified.py           # Hook script
└── skills/
    └── dignified-python/
        └── SKILL.md                   # Skill definition
```

### Kit Manifest (kit.toml)

The kit manifest defines metadata, artifacts, and hooks. Here's the `dignified-python` manifest:

```toml
# Kit metadata
name = "dignified-python"
version = "0.1.0"
description = "Workstack Python coding standards with LBYL patterns"
license = "MIT"

# Artifacts bundled with this kit
[artifacts]
skill = [
  "skills/dignified-python/SKILL.md"
]

# Hooks section - inline hook definitions
[[hooks]]
hook_id = "suggest_dignified"
lifecycle = "PreToolUse"
matcher = "Edit|Write"
script = "hooks/suggest_dignified.py"
description = "Suggests loading dignified-python skill when editing Python files"
timeout = 30
```

## Creating a Kit

### Step 1: Create Directory Structure

```bash
mkdir -p kits/my-kit/hooks
mkdir -p kits/my-kit/skills/my-skill
```

### Step 2: Write the Kit Manifest

Create `kit.toml` with your kit's metadata:

```toml
name = "my-kit"
version = "0.1.0"
description = "My awesome kit"
license = "MIT"

[artifacts]
skill = ["skills/my-skill/SKILL.md"]

[[hooks]]
hook_id = "my_hook"
lifecycle = "PreToolUse"
matcher = "Edit|Write"
script = "hooks/my_hook.py"
description = "What this hook does"
timeout = 30
```

### Step 3: Create Hook Script

Hook scripts receive JSON on stdin and output messages to stdout:

```python
#!/usr/bin/env python3
"""My Hook - Does something useful."""

import json
import sys


def main():
    try:
        # Read JSON input from stdin
        data = json.load(sys.stdin)

        # Extract tool information
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        # Apply your filtering logic
        if should_trigger(file_path, tool_name):
            print("Load my-skill for guidance")

        # Exit 0 to allow operation (non-blocking)
        sys.exit(0)

    except Exception as e:
        # Don't break workflow on errors
        print(f"my-hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
```

### Step 4: Create Skill Definition

Create `skills/my-skill/SKILL.md` with your skill content:

```markdown
# My Skill

This skill provides guidance on...

## Key Principles

1. Principle one
2. Principle two

## Examples

...
```

## Hook Configuration

### Hook Fields

| Field         | Required | Description                                         |
| ------------- | -------- | --------------------------------------------------- |
| `hook_id`     | Yes      | Unique identifier (becomes script filename)         |
| `lifecycle`   | Yes      | When hook runs: `PreToolUse` or `PostToolUse`       |
| `matcher`     | Yes      | Tool name pattern (e.g., `"Edit"`, `"Edit\|Write"`) |
| `script`      | Yes      | Relative path to hook script in kit                 |
| `description` | Yes      | Human-readable explanation                          |
| `timeout`     | No       | Max execution time in seconds (default: 30)         |

### Hook Lifecycle

**PreToolUse Hooks:**

- Execute BEFORE a tool runs
- Receive `tool_name` and `tool_input` as JSON
- Can output suggestions or guidance
- Exit code 0 = allow operation to proceed
- Exit code 1 = block operation (use sparingly)

**Example PreToolUse input:**

```json
{
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "old_string": "...",
    "new_string": "..."
  }
}
```

**PostToolUse Hooks:**

- Execute AFTER a tool completes
- Receive `tool_name`, `tool_input`, and `tool_output`
- Can validate results or trigger follow-up actions

### Matcher Patterns

The `matcher` field determines which tools trigger your hook:

| Pattern         | Matches             |
| --------------- | ------------------- |
| `"Edit"`        | Only the Edit tool  |
| `"Write"`       | Only the Write tool |
| `"Edit\|Write"` | Edit OR Write tools |
| `"Bash"`        | Only Bash commands  |

### Hook Best Practices

1. **Be non-blocking** - Exit 0 unless you have a strong reason to block
2. **Be defensive** - Catch all exceptions to avoid breaking workflows
3. **Be specific** - Only trigger on relevant files/operations
4. **Be helpful** - Output clear, actionable messages
5. **Be fast** - Hooks should complete in milliseconds, not seconds
6. **Log errors to stderr** - Use `print(..., file=sys.stderr)` for debugging

### Dignified-Python Hook Example

The `suggest_dignified.py` hook demonstrates these practices:

```python
# Only trigger for Python files
if not file_path.endswith(".py"):
    sys.exit(0)

# Skip test files (different patterns apply)
skip_patterns = ["test_", "_test.py", "conftest.py", "/tests/", "/migrations/"]
if any(pattern in file_path.lower() for pattern in skip_patterns):
    sys.exit(0)

# Output clear suggestion
print("Load the dignified-python skill to abide by Python standards")

# Always non-blocking
sys.exit(0)
```

## Installation and Usage

### Installing a Kit

From within a project:

```bash
# Install kit from bundled kits
dot-agent kit install dignified-python

# Verify installation
dot-agent kit list
```

### What Happens During Installation

1. **Hooks are copied** to `.claude/hooks/{kit-name}/`
   - `suggest_dignified.py` → `.claude/hooks/dignified-python/suggest_dignified.py`

2. **Skills are copied** to `.claude/skills/{skill-name}/`
   - `SKILL.md` → `.claude/skills/dignified-python/SKILL.md`

3. **settings.json is updated** with hook entries:
   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Edit|Write",
           "hooks": [
             {
               "type": "command",
               "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/dignified-python/suggest_dignified.py",
               "timeout": 30,
               "_dot_agent": {
                 "kit_id": "dignified-python",
                 "hook_id": "suggest_dignified"
               }
             }
           ]
         }
       ]
     }
   }
   ```

### Verifying Installation

After installation, you can verify:

```bash
# Check installed kits
dot-agent kit list

# Check hooks directory
ls .claude/hooks/

# Check skills directory
ls .claude/skills/

# Check settings.json
cat .claude/settings.json
```

### Testing the Hook

To test that your hook triggers correctly:

1. Edit a Python file (not a test file)
2. Look for the suggestion message in Claude's output
3. Check that the skill loads properly

### Removing a Kit

```bash
# Remove kit and all its artifacts
dot-agent kit remove dignified-python

# This removes:
# - .claude/hooks/dignified-python/
# - .claude/skills/dignified-python/
# - Hook entries from settings.json
```

## Troubleshooting

### Hook Not Triggering

**Problem:** Hook doesn't run when expected

**Solutions:**

1. Check `matcher` pattern matches the tool being used
2. Verify hook script has correct permissions (`chmod +x`)
3. Check hook script for syntax errors
4. Look for error messages in Claude's output
5. Verify settings.json has correct hook entry

### Hook Errors

**Problem:** Hook runs but produces errors

**Solutions:**

1. Check that hook script uses correct shebang (`#!/usr/bin/env python3`)
2. Verify JSON parsing is correct
3. Add debugging output to stderr: `print(f"Debug: {data}", file=sys.stderr)`
4. Make sure hook doesn't depend on external packages (keep dependencies minimal)
5. Check that exception handling catches all errors

### Skill Not Loading

**Problem:** Hook suggests skill but skill doesn't load

**Solutions:**

1. Verify skill was copied to `.claude/skills/{skill-name}/SKILL.md`
2. Check that skill filename is exactly `SKILL.md` (case-sensitive)
3. Verify skill content is valid markdown
4. Make sure skill name in hook message matches directory name

### Installation Fails

**Problem:** `dot-agent kit install` fails

**Solutions:**

1. Verify kit.toml syntax is valid TOML
2. Check that all referenced files exist in the kit
3. Ensure artifact paths are relative to kit root
4. Verify hook script paths are correct
5. Check that kit name doesn't conflict with existing kit

### Hook Blocks Operation

**Problem:** Hook exits with code 1 and blocks the tool

**Solutions:**

1. Review hook logic - should it really block?
2. Change exit code to 0 for non-blocking behavior
3. Add specific conditions for when blocking is appropriate
4. Log reason for blocking to stderr for debugging

### Common Pitfalls

1. **Using absolute paths** - Always use relative paths in kit.toml
2. **Missing shebang** - Hook scripts need `#!/usr/bin/env python3`
3. **Not handling exceptions** - Always wrap main logic in try/except
4. **Slow hooks** - Keep hooks fast (< 100ms ideally)
5. **Broad matching** - Be specific about which tools/files trigger hooks
6. **Forgetting to exit 0** - Always explicitly exit with code 0 for non-blocking

## Advanced Topics

### Multiple Hooks in One Kit

You can define multiple hooks in a single kit:

```toml
[[hooks]]
hook_id = "hook_one"
lifecycle = "PreToolUse"
matcher = "Edit"
script = "hooks/hook_one.py"
description = "First hook"

[[hooks]]
hook_id = "hook_two"
lifecycle = "PostToolUse"
matcher = "Bash"
script = "hooks/hook_two.py"
description = "Second hook"
```

### Combining Multiple Artifact Types

Kits can bundle different artifact types:

```toml
[artifacts]
skill = [
  "skills/skill-one/SKILL.md",
  "skills/skill-two/SKILL.md"
]
command = [
  "commands/my-command.md"
]
agent = [
  "agents/my-agent/agent.md"
]
```

### Kit Versioning

Use semantic versioning for kits:

```toml
version = "1.2.3"  # MAJOR.MINOR.PATCH
```

- **MAJOR**: Breaking changes to hook interface or skill structure
- **MINOR**: New features, backward-compatible
- **PATCH**: Bug fixes, backward-compatible

## Example: Dignified Python Kit Workflow

This section shows the complete workflow using the dignified-python kit.

### 1. Install the Kit

```bash
cd /path/to/your/project
dot-agent kit install dignified-python
```

### 2. Verify Installation

```bash
# Check it's installed
dot-agent kit list
# Output: dignified-python (0.1.0)

# Verify files
ls .claude/hooks/dignified-python/
# Output: suggest_dignified.py

ls .claude/skills/
# Output: dignified-python/
```

### 3. Edit a Python File

When you edit a Python file (not a test), Claude will see:

```
Load the dignified-python skill to abide by Python standards
```

### 4. The Skill Provides Guidance

The skill provides:

- LBYL (Look Before You Leap) exception handling patterns
- Python 3.13+ type annotation standards
- Path operation best practices
- Code style guidelines

### 5. Remove When Done

```bash
dot-agent kit remove dignified-python
```

## Next Steps

- **Create your own kit** - Start with a simple skill and hook
- **Share with others** - Distribute your kit for others to use
- **Iterate on patterns** - Refine your hooks and skills based on usage
- **Contribute improvements** - Share successful patterns back to the community

## References

- [Hook Models](../src/dot_agent_kit/models/hook.py) - Hook data structures
- [Kit Models](../src/dot_agent_kit/models/kit.py) - Kit manifest models
- [Hook Installation](../src/dot_agent_kit/operations/hook_install.py) - Installation logic
- [Dignified Python Kit](../src/dot_agent_kit/data/kits/dignified-python/) - Complete example
