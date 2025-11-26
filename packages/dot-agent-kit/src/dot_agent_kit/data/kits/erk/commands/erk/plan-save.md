---
description: Extract plan from conversation, fully enhance it, and create GitHub issue directly
---

# /erk:plan-save

⚠️ **CRITICAL: This command creates a GitHub issue with the plan - it does NOT implement code!**

## Goal

**Extract an implementation plan from conversation, enhance it for autonomous execution, and create a GitHub issue directly.**

This command uses an **agent-based architecture** with structural enforcement (tool restrictions) to prevent accidental code implementation.

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
/erk:plan-save [guidance]
```

**Examples:**

- `/erk:plan-save` - Create GitHub issue with enhanced plan
- `/erk:plan-save "Make error handling more robust and add retry logic"` - Apply guidance to plan
- `/erk:plan-save "Fix: Use LBYL instead of try/except throughout"` - Apply corrections to plan

## Prerequisites

- An implementation plan must exist in conversation
- Current working directory must be in a git repository
- GitHub CLI (gh) must be installed and authenticated
- Repository must have issues enabled
- (Optional) Guidance text for final corrections/additions to the plan

## Architecture

This command uses a **specialized agent** for plan extraction/enrichment instead of inline command logic:

```
/erk:plan-save (orchestrator)
  ↓
  ├─→ Validate prerequisites (git repo, gh auth)
  ├─→ Extract plan from session logs via kit CLI
  │     ↓
  │     dot-agent run erk save-plan-from-session --extract-only
  │     Returns JSON: {plan_content, title}
  ├─→ Launch plan-extractor agent (Task tool) with pre-extracted plan
  │     ↓
  │     Agent enriches plan with context + guidance + questions
  │     Agent returns markdown: # Plan: ... with Enrichment Details section
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
2. **Extract Plan** - Use kit CLI to extract plan from session logs (ExitPlanMode markers)
3. **Launch Agent** - Delegate to plan-extractor agent with pre-extracted plan
4. **Enrich Plan** - Agent applies guidance, extracts context, asks questions
5. **Receive Markdown** - Agent returns markdown with enrichment details
6. **Create Issue** - Use kit CLI to create GitHub issue
7. **Display Results** - Show issue URL and next-step commands

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
✅ Implementation plan extracted from session logs (ExitPlanMode markers)
✅ Kit CLI extraction returns valid JSON with plan_content
✅ If guidance provided, it has been applied to the plan by agent
✅ Semantic understanding extracted from conversation and integrated

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

You are executing the `/erk:plan-save` command. Follow these steps carefully:

### Step 1: Validate Prerequisites

@../../docs/erk/includes/save-plan-workflow.md#shared-step-validate-prerequisites

### Step 1.5: Extract Plan from Session Logs (with Fallback)

Use kit CLI to extract the plan from session logs before launching the agent:

```bash
# Extract plan using kit CLI
plan_result=$(dot-agent run erk save-plan-from-session --extract-only --format json 2>&1)
```

**Parse the result with fallback handling:**

```bash
# Check if extraction succeeded
if echo "$plan_result" | jq -e '.success' > /dev/null 2>&1; then
    # SUCCESS: Extract plan content and title
    plan_content=$(echo "$plan_result" | jq -r '.plan_content')
    plan_title=$(echo "$plan_result" | jq -r '.title')

    # Mark that we successfully extracted from session logs
    extraction_mode="session_logs"
else
    # FALLBACK: Session log extraction failed - agent will search conversation
    error_msg=$(echo "$plan_result" | jq -r '.error // "Unknown error"')

    echo "⚠️  Warning: Could not extract plan from session logs"
    echo "Details: $error_msg"
    echo ""
    echo "Falling back to conversation search..."
    echo ""

    # Set plan_content to empty - agent will search conversation
    plan_content=""
    extraction_mode="conversation_search"
fi
```

**Why this step:**

- **Primary path (session logs)**: Kit CLI Push-Down Pattern
  - Mechanical JSON parsing done by kit CLI
  - ExitPlanMode markers provide unambiguous identification
  - Token savings from avoiding conversation search
  - Structured error handling

- **Fallback path (conversation search)**: Backward compatibility
  - Agent searches conversation context if session logs unavailable
  - Supports workflows where plan wasn't created with ExitPlanMode
  - Maintains compatibility with existing behavior

**Error handling strategy:**

1. **Try session logs first** (preferred): Fast, reliable, token-efficient
2. **Fall back to conversation search**: Compatible with all plan creation methods
3. **Only error if both fail**: Agent will report if no plan found anywhere

### Step 2: Launch Plan-Extractor Agent (Enriched Mode)

Use the Task tool to launch the specialized agent. The prompt varies based on extraction mode:

**If extraction_mode == "session_logs" (plan_content populated):**

```json
{
  "subagent_type": "plan-extractor",
  "description": "Enrich plan with context",
  "prompt": "Enrich the pre-extracted implementation plan with semantic understanding and guidance.\n\nInput:\n{\n  \"mode\": \"enriched\",\n  \"plan_content\": \"[pre-extracted plan markdown from session logs]\",\n  \"guidance\": \"[guidance text or empty string]\"\n}\n\nThe plan has been pre-extracted from session logs using ExitPlanMode markers. Your job:\n1. Apply guidance if provided (in-memory)\n2. Ask clarifying questions via AskUserQuestion tool\n3. Extract semantic understanding (8 categories) from conversation context\n4. Return markdown output with enrichment details.\n\nExpected output: Markdown with # Plan: title, Enrichment Details section, and full plan content.",
  "model": "haiku"
}
```

**If extraction_mode == "conversation_search" (plan_content empty - fallback):**

```json
{
  "subagent_type": "plan-extractor",
  "description": "Extract and enrich plan",
  "prompt": "Extract implementation plan from conversation context, then enrich with semantic understanding and guidance.\n\nInput:\n{\n  \"mode\": \"enriched\",\n  \"plan_content\": \"\",\n  \"guidance\": \"[guidance text or empty string]\"\n}\n\nSession log extraction failed. Search conversation context for implementation plan.\nPlans typically appear after discussion. Your job:\n1. Find plan in conversation\n2. Apply guidance if provided (in-memory)\n3. Ask clarifying questions via AskUserQuestion tool\n4. Extract semantic understanding (8 categories) from conversation context\n5. Return markdown output with enrichment details.\n\nExpected output: Markdown with # Plan: title, Enrichment Details section, and full plan content.",
  "model": "haiku"
}
```

**What the agent does:**

**Primary path (session_logs):**

1. Receives pre-extracted plan from kit CLI
2. Applies guidance if provided (in-memory)
3. Asks clarifying questions via AskUserQuestion tool
4. Extracts semantic understanding (8 categories) from conversation
5. Returns markdown output

**Fallback path (conversation_search):**

1. Searches conversation for plan
2. Applies guidance if provided (in-memory)
3. Asks clarifying questions via AskUserQuestion tool
4. Extracts semantic understanding (8 categories) from conversation
5. Returns markdown output

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

**Implementation note:** Extract summary from the plan_content received from the agent. Look for major sections, objectives, or implementation phases to create meaningful bullet points.

#### Substep 6b: Display Issue URL and Next Steps

@../../docs/erk/includes/save-plan-workflow.md#shared-step-display-issue-url-and-next-steps

### Step 7: Note on Enrichment Details

The enrichment details (guidance applied, questions asked, clarifications, context categories) are now embedded in the markdown output from the agent in the "Enrichment Details" section. No separate summary is needed - the GitHub issue will contain these details.

## Error Scenarios

### No Plan Found in Session Logs

```
❌ Error: Failed to extract plan from session logs

Details: No plan found in Claude session files

This command requires a plan created with ExitPlanMode. To fix:

1. Create a plan (enter Plan mode if needed)
2. Exit Plan mode using the ExitPlanMode tool
3. Run this command again

The plan will be extracted from session logs automatically.
```

### No Plan Found (Fallback Failed)

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

@../../docs/erk/includes/save-plan-workflow.md#shared-error-scenarios

## Architecture Benefits

@../../docs/erk/includes/save-plan-workflow.md#shared-architecture-benefits

## Troubleshooting

@../../docs/erk/includes/save-plan-workflow.md#shared-troubleshooting

## Development Notes

**For maintainers:**

This command demonstrates the **agent-based orchestration pattern**:

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

**Shared workflow:** This command shares common steps with `/erk:plan-save-raw` via `docs/save-plan-workflow.md`.

**Agent file:** `.claude/agents/erk/plan-extractor.md`
