---
description: Extract plan from conversation, enhance using session log discoveries, and create GitHub issue directly
---

# /erk:save-session-enriched-plan

Extracts an implementation plan from the conversation and enhances it with discoveries mined from Claude Code session logs. Creates a GitHub issue directly with the enhanced plan, preserving all computational work from the planning session.

## Usage

```bash
/erk:save-session-enriched-plan
```

## Purpose

This command solves the critical problem where planning sessions lose valuable discoveries when plans are saved. By mining session logs and **filtering to Plan subagent sessions**, we preserve:

- Failed attempts and what didn't work
- API quirks and undocumented behaviors
- Architectural insights about WHY decisions were made
- Performance bottlenecks discovered
- Complex reasoning paths explored

## How It Works

1. **Locates session logs** for the current Claude Code project
2. **Mines discoveries** from:
   - Main session log
   - Plan subagent sessions only (filters out Explore, devrun, etc.)
   - Falls back to main session only if no Plan subagents found
3. **Extracts the plan** from the conversation
4. **Enhances the plan** with mined context
5. **Creates GitHub issue** with enhanced plan content and `erk-plan` label

### Streaming Analysis

The command uses streaming mode by default (`--streaming` flag), which:

- **Chunks large sessions** into batches of ~10 tool sequences
- **Processes incrementally** for better latency perception
- **Maintains completeness** by processing all batches (no early exit)
- **Falls back automatically** to single-pass for small sessions
- **Uses cost-efficient Haiku** model for batch processing

Benefits:

- Shows progress incrementally vs waiting for full analysis
- More memory-efficient with smaller context per inference
- Foundation for future parallel processing enhancements
- No quality loss - processes full XML in smaller chunks

---

## Agent Instructions

You are executing the `/erk:save-session-enriched-plan` command. Follow these steps carefully using ONLY the allowed tools.

### CRITICAL: Tool Restrictions

**ALLOWED TOOLS:**

- `Read` - For reading session logs and files
- `Bash` - For git commands, log operations, and kit CLI commands
- `Task` - ONLY for Step 3 mining delegation with general-purpose subagent
- `AskUserQuestion` - For clarifications

**FORBIDDEN TOOLS:**

- `Edit` - Do NOT modify any existing files
- `Write` - Do NOT write to codebase (only creating GitHub issue)
- `Glob` - Do NOT search the codebase
- `Grep` - Do NOT search the codebase
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
# Using --streaming flag for batched processing
dot-agent run erk save-session-enriched-plan discover --session-id <SESSION_ID> --cwd "$CWD" --streaming
```

This outputs JSON with structure (streaming mode):

```json
{
  "success": true,
  "mode": "streaming",
  "batches": ["<session>...</session>", "<session>...</session>", ...],
  "batch_count": 5,
  "log_path": "/Users/.../.jsonl",
  "session_id": "abc-123",
  "stats": {
    "entries_processed": 37,
    "entries_skipped": 142,
    "token_reduction_pct": "85.8%",
    "original_size": 227612,
    "compressed_size": 32337,
    "planning_agents_found": 2,
    "agent_filter_applied": true
  }
}
```

Or single-pass mode (if XML is small enough):

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
    "compressed_size": 32337,
    "planning_agents_found": 2,
    "agent_filter_applied": true
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
4. Then run /erk:save-session-enriched-plan
```

### Step 3: Mine Discoveries Using Haiku Subagent

**Step 3a: Detect Mode**

Check the JSON output from Step 1b to determine processing mode:

- If `"mode": "streaming"` present: Use batched processing (Step 3b)
- Otherwise: Use single-pass processing (Step 3c)

**Step 3b: Batched Processing (Streaming Mode)**

If streaming mode detected:

1. Extract the `batches` array from Step 1b JSON
2. For each batch in the array:
   - Launch Task tool with haiku subagent (parameters below)
   - Insert the current batch XML into the prompt template
   - Collect discoveries from the agent's response
3. After all batches processed, merge discoveries into a single structured report

Merge strategy:

- Combine discoveries by category
- Remove duplicates (same discovery from multiple batches)
- Preserve all unique insights

**Step 3c: Single-Pass Processing (Fallback)**

If single-pass mode (no `"mode"` field or XML is small):

1. Extract `compressed_xml` from Step 1b JSON
2. Launch Task tool once with haiku subagent (parameters below)
3. Use the complete compressed XML in the prompt template

**Subagent Parameters (both modes):**

- `subagent_type`: `"general-purpose"`
- `model`: `"haiku"`
- `description`: `"Mine session log discoveries"`
- `prompt`: Construct prompt from template below, inserting batch or full XML

**Prompt Template:**

````
Analyze this compressed XML from a Claude Code planning session to extract valuable discoveries.

The XML represents tool uses, results, user messages, and assistant reasoning from the session.

<compressed_xml>
{INSERT_COMPRESSED_XML_HERE}
</compressed_xml>

Your task: Semantically analyze this XML to identify discoveries organized into these categories.

**DO NOT use regex patterns.** Read and understand the XML as a narrative of the planning session.

## Discovery Categories

### Discovery Journey
- What search patterns were used to explore the codebase?
- What files were examined and in what order?
- How did the exploration sequence reveal the solution?

### Failed Attempts
- What approaches were tried that didn't work, and WHY?
- What errors provided valuable learning?
- What solutions were rejected, with their reasoning?

### API/Tool Quirks
- What undocumented behaviors were discovered?
- What edge cases were found through experimentation?
- What workarounds became necessary?

### Architectural Insights
- WHY were particular design decisions made?
- What design patterns were found in the codebase?
- What conventions or idioms were learned?

### Performance Issues
- What operations were identified as slow?
- What timeout or resource risks were discovered?
- What memory or efficiency concerns emerged?

### Domain Knowledge
- What business rules were uncovered?
- What non-obvious requirements surfaced?
- What hidden constraints affected the design?

### Technical Context
- What function signatures or APIs were discovered?
- What parameter requirements were learned?
- What return value formats or protocols were understood?

### Testing Insights
- What test patterns were found?
- What coverage gaps were identified?
- What testing challenges were encountered?

## Analysis Guidelines

When analyzing the XML, look for:

**Tool Invocations and Results:**
- What tools were used and for what purpose?
- What file paths or code patterns were explored?
- What commands were executed?

**Errors and Failures:**
- What errors were encountered?
- What approaches were attempted but didn't work?
- Why were certain solutions rejected?

**Assistant Reasoning:**
- What trade-offs were analyzed?
- What performance concerns were raised?
- What architectural decisions were explained?

**User Interactions:**
- What clarifications did the user provide?
- What requirements were revealed through questions?
- What domain knowledge did the user share?

## Output Format

Return a structured report with each category as a section. For each discovery:
- State the discovery clearly
- Explain WHY it matters for implementation
- Connect it to implementation considerations

Example format:

```markdown
## Discovery Journey

- Initial grep for pattern X failed at /old/path
- This revealed that the implementation moved to /new/path with refactored structure
- The refactoring was done for performance reasons (constraint Y)

## Failed Attempts

- Tried reading config at /old/path (FileNotFoundError)
- This revealed config was migrated to /new/path with schema validation added
- Important for implementation: Must use JSON schema validation, not plain JSON

## Architectural Insights

- Project uses pattern Y instead of pattern X due to performance constraint Q
- This was discovered through examining function Z implementation
- Affects implementation: Must follow pattern Y for consistency
````

## Focus Guidelines

Prioritize:

- **Context over facts**: Not just "error occurred" but "why it happened and what it revealed"
- **WHY over WHAT**: Not just "used this pattern" but "why this pattern was chosen"
- **Insights over data**: What was learned, not just what was seen
- **Connections**: How discoveries relate to the implementation plan

Focus on insights that will help during implementation.

````

**After Task completes:**

The agent returns a structured report with discoveries organized by category. Store this output for use in Step 4 composition.

### Step 4: Compose Enhanced Plan

Integrate discoveries from the mining agent (Step 3 output) with the plan (Step 2 output) to compose an enhanced plan.

**Inputs:**
- Plan extracted from conversation (Step 2)
- Discoveries from haiku mining agent (Step 3 structured report)
- Session metadata (Step 1b: stats, session_id)

Use the agent's structured report to enhance the plan - the discoveries are already organized by category.

**Extract Title and Summary:**

- Identify the plan's main objective from the first H1 (`# Title`) or H2 (`## Title`)
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

### Step 5: Validate Repository and Create GitHub Issue

After composing the enhanced plan, create a GitHub issue with the content.

**Step 5a: Validate Repository and GitHub CLI**

Verify we're in a git repository and GitHub CLI is available:

1. Verify git repository using: `git rev-parse --show-toplevel`
2. Verify GitHub CLI is authenticated

**If not in git repository:**

```
❌ Error: Not in a git repository

This command must be run from within a git repository.
```

**If GitHub CLI not available or not authenticated:**

```
❌ Error: GitHub CLI not available or not authenticated

Suggested action:
  1. Install GitHub CLI: https://cli.github.com/
  2. Authenticate with: gh auth login
  3. Verify authentication: gh auth status
```

**Step 5b: Create GitHub Issue**

Create a GitHub issue with the enhanced plan content using the kit CLI command:

```bash
issue_url=$(echo "$enhanced_plan_content" | dot-agent kit-command erk create-enriched-plan-issue-from-context)
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create GitHub issue" >&2
    exit 1
fi
```

The kit CLI command:
- Reads enhanced plan content from stdin
- Extracts title from plan for issue title
- Creates issue with `erk-plan` label
- Returns issue URL

**Extract issue number from URL:**

Parse the issue number from the returned URL (e.g., `https://github.com/org/repo/issues/123` → `123`)

**If issue creation fails:**

```
❌ Error: Failed to create GitHub issue

Details: [specific error from kit CLI command]

Suggested action:
  1. Verify GitHub CLI (gh) is installed and authenticated
  2. Check repository has issues enabled
  3. Verify network connectivity
  4. Check gh auth status
```

### Step 6: Output Summary

After creating the GitHub issue, output a summary based on the discoveries you mined and composed:

Calculate:

- Total discoveries: Count discoveries you identified in Step 3
- Number of discovery categories: Count categories from Step 3
- Failed attempts: Count failed attempts you documented
- Token reduction: From Step 1b stats

Output:

```
✅ GitHub issue created: #<number>
   <issue-url>

Summary:
- Discoveries mined: [total count]
- Discovery categories: [category count]
- Failed attempts documented: [failed attempts count]
- Token reduction: [from Step 1b stats, e.g., "85.8%"]

Next steps:
1. Review the issue if needed: gh issue view <number> --web
2. Implement: erk implement #<number>

---

{"issue_number": <number>, "issue_url": "<url>", "status": "created"}
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

**GitHub CLI not available:**

```
❌ Error: GitHub CLI not available or not authenticated

Suggested action:
  1. Install GitHub CLI: https://cli.github.com/
  2. Authenticate with: gh auth login
  3. Verify authentication: gh auth status
```

**GitHub issue creation failed:**

```
❌ Error: Failed to create GitHub issue

Details: [specific error from kit CLI command]

Suggested action:
  1. Verify GitHub CLI (gh) is installed and authenticated
  2. Check repository has issues enabled
  3. Verify network connectivity
  4. Check gh auth status

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
````
