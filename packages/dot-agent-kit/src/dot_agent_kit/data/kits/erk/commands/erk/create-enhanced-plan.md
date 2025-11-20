---
description: Extract plan from conversation and enhance using session log discoveries
---

# /erk:create-enhanced-plan

Extracts an implementation plan from the conversation and enhances it with discoveries mined from Claude Code session logs. This preserves all computational work from the planning session without triggering any implementation behavior.

## Usage

```bash
/erk:create-enhanced-plan
```

## Purpose

This command solves the critical problem where planning sessions lose valuable discoveries when plans are saved. By mining session logs, we preserve:

- Failed attempts and what didn't work
- API quirks and undocumented behaviors
- Architectural insights about WHY decisions were made
- Performance bottlenecks discovered
- Complex reasoning paths explored

## How It Works

1. **Locates session logs** for the current Claude Code project
2. **Mines discoveries** from tool invocations and assistant reasoning
3. **Extracts the plan** from the conversation
4. **Enhances the plan** with mined context
5. **Saves enhanced plan** to `.plan/` folder

---

## Agent Instructions

You are executing the `/erk:create-enhanced-plan` command. Follow these steps carefully using ONLY the allowed tools.

### CRITICAL: Tool Restrictions

**ALLOWED TOOLS:**

- `Read` - For reading session logs and files
- `Write` - ONLY for writing to `.plan/` folder
- `Bash` - ONLY for log operations in `~/.claude/projects/`
- `AskUserQuestion` - For clarifications

**FORBIDDEN TOOLS:**

- `Edit` - Do NOT modify any existing files
- `Glob` - Do NOT search the codebase
- `Grep` - Do NOT search the codebase
- `Task` - Do NOT launch subagents
- Any tool not explicitly listed as allowed

**CRITICAL:** If you use any forbidden tool, STOP immediately.

### Step 1: Locate Session Logs

Find the Claude Code session logs for this project:

```bash
# Get current directory to determine project
pwd

# List available projects
ls ~/.claude/projects/

# Find the current project's logs
# Project hash is typically derived from workspace path
ls ~/.claude/projects/<project-hash>/*.jsonl
```

Look for:

- Main session log (file NOT starting with "agent-")
- Agent logs (files starting with "agent-")

If logs not found or inaccessible:

```
⚠️ Warning: Session logs not accessible

Falling back to conversation-only extraction.
This will miss discoveries made during planning research.
```

### Step 2: Extract Plan from Conversation

Search the conversation for the implementation plan:

1. Look for `ExitPlanMode` tool results containing the plan
2. Look for sections like "## Implementation Plan" or "### Implementation Steps"
3. Look for numbered lists of implementation tasks

Extract:

- Objective/goal
- Implementation steps/phases
- Success criteria
- Testing requirements

If no plan found:

```
❌ Error: No implementation plan found in conversation

Please create a plan first:
1. Enter Plan mode
2. Create your implementation plan
3. Exit Plan mode
4. Then run /erk:create-enhanced-plan
```

### Step 3: Mine Session Logs for Discoveries

Parse each log file line by line (JSONL format). Each line is a separate JSON object.

#### What to Extract

From `tool_use` entries:

- Tool name and parameters
- What was being searched for
- File paths explored
- Commands executed

From `tool_result` entries:

- Errors encountered
- File contents discovered (key snippets only)
- Command outputs
- Search results

From assistant text blocks:

- Reasoning about approaches
- Trade-off analysis
- Rejection explanations
- Performance observations

#### Categories to Populate

**Discovery Journey:**

- Search patterns used
- Files examined
- Exploration sequence

**Failed Attempts:**

- Errors encountered
- Approaches that didn't work
- Rejected solutions

**API/Tool Quirks:**

- Undocumented behaviors
- Edge cases discovered
- Workarounds needed

**Architectural Insights:**

- WHY decisions were made
- Design patterns found
- Codebase conventions

**Performance Issues:**

- Slow operations
- Timeout risks
- Memory concerns

**Domain Knowledge:**

- Business rules discovered
- Non-obvious requirements
- Hidden constraints

**Technical Context:**

- Function signatures
- Parameter requirements
- Return value formats

**Testing Insights:**

- Test patterns found
- Coverage gaps
- Testing challenges

### Step 4: Create Enhanced Plan Structure

Build the enhanced plan with this structure:

```markdown
---
enriched_by_create_enhanced_plan: true
session_id: <from-logs>
discovery_count: <number>
timestamp: <ISO-8601>
---

# [Plan Title] - Enhanced Implementation Guide

## Executive Summary

[1-2 paragraphs summarizing the goal and approach]

## Critical Context from Planning

### What We Learned

#### [Category 1 - e.g., API Discoveries]

- [Key insight 1]
- [Key insight 2]

#### [Category 2 - e.g., Architecture]

- [Key insight 1]
- [Key insight 2]

### What Didn't Work

#### Failed Approaches Discovered

- **[Approach 1]**: [Why it failed]
- **[Approach 2]**: [Why it failed]

### Raw Discoveries Log

[Chronological list of significant discoveries]

- Discovered: [Finding]
- Confirmed: [Validation]
- Learned: [Insight]
- Found: [Pattern]

## Implementation Plan

### Objective

[Original objective from plan]

### Implementation Steps

#### Phase 1: [Name]

1. **[Step name]**
   [CRITICAL: Warning if applicable]
   - Success: [Criteria]
   - On failure: [Recovery]

   Related Context:
   - [Link to relevant discovery]
   - [Why this approach was chosen]

2. **[Step name]**
   [Details]

   Related Context:
   - [Link to relevant discovery]

[Continue for all phases...]

### Testing

[Testing requirements from original plan plus insights from logs]

## Progress Tracking

**Current Status:** Planning complete, ready for implementation

**Last Updated:** [Date]

### Implementation Progress

- [ ] Step 1: [Name from plan]
- [ ] Step 2: [Name from plan]
      [Continue for all steps...]

### Overall Progress

**Steps Completed:** 0 / [Total]

## Appendices

### A. Commands Run During Planning

[List of significant commands from logs]

### B. Code Examined

[List of files/functions examined with brief notes]

### C. Error Scenarios

[Errors encountered and how to handle them]

### D. Decision Log

[Key decisions made during planning and why]

### E. Key Discoveries Not to Lose

[Critical insights that must not be forgotten]
```

### Step 5: Apply Context Linking

Link discoveries to implementation steps:

1. **Inline warnings** for critical issues:

   ```
   [CRITICAL: Check exists() before resolve() - causes error otherwise]
   ```

2. **Related Context subsections** after each step:

   ```
   Related Context:
   - Session logs stored in JSONL format, one JSON per line
   - Project hash derived from workspace path
   - Must parse incrementally to avoid memory issues
   ```

3. **Cross-references** to appendices:
   ```
   (See Appendix A for full command list)
   ```

### Step 6: Save Enhanced Plan

Generate filename and save:

```python
# Determine repo root
repo_root = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"],
    capture_output=True,
    text=True,
    check=True
).stdout.strip()

# Generate filename (max 30 chars base for worktree compatibility)
# Example: "session-log-mining-enhanced-plan.md"
filename = f"{descriptive_name}-enhanced-plan.md"

# Save to .plan/ folder
plan_path = Path(repo_root) / ".plan" / filename

# Create .plan/ if needed
plan_path.parent.mkdir(exist_ok=True)

# Write enhanced plan
plan_path.write_text(enhanced_plan_content, encoding="utf-8")
```

Output:

```
✅ Enhanced plan saved to: .plan/[filename]

Summary:
- Discoveries mined: [count]
- Implementation steps: [count]
- Context links added: [count]

Next steps:
1. Run: /erk:create-planned-wt
2. Switch to new worktree
3. Run: /erk:implement-plan
```

### Step 7: Handle Errors

**No logs found:**

- Continue with conversation-only extraction
- Warn about missing discoveries

**Large logs (>25000 tokens):**

- Process incrementally line by line
- Extract key snippets only, not full contents

**Corrupted log entries:**

- Skip malformed JSON lines
- Continue with remaining entries

**File already exists:**

```
File .plan/[name] already exists.

Options:
1. Use different name
2. Overwrite existing
3. Cancel operation
```

## Example Mining Results

When mining logs, you might find:

```json
// Tool use that failed
{
  "type": "tool_use",
  "name": "Read",
  "input": {"file_path": "/nonexistent/path"}
}

// Result showing error
{
  "type": "tool_result",
  "error": "FileNotFoundError"
}

// Assistant reasoning about failure
{
  "type": "text",
  "text": "The file doesn't exist at that path. Let me search for it..."
}
```

This becomes:

```markdown
### Failed Attempts

- **Reading config at /nonexistent/path**: File not found, searched elsewhere
```

## Important Notes

- **No implementation**: This command ONLY reads and writes plans
- **Log mining focus**: Prioritize discoveries from logs over conversation
- **Key snippets only**: Don't include full file contents from logs
- **Tool boundaries**: Strictly enforce allowed/forbidden tools
- **Progressive disclosure**: Summary → Details → Raw data
