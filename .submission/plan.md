---
enriched_by_create_enhanced_plan: true
session_id: 4c8a7bdb-e807-496f-9691-24b40be8c485
generated_at: 2025-11-21T00:00:00Z
---

# Command-Agent Delegation Pattern Implementation

## Executive Summary

Refactor `/erk:create-planned-wt` from a monolithic 338-line command with inline orchestration to a lightweight delegation command following the pattern established by `/gt:submit-branch` → `gt-branch-submitter`. This creates the new `planned-wt-creator` agent (haiku model) that handles all workflow orchestration and error formatting, while documenting the general command-agent delegation pattern for future use across the codebase.

The session exploration revealed two existing delegation patterns (`/fast-ci` and `/all-ci` delegating to `devrun`) and comprehensive documentation structures in `docs/agent/` that serve as guides for organizing the new pattern documentation.

## Critical Context

### Existing Delegation Patterns

The codebase currently has **two primary delegation patterns**:

1. **CI commands → devrun agent**
   - `/fast-ci` and `/all-ci` both delegate to `devrun` agent
   - Share workflow documentation at `.claude/docs/ci-iteration.md`
   - Use explicit Task tool invocation with reminders to NEVER use Bash directly
   - Pattern: Command is minimal, agent handles all orchestration

2. **gt commands → gt-branch-submitter agent** (referenced in user request)
   - `/gt:submit-branch` delegates to `gt-branch-submitter` agent
   - Agent uses haiku model for cost efficiency
   - Agent handles complete workflow: pre-analysis → diff analysis → commit generation → submission
   - Agent formats all errors for user consumption

### Documentation Structure

**Location philosophy** (from `docs/agent/guide.md`):

- `docs/agent/` = Agent-focused reference (patterns, rules, navigation)
- `docs/writing/` = Human-readable guides
- Package-specific docs in package READMEs

**Existing pattern docs** in `docs/agent/`:

- `testing.md` - Testing architecture and patterns
- `hooks.md` - Hooks guide with lifecycle events
- `kit-cli-commands.md` - Python/LLM boundary patterns
- `cli-list-formatting.md` - CLI output conventions

All follow progressive disclosure: overview → patterns → examples → anti-patterns.

### Kit System Architecture

The project uses a **kit registry system** at `.agent/kits/`:

- Each kit has a `registry-entry.md` documenting purpose and artifacts
- Commands are stored in `.agent/kits/[kit-name]/commands/`
- Agents are stored in `.agent/kits/[kit-name]/agents/` OR `.claude/agents/`
- Registry entries specify usage patterns: "Use Task tool with subagent_type='X'"

**Installed kits** include: devrun, dignified-python, erk, fake-driven-testing, gt, fix-merge-conflicts.

### Current Command Structure

`/erk:create-planned-wt` currently:

- 338 lines of inline orchestration instructions
- Detailed step-by-step agent instructions embedded in command
- Complex error handling templates
- All logic in command file (no separation of concerns)

Target structure (like `/gt:submit-branch`):

- <50 lines total
- Frontmatter with description
- Brief "What This Command Does" section
- Single Task tool invocation to agent
- Agent handles all orchestration

## Implementation Plan

### Phase 1: Create Agent

**File**: `.claude/agents/erk/planned-wt-creator.md`

**Structure**:

```markdown
---
name: planned-wt-creator
description: Specialized agent for creating worktrees from plan files
model: haiku
color: blue
tools: Read, Bash, Task
---

[Agent philosophy and responsibilities]

## Complete Workflow

### Step 1: Detect and Validate Plan File

[Move detection logic from command]

### Step 2: Create Worktree with Plan

[Move erk create --plan orchestration from command]

### Step 3: Display Next Steps

[Move formatted output generation from command]

## Error Handling

[Move all error formatting from command]

## Best Practices

- Never change directory (use absolute paths)
- Never write to temporary files (use heredocs)

## Quality Standards

[Agent verification checklist]
```

**Key migrations**:

- Extract Step 0-3 workflow from command → agent steps
- Move error handling templates → agent error section
- Move validation logic → agent
- Keep JSON parsing and erk CLI interaction in agent
- Agent returns formatted output ready for user

### Phase 2: Update Command

**File**: `.claude/commands/erk/create-planned-wt.md`

**New structure** (following `/gt:submit-branch` pattern):

````markdown
---
description: Create worktree from existing plan file on disk
---

# /erk:create-planned-wt

Create a erk worktree from an existing plan file on disk.

## Usage

```bash
/erk:create-planned-wt
```
````

## What This Command Does

Delegates the complete worktree creation workflow to the `planned-wt-creator` agent, which handles:

1. Auto-detect most recent `*-plan.md` file at repository root
2. Validate plan file (exists, readable, not empty)
3. Run `erk create --plan <file>` with JSON output
4. Display plan location and next steps

## Prerequisites

- At least one `*-plan.md` file at repository root
- Current working directory in a git repository
- Typically run after `/persist-plan`

## Implementation

When this command is invoked, delegate to the planned-wt-creator agent:

```
Task(
    subagent_type="planned-wt-creator",
    description="Create worktree from plan",
    prompt="Execute the complete planned worktree creation workflow"
)
```

The agent handles all workflow orchestration, error handling, and result reporting.

````

**Line reduction**: 338 lines → ~50 lines (85% reduction)

### Phase 3: Document Pattern

**File**: `docs/agent/command-agent-delegation.md`

**Structure**:
```markdown
# Command-Agent Delegation Pattern

## Overview
[What is delegation, when to use it, benefits]

## When to Delegate

Decision framework:
- Command orchestrates 3+ steps → Consider delegation
- Command handles errors extensively → Good candidate
- Command has complex state management → Good candidate
- Command is simple wrapper → No delegation needed

## Delegation Patterns

### Pattern 1: Simple Delegation (devrun)
[Fast-ci/all-ci example - delegate to specialized tool runner]

### Pattern 2: Workflow Orchestration (gt-branch-submitter, planned-wt-creator)
[Multi-step workflows with error handling]

### Pattern 3: Shared Workflow Documentation
[CI iteration doc pattern - multiple commands share workflow]

## Implementation Guide

1. Create agent file with frontmatter (name, model, tools, color)
2. Define agent workflow steps
3. Implement error handling in agent
4. Update command to delegation-only
5. Add to kit registry if bundled

## Agent Specifications

### Frontmatter Requirements
```yaml
name: agent-name
description: What this agent does
model: haiku | sonnet | opus
color: blue | green | red | cyan
tools: Read, Bash, Task, etc.
````

### Model Selection

- haiku: Fast, cost-efficient (CI tools, workflow orchestration)
- sonnet: Balance (complex analysis)
- opus: Rare (highly complex reasoning)

## Examples from Codebase

### Example 1: /fast-ci → devrun

[Show delegation pattern]

### Example 2: /gt:submit-branch → gt-branch-submitter

[Show workflow orchestration]

### Example 3: /erk:create-planned-wt → planned-wt-creator

[Show new pattern]

## Anti-Patterns

❌ **Don't**: Run tools directly via Bash when agent exists
❌ **Don't**: Embed orchestration in command files
❌ **Don't**: Duplicate error handling across commands
❌ **Don't**: Mix delegation and inline logic

✅ **Do**: Delegate completely to agent
✅ **Do**: Keep commands minimal (<50 lines)
✅ **Do**: Let agent handle errors
✅ **Do**: Document agent capabilities in registry

## Agent Discovery

Finding available agents:

1. Check kit registry: `.agent/kits/kit-registry.md`
2. Browse `.claude/agents/` directory
3. Check AGENTS.md checklist

## Quality Standards

Commands:

- <50 lines total
- Clear prerequisites section
- Single Task tool invocation
- Reference agent for details

Agents:

- Comprehensive error handling
- Self-contained workflow
- Clear step-by-step structure
- Best practices section

````

### Phase 4: Update Navigation

**File**: `docs/agent/guide.md`

Add entry in "Available Documentation" section:
```markdown
- [Command-Agent Delegation](command-agent-delegation.md) - Patterns for delegating workflows to agents
````

**File**: `AGENTS.md`

Add to "BEFORE WRITING CODE" checklist table:

```markdown
| Creating command that orchestrates workflow | → [Command-Agent Delegation](docs/agent/command-agent-delegation.md) - When/how to delegate |
```

## Session Discoveries

### Discovery Journey

The exploration used a systematic approach:

1. **Found command examples** via `Glob` for `.claude/commands/*.md`
   - Discovered `/fast-ci` and `/all-ci` as delegation examples
   - Both use identical pattern: Task tool → devrun agent

2. **Mapped documentation structure** via `Glob` for `docs/agent/*.md`
   - Found 8 existing pattern docs (testing, hooks, kit-cli-commands, etc.)
   - Identified `guide.md` as navigation hub
   - Confirmed `docs/agent/` as location for pattern documentation

3. **Analyzed kit system** via `.agent/kits/` exploration
   - Found 6 installed kits with registry entries
   - Learned kit structure: commands + agents + registry
   - Confirmed usage pattern documentation in registry entries

4. **Read delegation examples** to extract patterns
   - `/fast-ci`: Delegates to devrun, references shared doc (`ci-iteration.md`)
   - Shared workflow doc pattern: Multiple commands reference single workflow guide
   - Explicit reminders: "NEVER run pytest/pyright directly via Bash"

### Architectural Insights

**Command-Agent Separation of Concerns**:

- **Command**: Entry point, prerequisites, high-level "what"
- **Agent**: Implementation, orchestration, error handling, "how"
- **Shared docs**: Workflow details when multiple commands share logic

**Progressive Disclosure Model** (from testing.md):

- Checklist in AGENTS.md → Quick reference
- Detailed docs in docs/agent/ → Complete patterns
- Navigation via guide.md → Discoverability

**Kit Registry System Design**:

- Registry entries = "advertisement" of capabilities
- Commands stored in kit (`.agent/kits/[kit]/commands/`)
- Agents can be in kit OR `.claude/agents/` (project-specific)
- Registry tells users HOW to invoke: "Use Task tool with subagent_type='X'"

### Domain Knowledge

**Naming Conventions** (from AGENTS.md checklist):

- Commands: `kebab-case` (e.g., `/erk:create-planned-wt`)
- Agents: `kebab-case` with pattern `{product}-{noun}-{verb}` (e.g., `gt-branch-submitter`)
  - Alternative patterns: `{noun}-{verb}` (e.g., `worktree-planner`)
  - Must be unique across kit + project agents

**Model Selection Philosophy**:

- Haiku: Cost-efficient for orchestration and tool invocation
  - Used by `gt-branch-submitter` (confirmed in user request)
  - Suitable for `planned-wt-creator` (similar workflow orchestration)
- Sonnet: Balance for analysis-heavy tasks
- Opus: Reserved for highly complex reasoning

**Documentation Audience Split**:

- `docs/agent/` → AI assistants (patterns, rules, quick reference)
- `docs/writing/` → Humans (guides, philosophy, context)
- Package READMEs → Package-specific implementation details

### Technical Context

**Task Tool Invocation Pattern**:

```python
Task(
    subagent_type="agent-name",  # Must match agent's "name" in frontmatter
    description="Brief task description",  # Shown in UI
    prompt="Detailed instructions for agent"  # Agent receives this
)
```

**Agent Frontmatter Requirements**:

```yaml
name: agent-name # Used in Task subagent_type
description: One-line summary # Shown in kit registry
model: haiku # Model selection
color: blue # UI color coding
tools: Read, Bash, Task # Available tools
```

**Command Frontmatter**:

```yaml
description: One-line summary # Shown in command list
argument-hint: <arg> # Optional, for commands with args
```

**Reference Pattern** (from ci-iteration.md):

- Commands reference shared docs with `@` syntax
- Example: `@.claude/docs/ci-iteration.md` in command body
- Shared docs live in `.claude/docs/` (project-specific workflows)

### Testing Insights

No explicit test requirements found for commands or agents. Pattern seems to be:

- Commands are thin wrappers (minimal logic to test)
- Agents are invoked via Task tool (integration-level testing)
- Kit CLI tools (like `erk create`) have their own tests

## Success Criteria

✅ `/erk:create-planned-wt` command is <50 lines (vs current 338 lines)
✅ `planned-wt-creator` agent handles all orchestration and error formatting
✅ `docs/agent/command-agent-delegation.md` provides clear delegation guidance
✅ Pattern is discoverable via AGENTS.md checklist
✅ Pattern is navigable via docs/agent/guide.md
✅ New pattern follows existing conventions (progressive disclosure, kebab-case, kit registry format)

## Failed Attempts

During the exploration session, there were no failed attempts - the research was systematic and successful in finding all relevant patterns and documentation.

However, the session did reveal **potential pitfalls to avoid**:

1. **Don't mix locations**: Commands in `.claude/commands/` vs `.agent/kits/[kit]/commands/`
   - Current `/erk:create-planned-wt` is in `.claude/commands/erk/`
   - Should likely stay there (project-specific, not bundled kit artifact)
   - Agent `planned-wt-creator` should go in `.claude/agents/erk/` to match

2. **Don't skip error handling**: Both examined delegation patterns emphasize complete error handling in agents
   - devrun: Specialized parsing of tool output
   - gt-branch-submitter: Comprehensive error formatting with context-aware guidance
   - planned-wt-creator must do the same

3. **Don't forget navigation**: Documentation is only useful if discoverable
   - Must update guide.md (navigation hub)
   - Must update AGENTS.md (checklist quick reference)
   - Progressive disclosure: checklist → docs → implementation

## Next Steps

After implementation:

1. Review enhanced plan for completeness
2. Begin Phase 1: Create `planned-wt-creator` agent
3. Test agent workflow with existing plan files
4. Continue with Phases 2-4 (update command, document pattern, update navigation)
5. Validate that pattern is discoverable and usable by future developers
