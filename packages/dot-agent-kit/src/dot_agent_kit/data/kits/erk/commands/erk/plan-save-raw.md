---
description: Extract plan from Claude session and create GitHub issue (no enrichment)
---

# /erk:plan-save-raw

Extracts the latest implementation plan from Claude session files and creates a GitHub issue with the raw plan content. This command uses an **agent-based architecture** with structural enforcement instead of text warnings.

## Usage

```bash
/erk:plan-save-raw
```

## Purpose

This command provides a **fast path** for creating GitHub issues from session plans. It:

- Extracts the latest `ExitPlanMode` plan from Claude session files (deterministic)
- Creates a GitHub issue with `erk-plan` label
- Preserves plan content exactly as found (no enrichment)
- Outputs JSON metadata with issue URL and number

**What it does NOT do:**

- ❌ No conversation context searching
- ❌ No plan enhancement or enrichment
- ❌ No interactive clarifying questions
- ❌ No semantic understanding extraction
- ❌ No code implementation (structurally impossible)

**Fast Path vs Enriched Path:**

- **save-raw-plan** (this command): Session files → Raw plan → GitHub issue (fast, deterministic)
- **save-plan**: Conversation context → Enriched plan → GitHub issue (interactive, comprehensive)

## Architecture

This command uses the same **plan-extractor agent** but in `raw` mode:

```
/erk:plan-save-raw (orchestrator)
  ↓
  ├─→ Validate prerequisites (git repo, gh auth)
  ├─→ Determine session ID (from environment or current session)
  ├─→ Launch plan-extractor agent in RAW mode (Task tool)
  │     ↓
  │     Agent reads session JSONL files
  │     Agent extracts ExitPlanMode content
  │     Agent returns markdown: # Plan: ... (raw mode - minimal enrichment)
  │     (Agent has NO Edit/Write tools - structurally safe)
  ├─→ Save plan to temp file
  ├─→ Call kit CLI: dot-agent run erk create-enriched-plan-from-context --plan-file
  │     ↓
  │     Kit CLI creates GitHub issue
  └─→ Display results (issue URL + copy-pastable commands)
```

**Key Innovation:** Same structural safety as save-plan - agent physically cannot edit files.

## How It Works

1. **Determine session ID** - Get current session or use SESSION_CONTEXT
2. **Launch agent** - Call plan-extractor in raw mode
3. **Extract plan** - Agent reads session JSONL for ExitPlanMode
4. **Create issue** - Use kit CLI to create GitHub issue
5. **Display results** - Show issue URL and commands

---

## Command Instructions

You are executing the `/erk:plan-save-raw` command. Follow these steps carefully:

### Step 1: Validate Prerequisites

Check that prerequisites are met:

```bash
# Verify we're in a git repository
git rev-parse --is-inside-work-tree

# Verify GitHub CLI is authenticated
gh auth status
```

**Error handling:**

If `git rev-parse` fails:

```
❌ Error: Not in a git repository

This command must be run from within a git repository.
```

If `gh auth status` fails:

```
❌ Error: GitHub CLI not authenticated

Run: gh auth login
```

### Step 2: Determine Session ID

The session ID is needed to locate session files.

**Method 1: Check SESSION_CONTEXT environment**

Look for session ID in context:

```bash
# SESSION_CONTEXT is set by hooks like UserPromptSubmit hook
# Format: session_id=71451478-0883-40d1-a8d4-6c36f219c719
echo "$SESSION_CONTEXT"
```

If found, extract the session ID:

```bash
session_id=$(echo "$SESSION_CONTEXT" | grep -oP 'session_id=\K[0-9a-f-]+')
```

**Method 2: Use current session (fallback)**

If no SESSION_CONTEXT available, use a kit CLI command to determine current session:

```bash
# This command finds the most recent session directory
session_id=$(ls -t ~/.claude/projects/ | head -1)
```

**Validation:**

Ensure session ID is a valid UUID format (8-4-4-4-12 hex digits).

**Error handling:**

If no session ID found:

```
❌ Error: Could not determine session ID

Ensure you're running this command within an active Claude session.

Session files are located in: ~/.claude/projects/
```

### Step 3: Launch Plan-Extractor Agent (Raw Mode)

Use the Task tool to launch the agent in raw mode:

**Task tool invocation:**

```json
{
  "subagent_type": "plan-extractor",
  "description": "Extract raw plan from session",
  "prompt": "Extract the implementation plan from session files WITHOUT enrichment.\n\nInput:\n- Mode: raw\n- Session ID: [session_id]\n\nFind the session JSONL files at ~/.claude/projects/[session_id]/data/*.jsonl and extract the latest ExitPlanMode tool use content.\n\nExpected output: Markdown with # Plan: title and minimal enrichment details (raw mode).",
  "model": "haiku"
}
```

**What the agent does:**

1. Reads session JSONL files from `~/.claude/projects/<session_id>/data/*.jsonl`
2. Finds latest ExitPlanMode tool use
3. Extracts plan content
4. Returns markdown (no enrichment, no questions)

**Agent tool restrictions (same as enriched mode):**

- ✅ Read - Can read session files
- ✅ Bash - Can run git commands (read-only)
- ✅ AskUserQuestion - Available but not used in raw mode
- ❌ Edit - NO access
- ❌ Write - NO access
- ❌ Task - NO access

**Error handling:**

If agent returns error JSON:

```
❌ Error: [agent error message]

Common causes:
- No ExitPlanMode found in session files
- Session files don't exist or are corrupted
- Session ID is incorrect

Try:
- Ensure you used ExitPlanMode to present a plan
- Check session files exist: ls ~/.claude/projects/[session_id]/data/
- Use /erk:plan-save with conversation context instead
```

### Step 4: Parse Agent Response

The agent returns markdown in this format:

```markdown
# Plan: [title extracted from plan]

## Enrichment Details

### Process Summary

- **Mode**: raw
- **Guidance applied**: no
- **Questions asked**: 0
- **Context categories extracted**: 0 of 8

---

[Full plan content...]
```

**Parse markdown response:**

```bash
# Check for error
if echo "$result" | grep -q "^## Error:"; then
    # Extract error message
    error_msg=$(echo "$result" | sed -n 's/^## Error: //p')
    echo "❌ Error: $error_msg"
    exit 1
fi

# Extract title from first heading
plan_title=$(echo "$result" | grep -m1 "^# Plan:" | sed 's/^# Plan: //')

# Use full content for issue
plan_content="$result"
```

**Validation:**

- Check for `## Error:` prefix (indicates error)
- Ensure `# Plan:` heading exists
- Verify content is non-empty

**Error handling:**

If error prefix found:

```
❌ Error: [error message from markdown]
```

If no `# Plan:` heading:

```
❌ Error: Agent returned invalid markdown (missing # Plan: heading)

[Display agent response for debugging]
```

### Step 5: Save Plan to Temporary File

Write plan content to a temporary file for kit CLI:

```bash
# Create temp file
temp_plan=$(mktemp)

# Write plan content
cat > "$temp_plan" <<'PLAN_EOF'
[plan_content from agent JSON]
PLAN_EOF
```

### Step 6: Create GitHub Issue via Kit CLI

Call the kit CLI command to create the issue:

```bash
# Call kit CLI with plan file
result=$(dot-agent run erk create-enriched-plan-from-context --plan-file "$temp_plan")

# Clean up temp file
rm "$temp_plan"

# Parse JSON result
echo "$result" | jq .
```

**Expected output:**

```json
{
  "success": true,
  "issue_number": 123,
  "issue_url": "https://github.com/owner/repo/issues/123"
}
```

**Error handling:**

If command fails:

```
❌ Error: Failed to create GitHub issue

[Display kit CLI error output]
```

### Step 7: Display Success Output

#### Substep 7a: Generate and Display Execution Summary

After receiving the successful response from the kit CLI, generate a concise summary of what was accomplished:

**Summary Generation Process:**

1. **Extract one-sentence overview** - Create a brief, high-level summary of the plan's main objective from the plan_content
2. **Extract three key bullet points** - Identify the three most important implementation steps or outcomes from the plan
3. **Format and display** - Present summary before the issue URL using this format:

```
**Execution Summary:**

[One sentence overview of what was accomplished]

- [Key bullet point 1]
- [Key bullet point 2]
- [Key bullet point 3]
```

**Implementation note:** Extract summary from the plan_content received from the agent. Raw mode plans may have less structured content than enriched plans, so extract from whatever plan structure exists in the raw content.

#### Substep 7b: Display Issue URL and Next Steps

Show the user the issue URL and copy-pastable commands:

```
✅ Raw plan saved to GitHub issue

**Issue:** [issue_url]

**Next steps:**

View the plan:
    gh issue view [issue_number]

Implement directly:
    erk implement [issue_number]

Implement with auto-confirmation (yolo mode):
    erk implement [issue_number] --yolo

Implement and auto-submit PR (dangerous mode):
    erk implement [issue_number] --dangerous

Submit plan to erk queue:
    erk submit [issue_number]

**Note:** This plan was extracted raw from session files without enrichment.
```

**Formatting requirements:**

- Use `✅` for success indicator
- Bold `**Issue:**` and `**Next steps:**`
- Show actual issue URL (clickable)
- Show actual issue number in commands
- Add note about raw extraction

## Error Scenarios

### No ExitPlanMode Found

```
❌ Error: No plan found in session files

Details: No ExitPlanMode tool use found in session JSONL files

Suggested action:
  1. Ensure you used ExitPlanMode to present a plan in this session
  2. Check session files: ls ~/.claude/projects/[session_id]/data/
  3. Try /erk:plan-save with conversation context instead
```

### Session Files Not Found

```
❌ Error: Session files not accessible

Session ID: [session_id]
Expected location: ~/.claude/projects/[session_id]/data/*.jsonl

Suggested action:
  1. Verify session ID is correct
  2. Check directory exists and has read permissions
  3. Use /erk:plan-save with conversation context instead
```

### GitHub CLI Not Authenticated

```
❌ Error: GitHub CLI not authenticated

To use this command, authenticate with GitHub:

    gh auth login

Then try again.
```

## Architecture Benefits

| Aspect          | Previous Design       | Current Design                   |
| --------------- | --------------------- | -------------------------------- |
| Enforcement     | Text warnings         | Structural (tool restrictions)   |
| Implementation  | Inline command logic  | Dedicated agent (raw mode)       |
| Safety          | Behavioral compliance | Physically impossible to violate |
| Session parsing | Kit CLI direct        | Agent delegation                 |
| Bypass-safe     | ❌ No                 | ✅ Yes                           |

## Technical Details

**Session File Location:**

Plans are stored in Claude session files:

```
~/.claude/projects/<session-id>/data/*.jsonl
```

Each JSONL line is a message. The agent searches for:

```json
{
  "type": "tool_use",
  "name": "ExitPlanMode",
  "input": {
    "plan": "[markdown plan content]"
  }
}
```

**Latest Plan Selection:**

If multiple ExitPlanMode entries exist, the agent selects the most recent by file timestamp and line position.

## Important Notes

- **Fast Path**: No interactive questions, no enrichment
- **Deterministic**: Session file parsing is repeatable
- **Raw Content**: Preserves plan exactly as found
- **Structural Safety**: Agent cannot edit files (tool restrictions)
- **Bypass-Safe**: Works correctly even with bypass permissions
- **Reuses Agent**: Same plan-extractor agent, just in raw mode
- **Command Comparison**:
  - `save-raw-plan`: Session files → Raw plan → GitHub issue (this command)
  - `save-plan`: Conversation → Enriched plan → GitHub issue (interactive)

## Development Notes

**For maintainers:**

This command demonstrates **mode-based agent reuse**:

- Same agent (plan-extractor)
- Different mode (raw vs enriched)
- Different behavior (file extraction vs conversation parsing)
- Same safety guarantees (tool restrictions)

**Benefits:**

- Single agent handles both workflows
- Consistent JSON output format
- Reusable orchestration pattern
- Structural safety in both modes

**Agent file:** `.claude/agents/erk/plan-extractor.md`
