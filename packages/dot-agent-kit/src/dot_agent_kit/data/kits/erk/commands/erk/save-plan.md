---
description: Extract plan from conversation, fully enhance it, and create GitHub issue directly (v2 - agent-based)
---

# /erk:save-plan-v2

⚠️ **CRITICAL: This command creates a GitHub issue with the plan - it does NOT implement code!**

## Goal

**Extract an implementation plan from conversation, enhance it for autonomous execution, and create a GitHub issue directly.**

This is the **v2 agent-based version** that uses structural enforcement (tool restrictions) instead of text warnings to prevent accidental code implementation.

**What this command does:**

- ✅ Find plan in conversation
- ✅ Apply optional guidance to plan
- ✅ Interactively enhance plan for autonomous execution
- ✅ Extract semantic understanding and context
- ✅ Structure complex plans into phases (when beneficial)
- ✅ Create GitHub issue with enhanced plan

**What this command CANNOT do:**

- ❌ Edit files on current branch (structurally impossible - agent lacks tools)
- ❌ Implement code (agent has no Write/Edit capabilities)
- ❌ Make commits (agent restricted from git mutations)

**What happens AFTER:**

- ⏭️ Implement directly: `erk implement <issue>`

## Usage

```bash
/erk:save-plan-v2 [guidance]
```

**Examples:**

- `/erk:save-plan-v2` - Create GitHub issue with enhanced plan
- `/erk:save-plan-v2 "Make error handling more robust and add retry logic"` - Apply guidance to plan
- `/erk:save-plan-v2 "Fix: Use LBYL instead of try/except throughout"` - Apply corrections to plan

## Prerequisites

- An implementation plan must exist in conversation
- Current working directory must be in a git repository
- GitHub CLI (gh) must be installed and authenticated
- Repository must have issues enabled
- (Optional) Guidance text for final corrections/additions to the plan

## Architecture

This command uses a **specialized agent** for plan extraction/enrichment instead of inline command logic:

```
/erk:save-plan-v2 (orchestrator)
  ↓
  ├─→ Validate prerequisites (git repo, gh auth)
  ├─→ Launch plan-extractor agent (Task tool)
  │     ↓
  │     Agent returns JSON: {plan_title, plan_content, enrichment: {...}}
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
2. **Launch Agent** - Delegate to plan-extractor agent (read-only tools)
3. **Receive JSON** - Agent returns structured plan data
4. **Create Issue** - Use kit CLI to create GitHub issue
5. **Display Results** - Show issue URL and next-step commands

## Semantic Understanding & Context Preservation

**Why This Matters:** Planning agents often discover valuable insights that would be expensive for implementing agents to re-derive. Capturing this context saves time and prevents errors.

The plan-extractor agent captures **8 categories of context:**

1. **API/Tool Quirks** - Undocumented behaviors, timing issues
2. **Architectural Insights** - WHY decisions were made
3. **Domain Logic & Business Rules** - Non-obvious invariants
4. **Complex Reasoning** - Alternatives considered and rejected
5. **Known Pitfalls** - Anti-patterns that cause problems
6. **Raw Discoveries Log** - Everything learned during planning
7. **Planning Artifacts** - Code examined, commands run
8. **Implementation Risks** - Uncertainties, performance concerns

See agent documentation for full details: `.claude/agents/erk/plan-extractor.md`

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Extraction:**
✅ Implementation plan extracted from conversation context
✅ If guidance provided, it has been applied to the plan
✅ Semantic understanding extracted and integrated

**Issue Creation:**
✅ GitHub issue created with enhanced plan content
✅ Issue has `erk-plan` label applied
✅ Issue title matches plan title

**Output:**
✅ JSON output provided with issue URL and number
✅ Copy-pastable commands displayed (view + implement variants)
✅ All commands use actual issue number, not placeholders
✅ Next steps clearly communicated to user

---

## Command Instructions

You are executing the `/erk:save-plan-v2` command. Follow these steps carefully:

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

### Step 2: Launch Plan-Extractor Agent

Use the Task tool to launch the specialized agent:

```
Launch agent: plan-extractor
Mode: enriched
Guidance: [user-provided guidance if any, otherwise null]
```

**Task tool invocation:**

```json
{
  "subagent_type": "plan-extractor",
  "description": "Extract and enrich plan",
  "prompt": "Extract the implementation plan from conversation context, apply guidance if provided, ask clarifying questions, extract semantic understanding, and return structured JSON.\n\nInput:\n- Mode: enriched\n- Guidance: [guidance text or 'none']\n\nExpected output: JSON with plan_title, plan_content, and enrichment metadata.",
  "model": "haiku"
}
```

**What the agent does:**

1. Finds plan in conversation
2. Applies guidance if provided (in-memory)
3. Asks clarifying questions via AskUserQuestion tool
4. Extracts semantic understanding (8 categories)
5. Returns JSON output

**Agent tool restrictions (enforced in YAML):**

- ✅ Read - Can read conversation and files
- ✅ Bash - Can run git/kit CLI (read-only)
- ✅ AskUserQuestion - Can clarify ambiguities
- ❌ Edit - NO access to file editing
- ❌ Write - NO access to file writing
- ❌ Task - NO access to subagents

**Error handling:**

If agent returns error JSON:

```
❌ Error: [agent error message]

[Display agent error details]
```

### Step 3: Parse Agent Response

The agent returns JSON in this format:

```json
{
  "success": true,
  "plan_title": "Add user authentication",
  "plan_content": "## Overview\n\n...",
  "enrichment": {
    "guidance_applied": true,
    "questions_asked": 2,
    "clarifications": ["..."],
    "context_extracted": true
  }
}
```

**Validate response:**

- Check `success` field is true
- Ensure `plan_title` and `plan_content` are present
- Verify `plan_content` is non-empty

**Error handling:**

If `success` is false or fields missing:

```
❌ Error: Agent returned invalid response

[Display agent response for debugging]
```

### Step 4: Save Plan to Temporary File

Write plan content to a temporary file for kit CLI:

```bash
# Create temp file
temp_plan=$(mktemp /tmp/erk-plan-XXXXXX.md)

# Write plan content
cat > "$temp_plan" <<'PLAN_EOF'
[plan_content from agent JSON]
PLAN_EOF
```

**Why temp file:** Kit CLI command expects `--plan-file` option for clean separation of concerns.

### Step 5: Create GitHub Issue via Kit CLI

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

### Step 6: Display Success Output

Show the user the issue URL and copy-pastable commands:

```
✅ Plan saved to GitHub issue

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
```

**Formatting requirements:**

- Use `✅` for success indicator
- Bold `**Issue:**` and `**Next steps:**`
- Show actual issue URL (clickable)
- Show actual issue number in commands (not `<issue-number>`)
- Each command should be on its own line with proper indentation
- Commands should be copy-pastable (no markdown formatting inside)

### Step 7: Enrichment Summary (Optional)

If the agent asked questions or applied guidance, show a summary:

```
**Enrichment applied:**

- Guidance: [guidance text]
- Questions asked: [count]
- Clarifications: [list]
- Context extracted: [yes/no]
```

## Error Scenarios

### No Plan Found

```
❌ Error: No plan found in conversation

Please present an implementation plan in the conversation, then run this command.

A plan typically includes:
- Overview or objective
- Implementation steps or phases
- Success criteria
```

### Guidance Without Plan

```
❌ Error: Guidance provided but no plan found

Guidance: "[guidance text]"

Please create a plan first, then apply guidance.
```

### GitHub CLI Not Authenticated

```
❌ Error: GitHub CLI not authenticated

To use this command, authenticate with GitHub:

    gh auth login

Then try again.
```

### Kit CLI Error

```
❌ Error: Failed to create GitHub issue

[Full kit CLI error output]

Common causes:
- Repository has issues disabled
- Network connectivity issue
- GitHub API rate limit
```

## Comparison with v1

| Feature       | v1 (save-plan)                  | v2 (save-plan-v2)                |
| ------------- | ------------------------------- | -------------------------------- |
| Enforcement   | Text warnings (7 instances)     | Structural (tool restrictions)   |
| Agent         | Inline command logic            | Dedicated agent                  |
| Safety        | Relies on behavioral compliance | Physically impossible to violate |
| Lines of code | 402 lines                       | ~120 lines (orchestrator)        |
| Bypass-safe   | ❌ No                           | ✅ Yes                           |

## Troubleshooting

### "Agent returned error"

**Cause:** Agent encountered issue during extraction/enrichment
**Solution:**

- Check agent error message for details
- Ensure plan is in conversation context
- Verify plan has clear structure

### "Invalid JSON from agent"

**Cause:** Agent output malformed or unexpected
**Solution:**

- Check agent output for debugging
- Retry command
- Report issue if persistent

### "Temp file error"

**Cause:** Cannot create temporary file (permissions, disk space)
**Solution:**

- Check `/tmp/` directory permissions
- Ensure disk space available
- Check `mktemp` command availability

## Development Notes

**For maintainers:**

This v2 command demonstrates the **agent-based orchestration pattern**:

1. Command validates prerequisites
2. Command launches specialized agent with tool restrictions
3. Agent does the work (structurally safe)
4. Agent returns JSON
5. Command handles I/O and user feedback

**Benefits:**

- Separation of concerns (orchestration vs. logic)
- Structural safety (agent can't violate tool restrictions)
- Reusable agents (plan-extractor can be used elsewhere)
- Testable components (agent can be tested independently)
- Shorter commands (orchestration only)

**Agent file:** `.claude/agents/erk/plan-extractor.md`
