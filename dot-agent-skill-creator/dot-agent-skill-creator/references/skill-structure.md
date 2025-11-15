# Skill Structure for dot-agent

## Complete SKILL.md Template

````markdown
---
name: skill-name
description: This skill should be used when [specific trigger conditions]. It provides [key functionality]. Essential for [primary use cases].
---

# Skill Title

Brief tagline explaining the skill's purpose.

## Overview

[1-2 paragraphs explaining what the skill enables, its key features, and when it's most valuable]

## Quick Start / Decision Tree

[Immediate guidance for the most common scenarios - should be scannable in seconds]

WHEN: [condition]
DO: [action]

WHEN: [condition]
DO: [action]

## Core Workflow

### Step 1: [Action]

[Brief description]

```bash
# Example command
dot-agent run kit-name command-name
```
````

### Step 2: [Action]

[Brief description]

## CLI Commands

Available via `dot-agent run <kit-name>`:

- **command-1** - Brief description
- **command-2** - Brief description
- **command-3 <arg>** - Brief description with argument

## Resources

### references/

- `patterns.md` - Common implementation patterns
- `examples.md` - Complete working examples
- `api-reference.md` - Detailed API documentation

## Activation

This skill activates automatically when:

- Editing files matching `*.ext` pattern
- Running specific commands
- Working in certain contexts

Hook configuration available in kit installation.

````

## Writing Effective Descriptions

The description field is crucial for discovery. Follow these patterns:

### Good Descriptions

```yaml
description: This skill should be used when writing tests for Python code that depends on external services (APIs, databases, email, etc.). It provides patterns for creating fake implementations that enable fast, deterministic testing without real I/O operations. Essential when tests need to verify business logic with external dependencies, handle error conditions, or test CLI commands.
````

Key elements:

- Starts with "This skill should be used when..."
- Lists specific trigger conditions
- Describes what it provides
- Mentions "Essential" scenarios

### Poor Descriptions

```yaml
description: Testing patterns for Python  # Too vague
description: Use this for tests  # Second person, unclear
description: Fake-based testing  # Just a title, no context
```

## Progressive Disclosure Patterns

### Level 1: SKILL.md Core Content

Keep under 300 lines. Include:

- Quick reference/decision tree
- Core workflow (5-10 steps max)
- CLI command list
- References to detailed docs

### Level 2: Reference Files

Each reference file focuses on one aspect:

```markdown
# patterns.md - Implementation Patterns

## Pattern: [Name]

### When to Use

[Specific conditions]

### Implementation

[Code example with explanation]

### Variations

[Alternative approaches]
```

### Level 3: External Resources

For very detailed content:

- Link to external documentation
- Reference kit repository
- Point to example projects

## Section Templates

### Quick Decision Tree

```markdown
## Quick Start Decision Tree

To determine the approach:

1. **[Question]?** → [Action]
2. **[Question]?** → [Action]
3. **[Question]?** → See `references/detailed-guide.md`
```

### CLI Commands Section

````markdown
## CLI Commands

This skill provides the following commands via `dot-agent run <kit-name>`:

### Data Processing

- **process-data <input> <output>** - Transform data between formats
  ```bash
  dot-agent run my-kit process-data input.json output.yaml
  ```
````

### Validation

- **validate <file>** - Check file against schema
  ```bash
  dot-agent run my-kit validate config.yaml
  ```

For command implementation details, see `references/cli-commands.md`

````

### Activation Section

```markdown
## Activation

### Automatic Triggering

This skill activates automatically via hooks when:
- Editing Python files (`*.py`)
- Working with test files (`test_*.py`, `*_test.py`)
- In directories containing `pyproject.toml`

### Manual Activation

Load the skill explicitly with:
- Command: Load skill `skill-name`
- Or use the Skill tool

### Hook Messages

When activated, you'll see:
````

🔴 Load skill-name for [context]

```

```

## Common Mistakes to Avoid

1. **Too much detail in SKILL.md** - Move to references
2. **No concrete examples** - Always show, don't just tell
3. **Missing CLI commands** - Document all available commands
4. **Unclear triggers** - Be specific about when skill activates
5. **No progressive disclosure** - Use references for details
6. **Poor description** - Makes skill hard to discover

## Examples from Successful Skills

### dignified-python

- Clear trigger: "when editing Python code"
- Quick reference table for common patterns
- References for detailed standards
- Hook for automatic activation

### gt-graphite

- CLI commands well documented
- Clear workflow for common tasks
- Progressive disclosure for complex operations
- Integration with git workflow

### devrun

- Auto-detection of test runners
- Clear decision tree for tool selection
- CLI commands for each tool
- Minimal main content, details in references
