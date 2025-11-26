---
description: Extract plan from Claude session and create GitHub issue (no enrichment)
---

# /erk:plan-save-raw

⚠️ **CRITICAL: This command creates a GitHub issue with the plan - it does NOT implement code!**

## Goal

**Extract the latest implementation plan from Claude session files and create a GitHub issue with the raw plan content.**

This command uses an **agent-based architecture** with structural enforcement (tool restrictions) to prevent accidental code implementation.

**What this command does:**

- ✅ Find plan in session logs (ExitPlanMode markers)
- ✅ Preserve plan content exactly as found
- ✅ Create GitHub issue with raw plan

**What this command does NOT do:**

- ❌ No conversation context searching (session logs only)
- ❌ No plan enhancement or enrichment
- ❌ No interactive clarifying questions
- ❌ No semantic understanding extraction
- ❌ No guidance parameter

**What this command CANNOT do:**

- ❌ Edit files on current branch (structurally impossible - agent lacks tools)
- ❌ Implement code (agent has no Write/Edit capabilities)
- ❌ Make commits (agent restricted from git mutations)

**What happens AFTER:**

- ⏭️ Implement directly: `erk implement <issue>`

## Usage

```bash
/erk:plan-save-raw
```

**Note:** This command does not accept a guidance parameter. Use `/erk:plan-save [guidance]` if you need to apply guidance to the plan.

## Prerequisites

- An implementation plan must exist in session logs (created with ExitPlanMode)
- Current working directory must be in a git repository
- GitHub CLI (gh) must be installed and authenticated
- Repository must have issues enabled

## Architecture

This command uses the same **plan-extractor agent** as `/erk:plan-save` but in `raw` mode:

```
/erk:plan-save-raw (orchestrator)
  ↓
  ├─→ Validate prerequisites (git repo, gh auth)
  ├─→ Determine session ID (from environment or current session)
  ├─→ Launch plan-extractor agent in RAW mode (Task tool)
  │     ↓
  │     Agent reads session JSONL files
  │     Agent extracts ExitPlanMode content
  │     Agent returns markdown: # Plan: ... (raw mode - no enrichment)
  │     (Agent has NO Edit/Write tools - structurally safe)
  ├─→ Save plan to temp file
  ├─→ Call kit CLI: dot-agent run erk create-enriched-plan-from-context --plan-file
  │     ↓
  │     Kit CLI creates GitHub issue
  └─→ Display results (issue URL + copy-pastable commands)
```

**Key Innovation:** The agent has **tool restrictions** in YAML front matter:

```yaml
---
name: plan-extractor
tools: Read, Bash, AskUserQuestion
---
```

This makes it **structurally impossible** to accidentally edit files, even with bypass permissions enabled.

## What Happens

When you run this command, these steps occur:

1. **Verify Prerequisites** - Check git repo and GitHub CLI authentication
2. **Determine Session ID** - Get current session from environment or find most recent
3. **Launch Agent** - Delegate to plan-extractor agent in raw mode
4. **Extract Plan** - Agent reads session JSONL for ExitPlanMode (no enrichment)
5. **Receive Markdown** - Agent returns raw markdown with minimal metadata
6. **Create Issue** - Use kit CLI to create GitHub issue
7. **Display Results** - Show issue URL and next-step commands

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Extraction:**
✅ Implementation plan extracted from session logs (ExitPlanMode markers)
✅ Agent returns raw plan content without enrichment

**Issue Creation:**
✅ GitHub issue created with raw plan content
✅ Issue has `erk-plan` label applied
✅ Issue title matches plan title

**Output:**
✅ JSON output provided with issue URL and number
✅ Copy-pastable commands displayed (view + implement variants)
✅ All commands use actual issue number, not placeholders
✅ Next steps clearly communicated to user

---

## Command Instructions

You are executing the `/erk:plan-save-raw` command. Follow these steps carefully:

### Step 1: Validate Prerequisites

@../../docs/erk/includes/save-plan-workflow.md#shared-step-validate-prerequisites

### Step 1.5: Determine Session ID

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

### Step 2: Launch Plan-Extractor Agent (Raw Mode)

Use the Task tool to launch the agent in raw mode:

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

**Agent tool restrictions (enforced in YAML):**

- ✅ Read - Can read session files
- ✅ Bash - Can run git commands (read-only)
- ✅ AskUserQuestion - Available but not used in raw mode
- ❌ Edit - NO access to file editing
- ❌ Write - NO access to file writing
- ❌ Task - NO access to subagents

**Error handling:**

If agent returns error:

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

### Step 3: Parse Agent Response

@../../docs/erk/includes/save-plan-workflow.md#shared-step-parse-agent-response

### Step 4: Save Plan to Temporary File

@../../docs/erk/includes/save-plan-workflow.md#shared-step-save-plan-to-temporary-file

### Step 5: Create GitHub Issue via Kit CLI

@../../docs/erk/includes/save-plan-workflow.md#shared-step-create-github-issue-via-kit-cli

### Step 6: Display Success Output

#### Substep 6a: Generate and Display Execution Summary

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

#### Substep 6b: Display Issue URL and Next Steps

@../../docs/erk/includes/save-plan-workflow.md#shared-step-display-issue-url-and-next-steps

**Note:** Add this footer after the standard next steps:

```
**Note:** This plan was extracted raw from session files without enrichment.
For enriched plans with semantic context, use: /erk:plan-save
```

### Step 7: Raw Mode Confirmation

Raw mode does not include enrichment details. The GitHub issue will contain the plan exactly as found in session logs, with minimal metadata (mode: raw, no guidance, no questions asked).

## Error Scenarios

### No Plan Found in Session Logs

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

@../../docs/erk/includes/save-plan-workflow.md#shared-error-scenarios

## Architecture Benefits

@../../docs/erk/includes/save-plan-workflow.md#shared-architecture-benefits

## Troubleshooting

@../../docs/erk/includes/save-plan-workflow.md#shared-troubleshooting

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

## Development Notes

**For maintainers:**

This command demonstrates **mode-based agent reuse**:

- Same agent (plan-extractor)
- Different mode (raw vs enriched)
- Different behavior (file extraction without enrichment vs conversation parsing with enrichment)
- Same safety guarantees (tool restrictions)

**Benefits:**

- Single agent handles both workflows
- Consistent markdown output format
- Reusable orchestration pattern
- Structural safety in both modes

**Shared workflow:** This command shares common steps with `/erk:plan-save` via `docs/save-plan-workflow.md`.

**Command Comparison:**

| Aspect     | `/erk:plan-save` (enriched) | `/erk:plan-save-raw` (this) |
| ---------- | --------------------------- | --------------------------- |
| Mode       | enriched                    | raw                         |
| Enrichment | Full 8-category context     | None                        |
| Questions  | Interactive clarifications  | None                        |
| Guidance   | Accepts `[guidance]` param  | No guidance parameter       |
| Fallback   | Session logs → conversation | Session logs only           |

**Agent file:** `.claude/agents/erk/plan-extractor.md`
