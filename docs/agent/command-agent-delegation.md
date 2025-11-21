# Command-Agent Delegation Pattern

## Overview

**Command-agent delegation** is a design pattern for organizing complex workflow orchestration in Claude Code. Instead of embedding detailed step-by-step instructions directly in slash commands, commands delegate to specialized agents that handle all orchestration, error handling, and result reporting.

**Benefits:**

- **Separation of concerns**: Commands define "what", agents implement "how"
- **Maintainability**: Workflow logic centralized in agent files
- **Reusability**: Multiple commands can delegate to the same agent
- **Cost efficiency**: Agents can use lighter models (haiku) for mechanical tasks
- **Consistent error handling**: Agents provide uniform error formatting

## When to Delegate

Use this decision framework to determine if delegation is appropriate:

### ✅ Good Candidates for Delegation

- **Multi-step workflows** (3+ sequential operations)
- **Complex error handling** (multiple failure modes with context-specific guidance)
- **State management** (tracking workflow progress across steps)
- **Tool orchestration** (coordinating git, CLI tools, JSON parsing)
- **Repeated patterns** (same workflow used in multiple commands)

### ❌ Keep Inline (No Delegation)

- **Simple wrappers** (single tool invocation with no logic)
- **Direct pass-through** (command just forwards to another tool)
- **Trivial operations** (1-2 steps with no error handling)

### Decision Examples

| Scenario | Delegate? | Rationale |
|----------|-----------|-----------|
| Run pytest with specialized output parsing | ✅ Yes | Complex parsing, multiple tools (devrun agent) |
| Create worktree with validation, JSON parsing, formatted output | ✅ Yes | Multi-step workflow with error handling (planned-wt-creator) |
| Submit branch: stage, diff analysis, commit, PR creation | ✅ Yes | Complex orchestration with git + GitHub CLI (git-branch-submitter) |
| Run single git command with no processing | ❌ No | Simple wrapper, no orchestration needed |
| Display help text or documentation | ❌ No | No workflow, just content display |

## Delegation Patterns

### Pattern 1: Simple Tool Delegation

**Use case:** Delegate to a specialized tool runner that handles parsing and error reporting.

**Example:** `/fast-ci` and `/all-ci` → `devrun` agent

**Characteristics:**
- Agent runs development tools (pytest, pyright, ruff, etc.)
- Specialized output parsing per tool
- Iterative error fixing
- Cost efficiency with lighter model

**Command structure:**
```markdown
---
description: Run fast CI checks iteratively (unit tests only)
---

# /fast-ci

Delegates to the `devrun` agent to run unit tests and type checking...

Task(
    subagent_type="devrun",
    description="Run fast CI checks",
    prompt="Run pytest tests/unit and pyright"
)
```

### Pattern 2: Workflow Orchestration

**Use case:** Multi-step workflow with complex orchestration and error handling.

**Examples:**
- `/gt:submit-branch` → `gt-branch-submitter` agent
- `/erk:create-planned-wt` → `planned-wt-creator` agent

**Characteristics:**
- Agent coordinates multiple operations (git, CLI tools, parsing)
- Rich error messages with context-aware suggestions
- JSON parsing and validation
- Formatted user-facing output
- Typically uses haiku model for cost efficiency

**Command structure:**
```markdown
---
description: Create worktree from existing plan file on disk
---

# /erk:create-planned-wt

Delegates the complete worktree creation workflow to the `planned-wt-creator` agent...

Task(
    subagent_type="planned-wt-creator",
    description="Create worktree from plan",
    prompt="Execute the complete planned worktree creation workflow"
)
```

### Pattern 3: Shared Workflow Documentation

**Use case:** Multiple commands share the same underlying workflow logic.

**Example:** `/fast-ci` and `/all-ci` both reference `.claude/docs/ci-iteration.md`

**Characteristics:**
- Shared workflow document in `.claude/docs/`
- Multiple commands reference via `@` syntax
- Reduces duplication across commands
- Agent implements shared workflow

**Shared doc reference:**
```markdown
@.claude/docs/ci-iteration.md
```

## Implementation Guide

### Step 1: Create Agent File

**Location:** `.claude/agents/<category>/<agent-name>.md`

Example: `.claude/agents/erk/planned-wt-creator.md`

**Required frontmatter:**

```yaml
---
name: agent-name               # Used in Task subagent_type
description: One-line summary  # Shown in kit registry
model: haiku                   # haiku | sonnet | opus
color: blue                    # UI color coding
tools: Read, Bash, Task        # Available tools
---
```

**Agent structure:**

```markdown
You are a specialized agent that [purpose]...

**Philosophy**: [Design principles and goals]

## Your Core Responsibilities

1. [Responsibility 1]
2. [Responsibility 2]
...

## Complete Workflow

### Step 1: [First Major Step]

[Detailed instructions for this step]

**Error handling:**
[How to handle errors in this step]

### Step 2: [Second Major Step]

...

## Best Practices

[Agent-specific patterns and anti-patterns]

## Quality Standards

[Verification checklist]
```

### Step 2: Update Command to Delegate

**Location:** `.claude/commands/<category>/<command-name>.md`

Example: `.claude/commands/erk/create-planned-wt.md`

**Command structure:**

```markdown
---
description: Brief one-line summary
---

# /command-name

[Brief description of what the command does]

## Usage

```bash
/command-name [arguments]
```

## What This Command Does

Delegates to the `agent-name` agent, which handles:

1. [Step 1]
2. [Step 2]
...

## Prerequisites

- [Prerequisite 1]
- [Prerequisite 2]
...

## Implementation

When this command is invoked, delegate to the agent:

```
Task(
    subagent_type="agent-name",
    description="Brief task description",
    prompt="Execute the complete workflow"
)
```

The agent handles all workflow orchestration, error handling, and result reporting.
```

**Target:** <50 lines total for the command file

### Step 3: Choose Agent Model

**Model selection criteria:**

| Model | Use Case | Examples |
|-------|----------|----------|
| **haiku** | Fast, cost-efficient orchestration; mechanical workflows | devrun, planned-wt-creator, git-branch-submitter |
| **sonnet** | Balanced; requires analysis and reasoning | (none currently, but suitable for complex analysis) |
| **opus** | Rare; highly complex reasoning requiring most capable model | (avoid unless necessary) |

**Default:** Use `haiku` for workflow orchestration unless you need complex reasoning.

### Step 4: Add to Kit Registry (if bundled)

If the agent is part of a bundled kit (not project-specific), add to the kit's registry entry:

**Location:** `.agent/kits/<kit-name>/registry-entry.md`

Update the "Available Agents" section:

```markdown
## Available Agents

- **agent-name**: [Brief description]. Use Task tool with `subagent_type="agent-name"`
```

## Agent Specifications

### Frontmatter Requirements

All agents MUST include frontmatter with these fields:

```yaml
---
name: agent-name           # Unique name, kebab-case
description: Brief summary # Shown in registry and UI
model: haiku               # Model selection
color: blue                # UI color (blue, green, red, cyan)
tools: Read, Bash, Task    # Available tools (comma-separated)
---
```

**Naming convention:**
- Use `kebab-case` (hyphens, not underscores)
- Pattern: `{product}-{noun}-{verb}` (e.g., `git-branch-submitter`)
- Alternative: `{noun}-{verb}` (e.g., `planned-wt-creator`)
- Must be unique across kit + project agents

### Error Handling Template

All agents MUST use a consistent error format:

```
❌ Error: [Brief description in 5-10 words]

Details: [Specific error message, relevant context, or diagnostic info]

Suggested action:
  1. [First concrete step to resolve]
  2. [Second concrete step if needed]
  3. [Third concrete step if needed]
```

**Key principles:**
- Brief, scannable error description
- Specific diagnostic details
- Actionable suggestions (not vague)
- Numbered steps for clarity

### Best Practices for Agents

**DO:**
- ✅ Use absolute paths (never `cd`)
- ✅ Parse command output directly (no temporary files)
- ✅ Provide rich error context
- ✅ Trust JSON output from tools
- ✅ Include quality standards checklist
- ✅ Document scope constraints clearly

**DON'T:**
- ❌ Change directories (`cd` commands)
- ❌ Write temporary files unnecessarily
- ❌ Mix orchestration with implementation logic
- ❌ Assume agent can navigate filesystem interactively
- ❌ Skip error handling for edge cases

## Examples from Codebase

### Example 1: Simple Tool Delegation

**Command:** `/fast-ci`

**Delegates to:** `devrun` agent

**Pattern:** Command delegates to specialized tool runner for parsing and error reporting

**Command file (simplified):**
```markdown
---
description: Run fast CI checks iteratively (unit tests only)
---

# /fast-ci

Task(
    subagent_type="devrun",
    description="Run fast CI checks",
    prompt="Run pytest tests/unit and pyright iteratively until all pass"
)
```

**Why delegation:**
- Specialized output parsing (pytest, pyright)
- Iterative error fixing
- Cost efficient (haiku model)

### Example 2: Workflow Orchestration

**Command:** `/erk:create-planned-wt`

**Delegates to:** `planned-wt-creator` agent

**Pattern:** Multi-step workflow with validation, tool invocation, JSON parsing, formatted output

**Command file:**
```markdown
---
description: Create worktree from existing plan file on disk
---

# /erk:create-planned-wt

Delegates the complete worktree creation workflow to the `planned-wt-creator` agent, which handles:

1. Auto-detect most recent `*-plan.md` file at repository root
2. Validate plan file (exists, readable, not empty)
3. Run `erk create --plan <file>` with JSON output
4. Display plan location and next steps

Task(
    subagent_type="planned-wt-creator",
    description="Create worktree from plan",
    prompt="Execute the complete planned worktree creation workflow"
)
```

**Agent responsibilities:**
- Plan file detection and validation
- Execute `erk create --plan` with JSON parsing
- Rich error handling with helpful suggestions
- Formatted output with next steps

**Why delegation:**
- Multi-step orchestration (detect → validate → create → report)
- Complex error handling (5+ error modes with context-specific guidance)
- JSON parsing and validation
- Formatted user-facing output

**Result:** Command reduced from 338 lines to 43 lines (87% reduction)

### Example 3: Git Workflow Orchestration

**Command:** `/git:submit-branch`

**Delegates to:** `git-branch-submitter` agent

**Pattern:** Complex git workflow with staging, diff analysis, commit generation, PR creation

**Command file:**
```markdown
---
description: Create git commit and submit branch as PR using git + GitHub CLI
---

# /git:submit-branch

Delegates to the `git-branch-submitter` agent, which handles:

1. Check for uncommitted changes and commit them if needed
2. Run pre-analysis phase (get branch info)
3. Analyze all changes and generate commit message
4. Create commit and push to remote
5. Create PR with GitHub CLI

Task(
    subagent_type="git-branch-submitter",
    description="Submit branch workflow",
    prompt="Execute the complete submit-branch workflow for the current branch"
)
```

**Agent responsibilities:**
- Git status verification
- Staging uncommitted changes
- Diff analysis for commit message generation
- Git commit creation
- Push to remote with upstream tracking
- PR creation via GitHub CLI

**Why delegation:**
- Complex workflow (6+ sequential steps)
- Rich diff analysis and commit message generation
- Multiple external tools (git, gh CLI)
- Error handling for git authentication, branch state, etc.

## Anti-Patterns

### ❌ Don't: Run Tools Directly When Agent Exists

**Wrong:**
```markdown
# Command that manually runs pytest
Execute: `pytest tests/unit`
Parse output...
```

**Right:**
```markdown
# Command that delegates to devrun
Task(
    subagent_type="devrun",
    prompt="Run pytest tests/unit"
)
```

### ❌ Don't: Embed Orchestration in Command Files

**Wrong:**
```markdown
# Command with 300+ lines of step-by-step instructions
## Step 1: Detect files
## Step 2: Validate
## Step 3: Execute
...
```

**Right:**
```markdown
# Command delegates to agent
Task(subagent_type="agent-name", ...)
```

### ❌ Don't: Duplicate Error Handling Across Commands

**Wrong:**
```markdown
# Command 1 with inline error handling
If error X: print "Error: ..."

# Command 2 with duplicate inline error handling
If error X: print "Error: ..."
```

**Right:**
```markdown
# Both commands delegate to same agent
# Agent handles all errors consistently
Task(subagent_type="shared-agent", ...)
```

### ❌ Don't: Mix Delegation and Inline Logic

**Wrong:**
```markdown
# Command that partly delegates but also has inline steps
Step 1: Do X inline
Step 2: Task(subagent_type="agent", ...)
Step 3: Do Y inline
```

**Right:**
```markdown
# Command fully delegates
Task(subagent_type="agent", prompt="Complete workflow")
```

## Agent Discovery

When you need to find available agents:

1. **Check kit registry:** `.agent/kits/kit-registry.md`
   - Lists all installed kits with their agents
   - Shows how to invoke each agent

2. **Browse agents directory:** `.claude/agents/`
   - Project-specific agents organized by category
   - Read agent files for detailed capabilities

3. **Check AGENTS.md checklist:**
   - Quick reference table for common tasks
   - Links to relevant agents and documentation

## Quality Standards

### For Commands

✅ **Target metrics:**
- <50 lines total
- Single Task tool invocation
- Clear prerequisites section
- Brief "What This Command Does" with numbered steps

✅ **Required sections:**
- Usage examples
- Prerequisites
- What This Command Does (with delegation statement)
- Implementation (Task tool invocation)

### For Agents

✅ **Required structure:**
- Complete frontmatter (name, description, model, color, tools)
- Philosophy statement
- Core responsibilities list
- Complete workflow (step-by-step)
- Error handling (with consistent format)
- Best practices section
- Quality standards checklist

✅ **Error handling:**
- Consistent error template
- Specific diagnostic details
- Actionable suggestions

✅ **Scope constraints:**
- Clear list of agent responsibilities
- Clear list of forbidden actions

## Migration Checklist

When refactoring an existing command to use delegation:

- [ ] Create agent file with frontmatter
- [ ] Migrate workflow steps from command to agent
- [ ] Migrate error handling from command to agent
- [ ] Update command to delegation-only (<50 lines)
- [ ] Add agent to kit registry (if bundled)
- [ ] Update AGENTS.md checklist (if pattern is common)
- [ ] Update docs/agent/guide.md navigation
- [ ] Test agent workflow end-to-end
- [ ] Verify error handling for all failure modes

## Related Documentation

- [AGENTS.md](../../AGENTS.md) - Quick reference checklist
- [docs/agent/guide.md](guide.md) - Documentation navigation
- [.agent/kits/kit-registry.md](../../.agent/kits/kit-registry.md) - Installed kits and agents
