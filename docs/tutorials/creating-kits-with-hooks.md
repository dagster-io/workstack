# Creating Kits with Hooks

## Introduction

This tutorial guides you through creating bundled kits that combine artifacts (skills, commands, agents) with hooks that automatically execute in response to workflow events.

### What are kits?

Kits are distributable packages that bundle Claude artifacts with configuration and automation. They enable you to:

- Package related artifacts together for distribution
- Include hooks that provide contextual guidance
- Version and distribute development workflows
- Share team standards and practices

### What are hooks?

Hooks are scripts that execute automatically in response to workflow events like editing files or submitting prompts. They can:

- Suggest loading relevant skills based on file context
- Validate operations before they execute
- Provide just-in-time guidance to Claude
- Enforce team standards and practices

### Why combine them?

Combining artifacts with hooks creates self-contained, context-aware development kits that automatically activate when needed. For example, a Python standards kit can automatically suggest loading coding guidelines when editing Python files.

## Prerequisites

### Required Knowledge

- Basic understanding of Claude artifacts (skills, commands, agents)
- Familiarity with YAML configuration
- Basic Python scripting (for hook implementation)

### Tools Needed

- `dot-agent` CLI (for installing/managing kits)
- Access to the `packages/dot-agent-kit` package in workstack repository
- Text editor for creating kit files

## Kit Structure Overview

### Directory Layout

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/<kit-name>/
├── kit.yaml                    # Kit manifest (required)
├── skills/                     # Skill artifacts (optional)
│   └── <skill-name>/
│       └── SKILL.md
├── commands/                   # Command artifacts (optional)
│   └── <command-name>.md
├── agents/                     # Agent artifacts (optional)
│   └── <agent-name>.md
└── hooks/                      # Hook scripts (optional)
    └── <hook-name>.py
```

### Manifest Format

The `kit.yaml` file defines the kit's metadata, artifacts, and hooks:

```yaml
name: kit-name # Unique identifier (kebab-case)
version: 0.1.0 # Semantic version
description: Brief description # What the kit provides
license: MIT # License identifier

artifacts: # Artifact declarations
  skill: # Artifact type
    - skills/skill-name/SKILL.md
  command:
    - commands/command-name.md
  agent:
    - agents/agent-name.md

hooks: # Hook definitions (optional)
  - id: hook-identifier # Unique hook ID
    lifecycle: PreToolUse # When to trigger (must be valid Claude Code lifecycle)
    matcher: "**/*.py" # File pattern to match (optional, see notes below)
    script: hooks/script.py # Path to hook script
    description: What it does # Human-readable description
    timeout: 30 # Execution timeout (seconds, defaults to 30)
```

### Artifact Types

Kits can include three types of artifacts:

1. **Skills** - Domain knowledge and guidelines loaded into context
2. **Commands** - Slash commands that expand to prompts
3. **Agents** - Specialized subagents for complex tasks

## Step-by-Step: Creating a Kit with Hooks

We'll create the `dignified-python` kit as a worked example. This kit combines Python coding standards with a hook that suggests loading the skill when editing Python files.

### Step 1: Create Kit Directory Structure

Create the base kit directory and subdirectories:

```bash
mkdir -p packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python/{skills/dignified-python,hooks}
```

Expected structure:

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python/
├── skills/
│   └── dignified-python/
└── hooks/
```

### Step 2: Create Kit Manifest

Create `kit.yaml` in the kit directory:

```yaml
name: dignified-python
version: 0.1.0
description: Workstack Python coding standards with automatic suggestion hook
license: MIT

artifacts:
  skill:
    - skills/dignified-python/SKILL.md

hooks:
  - id: suggest-dignified-python
    lifecycle: UserPromptSubmit
    script: hooks/suggest-dignified-python.py
    description: Suggests loading dignified-python skill on every prompt
    timeout: 30
```

### Step 3: Add Skill Artifact

Copy your skill file to the kit structure:

```bash
cp .claude/skills/dignified-python/SKILL.md \
   packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python/skills/dignified-python/SKILL.md
```

**Important:** Kit artifacts should NOT include frontmatter. The installer adds frontmatter automatically during installation.

### Step 4: Create Hook Script

Create `hooks/suggest-dignified-python.py`:

```python
#!/usr/bin/env python3
"""
Dignified Python Skill Suggestion Hook

Injects dignified-python skill suggestion on every user prompt.
This ensures Claude always has access to Python coding standards.
"""

import json
import sys


def main():
    try:
        # Read JSON input from stdin
        data = json.load(sys.stdin)

        # Always output suggestion (runs on every prompt)
        print("Load the dignified-python skill to abide by Python standards")

        # Exit 0 to allow prompt to proceed
        # For prompt-submit lifecycle, stdout is injected as context for Claude
        sys.exit(0)

    except Exception as e:
        # Print error for debugging but don't block workflow
        print(f"dignified-python hook error: {e}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
```

### Step 5: Verify Kit Structure

Verify all files are in place:

```bash
tree packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python
```

Expected output:

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python
├── hooks
│   └── suggest-dignified-python.py
├── kit.yaml
└── skills
    └── dignified-python
        └── SKILL.md
```

## Hook Definition Details

### Lifecycle Types

Hooks use Claude Code's official lifecycle event names. The `lifecycle` field **must** be one of these exact values:

| Lifecycle Event      | When it triggers                             | Matcher used?                                 |
| -------------------- | -------------------------------------------- | --------------------------------------------- |
| `PreToolUse`         | Before each tool executes                    | Yes - tool names or file patterns             |
| `PostToolUse`        | After each tool completes                    | Yes - tool names or file patterns             |
| `PostCustomToolCall` | After MCP tool completes, before PostToolUse | Yes - MCP tool names                          |
| `UserPromptSubmit`   | When user submits a prompt                   | No - runs on all prompts                      |
| `Notification`       | When Claude sends a notification             | No                                            |
| `Stop`               | When main agent finishes                     | No                                            |
| `SubagentStop`       | When subagent (Task tool) finishes           | No                                            |
| `PreCompact`         | Before context compaction                    | Yes - `manual` or `auto`                      |
| `SessionStart`       | When session starts/resumes                  | Yes - `startup`, `resume`, `clear`, `compact` |
| `SessionEnd`         | When session ends                            | No                                            |

#### Common Lifecycles

**`PreToolUse`** - Executes before each tool call (Edit, Write, Bash, etc.):

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

**Use cases:** Context-aware skill suggestions, pre-operation validation, file-specific guidance

**`UserPromptSubmit`** - Executes when user submits a message:

```json
{
  "prompt": "User's message content"
}
```

**Use cases:** Workflow reminders, context loading suggestions, policy enforcement

### Matcher Patterns

The `matcher` field is **optional** in kit.yaml. When omitted, it defaults to `"*"` (wildcard).

Matchers filter when hooks execute:

| Pattern       | Matches             | Example                            |
| ------------- | ------------------- | ---------------------------------- |
| `**/*.py`     | All Python files    | `src/main.py`, `tests/test_foo.py` |
| `src/**/*.ts` | TypeScript in src   | `src/utils/helper.ts`              |
| `Edit\|Write` | Specific tools      | Only Edit and Write operations     |
| `*.{js,jsx}`  | Multiple extensions | JavaScript and JSX files           |
| `*`           | Match everything    | Wildcard (default if omitted)      |

**For tool-based lifecycles (`PreToolUse`, `PostToolUse`):**

- File patterns match against `tool_input.file_path`
- Tool patterns match against `tool_name`
- Combine with `\|` for multiple values (e.g., `Edit|Write`)
- Matcher field is useful for filtering by file type or tool

**For prompt-based lifecycles (`UserPromptSubmit`, `Notification`, `Stop`, etc.):**

- Matchers are not used by Claude Code
- You should omit the `matcher` field for these hooks
- If included, it defaults to wildcard `*` and is stored but not evaluated

### Script Requirements

Hook scripts must follow these requirements:

1. **Executable format:** Python 3 scripts that read from stdin
2. **JSON input:** Scripts receive context as JSON on stdin
3. **Text output:** Print messages to stdout for display to user
4. **Exit codes:**
   - `0` - Allow operation to proceed (non-blocking)
   - Non-zero - Block operation (use sparingly)
5. **Error handling:** Catch exceptions to prevent blocking workflow

**Example template:**

```python
#!/usr/bin/env python3
import json
import sys

def main():
    try:
        # Read context from stdin
        data = json.load(sys.stdin)

        # Extract relevant fields
        tool_name = data.get("tool_name", "")
        file_path = data.get("tool_input", {}).get("file_path", "")

        # Implement your logic
        if should_suggest(file_path):
            print("Your suggestion message here")

        # Always exit 0 for non-blocking hooks
        sys.exit(0)

    except Exception as e:
        print(f"Hook error: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
```

### Timeout Considerations

Hook timeouts prevent long-running scripts from blocking the workflow:

- **Default:** 30 seconds (recommended)
- **Range:** 1-120 seconds
- **Behavior:** Process is terminated if timeout is exceeded
- **Recommendation:** Keep hooks fast (<1 second) for good UX

## Installing and Testing

### Installation Commands

#### Install to Project Directory

```bash
dot-agent kit install dignified-python --project
```

This installs to `.claude/` in the current project.

#### Install to User Directory

```bash
dot-agent kit install dignified-python --user
```

This installs to `~/.claude/` for all projects.

**Note:** Hooks can only be installed at project level for security reasons.

#### Force Overwrite

```bash
dot-agent kit install dignified-python --project --force
```

Use `--force` to overwrite existing artifacts.

### Verification Checklist

After installation, verify these components:

#### 1. Skill Installation

Check `.claude/skills/dignified-python/SKILL.md`:

- File exists
- Contains frontmatter:
  ```yaml
  ---
  __dot_agent:
    kit_id: dignified-python
    kit_version: 0.1.0
    artifact_type: skill
    artifact_path: skills/dignified-python/SKILL.md
  ---
  ```
- Content matches original skill

#### 2. Hook Installation

Check `.claude/hooks/dignified-python/suggest-dignified-python.py`:

- File exists
- Content matches original script
- File is executable (`chmod +x` applied)

#### 3. Settings Configuration

Check `.claude/settings.json` contains:

```json
{
  "hooks": {
    "tool-call": [
      {
        "matcher": "**/*.py",
        "hooks": [
          {
            "command": "python3 \"/absolute/path/.claude/hooks/dignified-python/suggest-dignified-python.py\"",
            "timeout": 30,
            "_dot_agent": {
              "kit_id": "dignified-python",
              "hook_id": "suggest-dignified-python"
            }
          }
        ]
      }
    ]
  }
}
```

Verify:

- Hook appears under `tool-call` lifecycle
- Matcher is `**/*.py`
- Command uses absolute path
- Timeout is 30 seconds
- `_dot_agent` metadata tracks kit and hook IDs

#### 4. Kit Configuration

Check `dot-agent.toml` contains:

```toml
[kits.dignified-python]
kit_id = "dignified-python"
version = "0.1.0"
source = "dignified-python"
installed_at = "2025-11-02T..."
artifacts = [
  ".claude/skills/dignified-python/SKILL.md",
]

[[kits.dignified-python.hooks]]
id = "suggest-dignified-python"
lifecycle = "tool-call"
matcher = "**/*.py"
script = "hooks/suggest-dignified-python.py"
description = "Suggests loading dignified-python skill when editing Python files"
timeout = 30
```

### Testing Hook Execution

#### Manual Test

Test the hook script directly:

```bash
echo '{"tool_name": "Edit", "tool_input": {"file_path": "src/test.py"}}' | \
  python3 .claude/hooks/dignified-python/suggest-dignified-python.py
```

Expected output:

```
Load the dignified-python skill to abide by Python standards
```

#### Test Edge Cases

Test that hook skips test files:

```bash
echo '{"tool_name": "Edit", "tool_input": {"file_path": "tests/test_example.py"}}' | \
  python3 .claude/hooks/dignified-python/suggest-dignified-python.py
```

Expected: No output (hook exits without suggesting)

#### Live Test

Try editing a Python file in your project:

1. Use Claude to edit any `.py` file (not in test directories)
2. Hook should trigger before the Edit/Write tool executes
3. You should see: "Load the dignified-python skill to abide by Python standards"
4. The edit operation should proceed normally (non-blocking)

### Troubleshooting

#### Kit Not Found

**Error:** `ValueError: No resolver found for: dignified-python`

**Solution:** Ensure the kit directory exists at the correct path and contains `kit.yaml`

```bash
ls packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python/kit.yaml
```

#### Frontmatter Parse Error

**Error:** `yaml.scanner.ScannerError: while scanning an alias`

**Cause:** Artifact file contains markdown `---` separators that are mistaken for frontmatter

**Solution:** This has been fixed in the code. The frontmatter parser now only matches at the start of files.

#### Hook Not Triggering

**Checks:**

1. Verify hook is in `.claude/settings.json`
2. Check matcher pattern matches your file
3. Ensure tool name matches (Edit/Write)
4. Test hook script manually
5. Check Claude error messages

#### Permission Denied

**Error:** Permission denied when executing hook

**Solution:** Make hook script executable:

```bash
chmod +x .claude/hooks/dignified-python/suggest-dignified-python.py
```

## Best Practices

### When to Use Hooks

**Good Use Cases:**

- Contextual skill suggestions based on file type
- Reminding about team conventions before operations
- Providing just-in-time documentation
- Validating file paths or patterns

**Avoid Using Hooks For:**

- Long-running operations (use agents instead)
- Operations requiring user input
- Critical business logic (hooks can be disabled)
- Operations with side effects (hooks may run multiple times)

### Security Considerations

1. **Code Review:** Always review hook scripts before installation
2. **Project-Level Only:** Hooks intentionally cannot be installed at user level
3. **Non-Blocking:** Default to exit code 0 to avoid disrupting workflow
4. **Input Validation:** Validate all JSON input fields
5. **Error Handling:** Catch all exceptions to prevent crashes
6. **Minimal Privileges:** Don't request unnecessary file system access
7. **No Secrets:** Never include credentials or secrets in hook scripts

### Performance Guidelines

1. **Fast Execution:** Keep hooks under 100ms for good UX
2. **Early Exit:** Check conditions early and exit when not applicable
3. **Avoid I/O:** Minimize file reads, network calls, or subprocess execution
4. **Efficient Patterns:** Use simple string operations over regex when possible
5. **Timeout Budget:** Set realistic timeouts (30 seconds is generous)

### Maintenance Tips

1. **Version Artifacts:** Use semantic versioning for kits
2. **Document Changes:** Update descriptions when modifying hooks
3. **Test Edge Cases:** Test hooks with various file patterns and tools
4. **Monitor Performance:** Check hook execution time in practice
5. **Keep Simple:** One clear purpose per hook (split complex hooks)
6. **Update Together:** Keep kit artifacts and hooks in sync

## Reference Implementation

### Full Example: dignified-python Kit

#### Directory Structure

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/dignified-python/
├── kit.yaml
├── skills/
│   └── dignified-python/
│       └── SKILL.md
└── hooks/
    └── suggest-dignified-python.py
```

#### Annotated kit.yaml

```yaml
# Unique identifier - used for installation and tracking
name: dignified-python

# Semantic version - increment for updates
version: 0.1.0

# Brief description shown in kit listings
description: Workstack Python coding standards with automatic suggestion hook

# License identifier (MIT, Apache-2.0, etc.)
license: MIT

# Artifact declarations by type
artifacts:
  # Skill artifacts provide domain knowledge
  skill:
    - skills/dignified-python/SKILL.md # Relative to kit directory

  # Other types (not used in this kit):
  # command:
  #   - commands/command-name.md
  # agent:
  #   - agents/agent-name.md

# Hook definitions (optional)
hooks:
  - id: suggest-dignified-python # Unique hook identifier
    lifecycle: UserPromptSubmit # Trigger point (valid Claude Code lifecycle event)
    # matcher omitted - not needed for UserPromptSubmit lifecycle
    script: hooks/suggest-dignified-python.py # Path relative to kit directory
    description: Suggests loading dignified-python skill on every prompt
    timeout: 30 # Maximum execution time in seconds
```

#### Complete Hook Script

See Step 4 above for the full, annotated `suggest-dignified-python.py` implementation.

### Key Design Decisions

1. **Lifecycle: `UserPromptSubmit`** - Triggers on every user prompt, ensuring coding standards are always available
2. **No Matcher** - Not needed for UserPromptSubmit lifecycle; runs on all prompts
3. **Non-Blocking: Exit 0** - Always allows operations to proceed, hook is advisory only
4. **Simple Output** - Always suggests loading the skill without complex filtering
5. **Error Handling** - Catches all exceptions to prevent blocking workflow

## Advanced Topics

### Multiple Hooks in One Kit

You can define multiple hooks with different lifecycles and matchers:

```yaml
hooks:
  # Hook without matcher (runs on all prompts)
  - id: suggest-skill
    lifecycle: UserPromptSubmit
    script: hooks/suggest-skill.py
    description: Suggests loading skill on every prompt
    timeout: 30

  # Hook with matcher (filters by file pattern)
  - id: python-file-check
    lifecycle: PreToolUse
    matcher: "**/*.py"
    script: hooks/python-check.py
    description: Runs checks before editing Python files
    timeout: 30
```

### Hook Dependencies

Hooks cannot declare dependencies on each other. If you need sequential execution:

1. Combine logic into a single hook
2. Use priority ordering (hooks execute in definition order)
3. Consider using agents for complex workflows

### Conditional Installation

All artifacts and hooks in a kit are installed together. For optional components:

1. Create separate kits for different use cases
2. Use artifact selectors: `dot-agent install kit-name:artifact-name`
3. Document installation variations in kit README

## Next Steps

- Review existing bundled kits in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`
- Create a kit for your team's coding standards
- Experiment with different hook lifecycles and matchers
- Share your kits with the team via the bundled kits directory

## Resources

- Kit system architecture: `packages/dot-agent-kit/src/dot_agent_kit/`
- Hook installer: `packages/dot-agent-kit/src/dot_agent_kit/hooks/installer.py`
- Settings format: `packages/dot-agent-kit/src/dot_agent_kit/hooks/settings.py`
- Example kits: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/`
