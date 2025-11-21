---
description: Extract plan from conversation and enhance using session log discoveries
---

# /erk:enhance-and-save-plan

Extracts an implementation plan from the conversation and enhances it with discoveries mined from Claude Code session logs. This preserves all computational work from the planning session without triggering any implementation behavior.

## Usage

```bash
/erk:enhance-and-save-plan
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
5. **Saves enhanced plan** to repository root

---

## Agent Instructions

You are executing the `/erk:enhance-and-save-plan` command. Follow these steps carefully using ONLY the allowed tools.

### CRITICAL: Tool Restrictions

**ALLOWED TOOLS:**

- `Read` - For reading session logs and files
- `Write` - ONLY for writing to repository root
- `Bash` - ONLY for log operations in `~/.claude/projects/`
- `AskUserQuestion` - For clarifications

**FORBIDDEN TOOLS:**

- `Edit` - Do NOT modify any existing files
- `Glob` - Do NOT search the codebase
- `Grep` - Do NOT search the codebase
- `Task` - Do NOT launch subagents
- Any tool not explicitly listed as allowed

**CRITICAL:** If you use any forbidden tool, STOP immediately.

### Step 1: Discover and Preprocess Session Logs

**Step 1a: Extract Session ID from Context**

Search the conversation for the session ID injected by the session-id-injector-hook:

1. Look for system-reminder or reminder messages containing "SESSION_CONTEXT:"
2. Extract the session ID from format: `SESSION_CONTEXT: session_id={uuid}`
3. Store the session ID for use in the discover phase

Example pattern to match:

```
SESSION_CONTEXT: session_id=abc-123-def-456
```

If session ID not found in context:

```
⚠️ Warning: Session ID not found in conversation context

The session-id-injector-hook may not be installed or running.
Cannot proceed without session ID.
```

**Step 1b: Run Discovery Phase**

Use the kit CLI command to discover and preprocess session logs (NO permission prompts):

```bash
# Get current working directory
CWD=$(pwd)

# Run discover phase with session ID from Step 1a
dot-agent run erk enhance-and-save-plan discover --session-id <SESSION_ID> --cwd "$CWD"
```

This outputs JSON with structure:

```json
{
  "success": true,
  "compressed_xml": "<session>...</session>",
  "log_path": "/Users/.../.jsonl",
  "session_id": "abc-123",
  "stats": {
    "entries_processed": 37,
    "entries_skipped": 142,
    "token_reduction_pct": "85.8%",
    "original_size": 227612,
    "compressed_size": 32337
  }
}
```

**If error occurs:**

```json
{
  "success": false,
  "error": "Project directory not found",
  "help": "Could not find Claude Code project for /path",
  "context": { "cwd": "/path" }
}
```

Parse the JSON output and extract the `compressed_xml` field for mining in Step 3.

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
4. Then run /erk:enhance-and-save-plan
```

### Step 3: Mine Discoveries Semantically from Compressed XML

**Use the compressed_xml field from Step 1b JSON output.**

The compressed XML contains the session's tool uses, results, user messages, and assistant reasoning. Your task is to **read and understand** this content semantically to identify valuable discoveries.

**DO NOT use regex patterns.** Instead, analyze the XML as a narrative of the planning session, identifying patterns through understanding rather than mechanical extraction.

#### How to Analyze

Read through the compressed XML and look for:

**Tool Invocations and Results:**

- What tools were used and for what purpose?
- What were the assistant searching for?
- What file paths or code patterns were explored?
- What commands were executed?

**Errors and Failures:**

- What errors were encountered?
- What approaches were attempted but didn't work?
- Why were certain solutions rejected?
- What provided the context for these failures?

**Assistant Reasoning:**

- What trade-offs were analyzed?
- What performance concerns were raised?
- What architectural decisions were explained?
- What insights emerged from the reasoning?

**User Interactions:**

- What clarifications did the user provide?
- What requirements were revealed through questions?
- What domain knowledge did the user share?

#### Discoveries to Extract

Organize your findings into these categories:

**Discovery Journey:**

- What search patterns were used to explore the codebase?
- What files were examined and in what order?
- How did the exploration sequence reveal the solution?

**Failed Attempts:**

- What approaches were tried that didn't work, and WHY?
- What errors provided valuable learning?
- What solutions were rejected, with their reasoning?

**API/Tool Quirks:**

- What undocumented behaviors were discovered?
- What edge cases were found through experimentation?
- What workarounds became necessary?

**Architectural Insights:**

- WHY were particular design decisions made?
- What design patterns were found in the codebase?
- What conventions or idioms were learned?

**Performance Issues:**

- What operations were identified as slow?
- What timeout or resource risks were discovered?
- What memory or efficiency concerns emerged?

**Domain Knowledge:**

- What business rules were uncovered?
- What non-obvious requirements surfaced?
- What hidden constraints affected the design?

**Technical Context:**

- What function signatures or APIs were discovered?
- What parameter requirements were learned?
- What return value formats or protocols were understood?

**Testing Insights:**

- What test patterns were found?
- What coverage gaps were identified?
- What testing challenges were encountered?

#### Focus on Context and WHY

When extracting discoveries, prioritize:

- **Context over facts**: Not just "error occurred" but "why it happened and what it revealed"
- **WHY over WHAT**: Not just "used this pattern" but "why this pattern was chosen"
- **Insights over data**: What was learned, not just what was seen
- **Connections**: How discoveries relate to the implementation plan

### Step 4: Compose and Save Enhanced Plan

**Step 4a: Compose Enhanced Plan**

Use your semantic understanding from Step 3 to compose an enhanced plan. You already have the discoveries organized by category from Step 3 - directly integrate the plan (Step 2) with discoveries (Step 3).

**Generate Appropriate Filename:**

Read the plan objectives and scope, then create a descriptive filename:

- Use kebab-case format
- Maximum 30 characters (git worktree compatibility)
- Prioritize clarity over mechanical rules
- End with `-plan.md` suffix
- Examples: `auth-refactor-plan.md`, `api-migration-plan.md`, `test-framework-plan.md`

**Extract Title and Summary:**

- Identify the plan's main objective
- Synthesize an executive summary from goals and approach
- Keep summary concise (2-3 sentences)

**Compose the Enhanced Plan:**

Structure the document with these suggested sections (adapt based on content):

1. **Title and Frontmatter**
   - Include `erk_plan: true` in YAML frontmatter
   - Add session_id from discoveries
   - Include generation timestamp

2. **Executive Summary**
   - Synthesize from plan objectives
   - Highlight key approach
   - Note critical discoveries that affect implementation

3. **Critical Context** (from discoveries)
   - API quirks and undocumented behaviors
   - Architectural insights that guide implementation
   - Performance considerations
   - Technical context (signatures, protocols)

4. **Implementation Plan** (from original plan)
   - Preserve the original plan structure
   - May add inline notes about relevant discoveries

5. **Session Discoveries** (organized by relevance)
   - Discovery journey (how solution was found)
   - Domain knowledge uncovered
   - Testing insights

6. **Failed Attempts** (what didn't work and why)
   - Document approaches that were tried
   - Explain why they failed
   - Note what was learned from each failure

**Composition Guidelines:**

- **Adapt structure to content**: Reorder, combine, or omit sections as appropriate
- **Write naturally**: Format discoveries as insights, not bullet dumps
- **Connect discoveries to plan**: Show how discoveries affect implementation decisions
- **Emphasize WHY**: Explain reasoning behind decisions
- **Progressive disclosure**: Summary → Critical info → Details → Raw data

**Step 4b: Write Enhanced Plan to Repository Root**

After composing the enhanced plan content and generating the filename, write to repo root:

Use the Write tool to save your composed enhanced plan:

1. Determine the repository root using git
2. Use the filename you generated in Step 4a
3. Write the enhanced plan content you composed

Example:

```python
from pathlib import Path
import subprocess

# Get repo root
repo_root = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"],
    capture_output=True,
    text=True,
    check=True
).stdout.strip()

# Use your generated filename
filename = "your-generated-filename.md"  # From Step 5b

# Construct path (repo root, NOT .plan/ folder)
plan_path = Path(repo_root) / filename

# Write your composed content
plan_path.write_text(enhanced_plan_content, encoding="utf-8")
```

### Step 5: Output Summary

After writing the enhanced plan, output a summary based on the discoveries you mined and composed:

Calculate:

- Total discoveries: Count discoveries you identified in Step 3
- Number of discovery categories: Count categories from Step 3
- Failed attempts: Count failed attempts you documented
- Token reduction: From Step 1b stats

Output:

```
✅ Enhanced plan saved to: [filename you generated]

Summary:
- Discoveries mined: [total count]
- Discovery categories: [category count]
- Failed attempts documented: [failed attempts count]
- Token reduction: [from Step 1b stats, e.g., "85.8%"]

Next steps:
1. Review the enhanced plan
2. Create worktree: /erk:create-planned-wt [filename]
3. Switch to worktree and implement
```

### Step 6: Handle Errors

**Session ID not found:**

```
❌ Error: Session ID not found in conversation context

The session-id-injector-hook may not be installed.
Cannot proceed without session ID.
```

**Project directory not found:**

```
❌ Error: Claude Code project not found

The discover phase returned: "Project directory not found"

Verify:
1. You're in a Claude Code project directory
2. The project has session logs in ~/.claude/projects/
```

**Session log not found:**

```
❌ Error: Session log not found

The discover phase returned: "Session log not found"

Possible reasons:
1. Session ID is incorrect
2. Session logs have been cleaned up
3. Session was created in a different project
```

**File already exists:**

```
File [name] already exists in repository root.

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
