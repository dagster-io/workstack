---
name: dot-agent-skill-creator
description: This skill should be used when creating new skills for the dot-agent system or updating existing skills to follow dot-agent best practices. It provides patterns for creating skills with CLI commands, hooks for deterministic discovery, and progressive disclosure following both Anthropic standards and dot-agent specific idioms. Essential when building skills that need to be reliably discovered and that leverage dot-agent's Python package system for sophisticated functionality.
---

# dot-agent Skill Creator

Create effective skills for the dot-agent system that combine Anthropic's progressive disclosure principles with dot-agent's powerful CLI and hook patterns.

## Overview

dot-agent skills extend Anthropic's skill standards with:

- **CLI commands** instead of bundled scripts for better testability and discoverability
- **Hooks** for deterministic skill triggering
- **Python packages** for sophisticated, well-engineered functionality
- **Progressive disclosure** for token-efficient loading

## Skill Creation Workflow

### Step 1: Understand the Use Case

Gather concrete examples of how the skill will be used:

- What triggers the skill? (file types, commands, patterns)
- What functionality does it provide?
- When should it activate automatically?
- What CLI commands would be helpful?

Example questions to ask:

- "What file types or patterns should trigger this skill?"
- "Can you give examples of tasks this skill will help with?"
- "Should this skill activate automatically in certain contexts?"
- "What reusable commands would be helpful?"

### Step 2: Plan the Skill Architecture

Determine the skill components:

1. **Core skill file** (SKILL.md)
   - Main instructions and workflow
   - References to detailed patterns
   - Quick decision trees

2. **Reference files** (references/)
   - Detailed patterns and examples
   - Domain-specific knowledge
   - Complex workflows

3. **CLI commands** (via kit)
   - Reusable Python functionality
   - Testable, discoverable tools
   - External library integration

4. **Hooks** (for automatic triggering)
   - File pattern matchers
   - Context reminders
   - Skill activation hints

### Step 3: Initialize the Skill Structure

Use the Anthropic skill initializer, then adapt for dot-agent:

```bash
# Initialize basic structure
scripts/init_skill.py <skill-name> --path <output-directory>

# Remove scripts directory (we'll use CLI commands instead)
rm -rf <skill-name>/scripts

# Remove assets if not needed
rm -rf <skill-name>/assets
```

### Step 4: Write the SKILL.md

Follow this structure:

```markdown
---
name: skill-name
description:
  [
    Third-person description of when to use this skill,
    including specific triggers and use cases,
  ]
---

# Skill Title

## Overview

[1-2 sentences explaining what this skill enables]

## Quick Start / Decision Tree

[Immediate guidance for common scenarios]

## Core Workflow

[Step-by-step process, referencing CLI commands]

## CLI Commands

[List of available dot-agent run commands]

## Resources

### references/

[List reference files with descriptions]

## Activation

[When this skill activates automatically via hooks]
```

See `references/skill-structure.md` for detailed patterns.

### Step 5: Create CLI Commands (Optional but Recommended)

Instead of bundling Python scripts, create CLI commands:

1. **Create a kit** with the skill
2. **Add Python package** with commands
3. **Make commands discoverable** via `dot-agent run`

Example kit structure:

```
my-kit/
├── kit.toml
├── skills/
│   └── my-skill/
│       ├── SKILL.md
│       └── references/
└── src/
    └── my_kit/
        ├── __init__.py
        └── commands.py
```

See `references/cli-commands.md` for implementation details.

### Step 6: Configure Hooks for Deterministic Discovery

Add hooks to ensure the skill activates when needed:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*.py", // File pattern
        "hooks": [
          {
            "type": "command",
            "command": "dot-agent run my-kit reminder-hook",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

The reminder hook outputs a brief message like:

```
🔴 Load my-skill when editing Python files
```

See `references/hooks.md` for complete patterns.

### Step 7: Add Reference Documentation

Create reference files for detailed patterns:

- **references/patterns.md** - Common implementation patterns
- **references/examples.md** - Complete working examples
- **references/troubleshooting.md** - Common issues and solutions
- **references/api.md** - If the skill works with specific APIs

Keep references focused and scannable with clear headers.

### Step 8: Test the Skill

Verify the skill works correctly:

1. **Test CLI commands** (if created):

   ```bash
   dot-agent run <kit-name> <command>
   ```

2. **Test hook activation**:
   - Edit a file that should trigger the skill
   - Verify reminder appears in context

3. **Test progressive disclosure**:
   - Ensure SKILL.md is concise (<5k words)
   - Verify references load only when needed

### Step 9: Package and Distribute

For standalone skills:

```bash
scripts/package_skill.py <path/to/skill-folder>
```

For skills in kits:

```bash
dot-agent kit package <kit-name>
```

## Key Principles

### dot-agent Specific

1. **CLI over scripts** - Create testable, discoverable commands
2. **Hooks for discovery** - Use deterministic triggers
3. **Python packages** - Leverage proper dependency management
4. **Kit integration** - Bundle related functionality

### From Anthropic Standards

1. **Progressive disclosure** - Core content visible, details in references
2. **Concrete examples** - Show, don't just tell
3. **Imperative writing** - Use verb-first instructions
4. **Token efficiency** - Keep main content under 5k words

## Common Patterns

### Pattern: File-Type Triggered Skill

For skills that activate on specific file types:

1. Create hook matcher for file pattern
2. Add reminder hook command
3. Include file-specific guidance in SKILL.md

See `references/file-triggered-skills.md`

### Pattern: Command-Enhanced Skill

For skills that provide CLI functionality:

1. Create Python package with commands
2. Add to kit.toml
3. Document commands in SKILL.md

See `references/cli-commands.md`

### Pattern: API Integration Skill

For skills working with external services:

1. Create operations interface
2. Add CLI commands for common operations
3. Include authentication guidance

See `references/api-skills.md`

## Resources

### references/

- `skill-structure.md` - Detailed SKILL.md structure and examples
- `cli-commands.md` - Creating dot-agent CLI commands
- `hooks.md` - Hook configuration and patterns
- `kit-integration.md` - Building skills as part of kits
- `file-triggered-skills.md` - Pattern for file-type activation
- `api-skills.md` - Pattern for API integration skills
- `migration-guide.md` - Converting Anthropic skills to dot-agent

## Examples

### Successful dot-agent Skills

1. **dignified-python** - Python coding standards with hook reminders
2. **gt-graphite** - Graphite CLI integration with commands
3. **devrun** - Test runner with automatic tool detection

Each demonstrates different dot-agent patterns effectively.
