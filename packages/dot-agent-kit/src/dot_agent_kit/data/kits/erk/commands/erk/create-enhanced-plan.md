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
5. **Saves enhanced plan** to repository root

---

## Agent Instructions

You are executing the `/erk:create-enhanced-plan` command. Follow these steps carefully using ONLY the allowed tools.

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
dot-agent run erk create-enhanced-plan discover --session-id <SESSION_ID> --cwd "$CWD"
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
  "context": {"cwd": "/path"}
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
4. Then run /erk:create-enhanced-plan
```

### Step 3: Mine Discoveries from Compressed XML

**Use the compressed_xml field from Step 1b JSON output.**

The format uses coarse-grained tags:

```xml
<session>
  <meta branch="..." />
  <user>User message text</user>
  <assistant>Assistant reasoning</assistant>
  <tool_use name="ToolName" id="toolu_123">
    <param name="param1">value</param>
  </tool_use>
  <tool_result tool="toolu_123">
    Full tool result content preserved verbatim...
  </tool_result>
</session>
```

Extract discoveries using simple regex patterns:

```python
# Extract tool uses
tool_uses = re.findall(r'<tool_use name="([^"]+)" id="([^"]+)">(.*?)</tool_use>', xml, re.DOTALL)

# Extract tool results (preserve full verbosity)
tool_results = re.findall(r'<tool_result tool="([^"]+)">(.*?)</tool_result>', xml, re.DOTALL)

# Extract user messages
user_messages = re.findall(r'<user>(.*?)</user>', xml, re.DOTALL)

# Extract assistant reasoning
assistant_text = re.findall(r'<assistant>(.*?)</assistant>', xml, re.DOTALL)
```

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

### Step 4: Structure Discoveries as JSON

After mining discoveries from the compressed XML in Step 3, structure them as JSON for the assemble phase:

```json
{
  "session_id": "<session-id-from-step-1a>",
  "categories": {
    "API Discoveries": [
      "Project directories use escaped paths: /Users/foo → -Users-foo",
      "Session logs stored in JSONL format"
    ],
    "Architecture": [
      "Two-phase pattern enables clean separation",
      "JSON output eliminates temp file issues"
    ]
  },
  "failed_attempts": [
    {
      "name": "Simple permission add",
      "reason": "Requires manual config, not automatic"
    }
  ],
  "raw_discoveries": [
    "Discovered: Kit CLI commands bypass all permissions",
    "Found: Two-phase pattern in submit_branch.py",
    "Learned: 85.8% token reduction with preprocessing"
  ]
}
```

### Step 5: Assemble Enhanced Plan

**Step 5a: Run Assemble Phase**

Use the kit CLI command to build the enhanced plan:

```bash
# Create temp files for plan and discoveries
echo "$PLAN_CONTENT" > /tmp/plan-temp.md
echo "$DISCOVERIES_JSON" > /tmp/discoveries-temp.json

# Run assemble phase
dot-agent run erk create-enhanced-plan assemble /tmp/plan-temp.md /tmp/discoveries-temp.json
```

This outputs JSON with structure:

```json
{
  "success": true,
  "content": "---\nenriched_by_create_enhanced_plan: true\n...",
  "filename": "enhanced-plan.md",
  "stats": {
    "discovery_count": 18,
    "categories": 5,
    "failed_attempts": 2
  }
}
```

**Step 5b: Write Enhanced Plan to Repository Root**

Extract the `content` and `filename` fields from the JSON output and write to repo root:

```python
# Determine repo root
repo_root = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"],
    capture_output=True,
    text=True,
    check=True
).stdout.strip()

# Use filename from assemble output
filename = assemble_result["filename"]

# Save directly to repo root (NOT to .plan/ folder)
plan_path = Path(repo_root) / filename

# Write enhanced plan content
plan_path.write_text(assemble_result["content"], encoding="utf-8")
```

### Step 6: Output Summary

After writing the enhanced plan, output:

```
✅ Enhanced plan saved to: [filename]

Summary:
- Discoveries mined: [count from stats]
- Discovery categories: [count from stats]
- Failed attempts documented: [count from stats]
- Token reduction: [from Step 1b stats]

Next steps:
1. Review the enhanced plan
2. Create worktree: /erk:create-planned-wt [plan-file]
3. Switch to worktree and implement
```

### Step 7: Handle Errors

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
