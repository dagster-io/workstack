# Agent-Delegating Commands Pattern

## What

Commands that immediately delegate to specialized agents through the `Task()` tool. These are lightweight wrappers (~40-50 lines) that shell out to agents for complete workflow orchestration.

**Architecture:**

```
Slash Command (lightweight wrapper)
    ↓ delegates via Task()
Agent (orchestration + AI reasoning)
    ↓ calls via Bash/Task
Python Kit Command (mechanical operations)
    ↓ returns
JSON Output (structured results)
```

## Why

This pattern provides a two-part value proposition:

### 1. Context Reduction

Commands immediately delegate to agents, declining accumulated conversation context. This prevents context pollution and keeps workflows focused.

**Problem it solves:** As users interact with the assistant, context accumulates. Commands that perform complex workflows can carry unnecessary context, leading to:

- Increased token costs
- Slower execution
- Potential context confusion

**Solution:** Immediate delegation creates a clean context boundary. The agent starts with only what it needs to know.

### 2. Model Selection

Different agents can use different models based on their needs. Fast, mechanical workflows can use Haiku for speed and cost efficiency, while complex analysis can use Sonnet or Opus.

**Examples:**

- `gt-update-pr-submitter`: Uses Haiku (simple mechanical workflow)
- `gt-branch-submitter`: Uses Haiku but includes AI-driven diff analysis
- `devrun`: Uses Haiku for fast tool execution

## When

Use agent-delegating commands when:

✅ **Multi-step workflows** - Operations involving multiple sequential steps
✅ **Orchestration needed** - Tasks requiring coordination between multiple tools
✅ **Speed matters** - Workflows that benefit from fast model execution (Haiku)
✅ **Context minimization** - Operations where fresh context improves outcomes
✅ **Reusability desired** - Agents can be invoked directly or via multiple commands

**DO NOT use for:**

❌ **Simple operations** - Single tool invocations that don't need orchestration
❌ **High-frequency commands** - Operations called many times in quick succession
❌ **Precise tool control** - When you need exact control over tool invocation order

## How

### Architecture Components

**1. Command File (.md)**

Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/[kit-name]/commands/[namespace]/[command].md`

Purpose: Thin wrapper that delegates to agent

Structure:

```markdown
---
description: Brief description of what the command does
---

# Command Title

User-facing documentation and usage instructions.

## Implementation

Task(
subagent_type="[agent-name]",
description="Brief task description",
prompt="Detailed instruction for the agent",
model="haiku" # Optional: specify model if different from agent default
)
```

**2. Agent File (.md)**

Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/[kit-name]/agents/[namespace]/[agent].md`

Purpose: Orchestrate the complete workflow

Structure:

```markdown
---
name: agent-name
description: What this agent does
model: haiku # or sonnet, opus
color: green
tools: Read, Bash, Task
---

You are a specialized agent that [purpose].

## Your Core Responsibilities

[List key responsibilities]

## Complete Workflow

### Step 1: [First Phase]

[Detailed instructions]

### Step 2: [Second Phase]

[Detailed instructions]

...
```

**3. Python Kit Command (optional)**

Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/[kit-name]/kit_cli_commands/[namespace]/[command].py`

Purpose: Handle mechanical preprocessing and validation

**Important:** Python commands should NOT contain heavy business logic. They should:

- Validate inputs
- Check state
- Execute mechanical operations
- Return structured JSON

**4. Kit Manifest Registration**

Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/[kit-name]/kit.yaml`

All components must be registered:

```yaml
kit_cli_commands:
  - name: command-name
    path: kit_cli_commands/namespace/file.py

artifacts:
  agent:
    - agents/namespace/agent-name.md
  command:
    - commands/namespace/command-name.md
```

New components don't exist until registered in this manifest.

### Implementation Steps

1. **Create the agent file** with complete workflow instructions
2. **Simplify the command file** to just delegate to the agent
3. **Keep Python command as-is** (if it exists and follows preprocessing pattern)
4. **Register the agent** in `kit.yaml` manifest
5. **Test the workflow** end-to-end

## Examples from Codebase

### Simple Mechanical Workflow: /gt:update-pr

**Command:** 49 lines (reduced from 161)

```markdown
Task(
subagent_type="gt-update-pr-submitter",
description="Update PR workflow",
prompt="Execute the complete update-pr workflow for the current branch",
model="haiku"
)
```

**Agent:** `gt-update-pr-submitter` (Haiku model)

- Executes Python command
- Parses JSON results
- Handles errors
- Displays results

**Python:** 174 lines of mechanical git operations

### Complex Multi-Phase: /gt:submit-branch

**Command:** ~40 lines

```markdown
Task(
subagent_type="gt-branch-submitter",
description="Submit branch workflow",
prompt="Execute the complete submit-branch workflow...",
model="haiku"
)
```

**Agent:** `gt-branch-submitter` (Haiku model, 3-phase workflow)

1. Pre-analysis (mechanical ops)
2. Diff analysis (AI-driven)
3. Post-analysis (PR submission)

**Python:** Two-phase commands for pre/post operations

### Workflow Orchestration: /erk:create-planned-wt

**Command:** 42 lines (reduced from 338, 87% reduction)

**Agent:** `planned-wt-creator`

- Detects plan files
- Validates structure
- Creates worktree via erk CLI
- Displays next steps

## Benefits

### Maintainability

- **Commands stay <50 lines** - Clear, focused contract with users
- **Agents handle complexity** - Workflow logic lives in one place
- **Python stays testable** - Pure logic without AI orchestration

### Performance

- **Model selection** - Use Haiku for speed, Sonnet/Opus for complexity
- **Context efficiency** - Fresh context for each workflow
- **Parallel execution** - Multiple commands can delegate to same agent

### Reusability

- **Agents invokable directly** - Can be called from code via Task tool
- **Shared logic** - Multiple commands can use the same agent
- **Composable workflows** - Agents can invoke other agents

## Anti-Patterns

### ❌ Embedding Orchestration in Commands

Don't put multi-step workflow logic directly in command files:

```markdown
# BAD: 161 lines of orchestration in command file

1. Run this command
2. Parse the output
3. If error, do this
4. Otherwise, do that
5. Format results
   ...
```

Instead: Delegate to an agent that handles orchestration.

### ❌ Passing Flags Through Business Logic

Don't pass `dry_run` or similar flags through business logic:

```python
# BAD
def execute_workflow(ctx, dry_run=False):
    if not dry_run:
        git.commit(...)
```

Instead: Use dependency injection (Noop wrappers) as documented in AGENTS.md.

### ❌ Using Agent Delegation for Simple Operations

Don't create agent-delegating commands for single tool invocations:

```markdown
# BAD: Overkill for a simple operation

Task(
subagent_type="file-reader",
prompt="Read this file"
)
```

Instead: Just use the tool directly in the command.

## Implementation Guide

For detailed step-by-step technical implementation instructions, see:
[Command-Agent Delegation How-To](../agent/command-agent-delegation.md)

## Related Documentation

- [Erk Coding Standards](../../AGENTS.md) - Project coding standards and patterns
- [Kit CLI Commands](../agent/kit-cli-commands.md) - Python preprocessing patterns
- [Command-Agent Delegation How-To](../agent/command-agent-delegation.md) - Step-by-step implementation
