---
description: Enrich plan from current session with context extraction
---

# /erk:session-plan-enrich

## Goal

**Extract an implementation plan from the current session, enrich it with semantic understanding, and present for review.**

This command enables iterative plan refinement by enriching the plan in your current Claude session with context extraction.

**What this command does:**

- ✅ Find plan in session logs (ExitPlanMode markers)
- ✅ Apply optional guidance to plan
- ✅ Interactively enhance plan for autonomous execution
- ✅ Extract semantic understanding and context (8 categories)
- ✅ Present enriched plan via ExitPlanMode for review
- ✅ Enable save to GitHub issue via `/erk:plan-save`

**What this command CANNOT do:**

- ❌ Edit files on current branch (structurally impossible - agent lacks tools)
- ❌ Implement code (agent has no Write/Edit capabilities)
- ❌ Make commits (agent restricted from git mutations)

**Workflow:**

```
Create plan → ExitPlanMode
           → /erk:session-plan-enrich [guidance]
           → Review enriched plan
           → [optional: iterate with more guidance]
           → /erk:plan-save → GitHub issue
```

## Usage

```bash
/erk:session-plan-enrich [guidance]
```

**Examples:**

- `/erk:session-plan-enrich` - Enrich plan with default context extraction
- `/erk:session-plan-enrich "Make error handling more robust and add retry logic"` - Apply guidance
- `/erk:session-plan-enrich "Fix: Use LBYL instead of try/except throughout"` - Apply corrections

## Prerequisites

- An implementation plan must exist in session logs (created with ExitPlanMode)
- Current working directory must be in a git repository
- GitHub CLI (gh) must be installed and authenticated

## Architecture

```
/erk:session-plan-enrich (orchestrator)
  ↓
  ├─→ Validate prerequisites (git repo, gh auth)
  ├─→ Extract plan from session logs via kit CLI
  │     ↓
  │     dot-agent run erk save-plan-from-session --extract-only
  │     Returns JSON: {plan_content, title}
  ├─→ Launch plan-extractor agent (enriched mode)
  │     ↓
  │     Agent enriches plan with context + guidance + questions
  │     Agent returns markdown: # Plan: ... with Enrichment Details
  │     (Agent has NO Edit/Write tools - structurally safe)
  └─→ Present enriched plan via ExitPlanMode
```

**Key Innovation:** The enriched plan is stored via ExitPlanMode, enabling:

1. User review before saving to GitHub
2. Iterative refinement (run again with more guidance)
3. Composition with `/erk:plan-save`

---

## Command Instructions

You are executing the `/erk:session-plan-enrich` command. Follow these steps carefully:

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

### Step 2: Extract Plan from Session Logs

Use kit CLI to extract the plan from session logs:

```bash
# Extract plan using kit CLI
plan_result=$(dot-agent run erk save-plan-from-session --extract-only --format json 2>&1)
```

**Parse the result:**

```bash
# Check if extraction succeeded
if echo "$plan_result" | jq -e '.success' > /dev/null 2>&1; then
    # SUCCESS: Extract plan content and title
    plan_content=$(echo "$plan_result" | jq -r '.plan_content')
    plan_title=$(echo "$plan_result" | jq -r '.title')
else
    # FAILURE: Report error
    error_msg=$(echo "$plan_result" | jq -r '.error // "Unknown error"')
    echo "❌ Error: Failed to extract plan from session logs"
    echo "Details: $error_msg"
fi
```

**Error handling:**

If no plan found:

```
❌ Error: No plan found in session logs

This command requires a plan created with ExitPlanMode. To fix:

1. Create a plan (enter Plan mode if needed)
2. Exit Plan mode using the ExitPlanMode tool
3. Run this command again

The plan will be extracted from session logs automatically.
```

### Step 3: Launch Plan-Extractor Agent (Enriched Mode)

Use the Task tool to launch the specialized agent with the extracted plan:

```json
{
  "subagent_type": "plan-extractor",
  "description": "Enrich plan with context",
  "prompt": "Enrich the pre-extracted implementation plan with semantic understanding and guidance.\n\nInput:\n{\n  \"mode\": \"enriched\",\n  \"plan_content\": \"[pre-extracted plan markdown from session logs]\",\n  \"guidance\": \"[guidance text or empty string]\"\n}\n\nThe plan has been pre-extracted from session logs using ExitPlanMode markers. Your job:\n1. Apply guidance if provided (in-memory)\n2. Ask clarifying questions via AskUserQuestion tool\n3. Extract semantic understanding (8 categories) from conversation context\n4. Return markdown output with enrichment details.\n\nExpected output: Markdown with # Plan: title, Enrichment Details section, and full plan content.",
  "model": "haiku"
}
```

**What the agent does:**

1. Receives pre-extracted plan from kit CLI
2. Applies guidance if provided (in-memory)
3. Asks clarifying questions via AskUserQuestion tool
4. Extracts semantic understanding (8 categories) from conversation
5. Returns enriched markdown output

**Agent tool restrictions (enforced in YAML):**

- ✅ Read - Can read conversation and files
- ✅ Bash - Can run git/kit CLI (read-only)
- ✅ AskUserQuestion - Can clarify ambiguities
- ❌ Edit - NO access to file editing
- ❌ Write - NO access to file writing
- ❌ Task - NO access to subagents

### Step 4: Present Enriched Plan via ExitPlanMode

After receiving the enriched plan from the agent, use the **ExitPlanMode** tool to present the plan to the user and store it in session logs.

**Critical:** This step makes the enriched plan available for subsequent `/erk:plan-save` command.

```
Call ExitPlanMode with the enriched markdown content from the agent.
```

The user will see the enriched plan in the conversation and can:

1. Review the enrichment
2. Run `/erk:session-plan-enrich "more guidance"` to iterate
3. Run `/erk:plan-save` to save to GitHub issue

### Step 5: Display Summary

After presenting the plan, display a summary:

```
✅ Plan enriched and ready for review

**Enrichment:** [N] context categories extracted, [M] questions asked
**Guidance applied:** [yes/no - guidance text if provided]

**Next steps:**

Save to GitHub issue:
    /erk:plan-save

Iterate with additional guidance:
    /erk:session-plan-enrich "Add retry logic"
```

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

## Error Scenarios

### No Plan Found in Session Logs

```
❌ Error: No plan found in session logs

This command requires a plan created with ExitPlanMode. To fix:

1. Create a plan (enter Plan mode if needed)
2. Exit Plan mode using the ExitPlanMode tool
3. Run this command again

The plan will be extracted from session logs automatically.
```

### Agent Error

```
❌ Error: [agent error message]

The plan-extractor agent encountered an error during enrichment.
[Display agent error details]
```

### Guidance Without Plan

```
❌ Error: Guidance provided but no plan found

Guidance: "[guidance text]"

Please create a plan first using ExitPlanMode, then run this command.
```

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Extraction:**
✅ Implementation plan extracted from session logs (ExitPlanMode markers)
✅ Kit CLI extraction returns valid JSON with plan_content
✅ If guidance provided, it has been applied to the plan by agent
✅ Semantic understanding extracted from conversation and integrated

**Presentation:**
✅ Enriched plan presented via ExitPlanMode
✅ Plan stored in session logs for subsequent commands
✅ Summary displayed with next steps

## Development Notes

**For maintainers:**

This command demonstrates the **session-based enrichment pattern**:

1. Command extracts plan from session logs
2. Command launches specialized agent for enrichment
3. Agent enriches plan (structurally safe)
4. Command presents via ExitPlanMode (enables composition)
5. User can iterate or save

**Related commands:**

- `/erk:plan-enrich <issue>` - Enrich plan from GitHub issue
- `/erk:plan-save` - Save plan from session logs to GitHub issue

**Agent file:** `.claude/agents/erk/plan-extractor.md`
