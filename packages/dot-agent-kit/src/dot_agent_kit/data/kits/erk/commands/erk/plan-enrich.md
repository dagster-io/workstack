---
description: Enrich plan from GitHub issue with context extraction
---

# /erk:plan-enrich

## Goal

**Fetch an implementation plan from a GitHub issue, enrich it with semantic understanding, and present for review.**

This command enables iterative plan refinement by enriching already-persisted plans with context extraction.

**What this command does:**

- ✅ Fetch plan content from GitHub issue
- ✅ Interactively enhance plan for autonomous execution
- ✅ Extract semantic understanding and context (8 categories)
- ✅ Present enriched plan via ExitPlanMode for review
- ✅ Enable save to new GitHub issue via `/erk:plan-save`

**What this command CANNOT do:**

- ❌ Edit files on current branch (structurally impossible - agent lacks tools)
- ❌ Implement code (agent has no Write/Edit capabilities)
- ❌ Make commits (agent restricted from git mutations)
- ❌ Modify the original GitHub issue

**Workflow:**

```
/erk:plan-enrich <issue>
  ↓
Review enriched plan in conversation
  ↓
/erk:plan-save → New GitHub issue (enriched version)
```

## Usage

```bash
/erk:plan-enrich <issue-number>
```

**Examples:**

- `/erk:plan-enrich 456` - Fetch and enrich plan from issue #456
- `/erk:plan-enrich 123` - Fetch and enrich plan from issue #123

## Prerequisites

- A GitHub issue containing an implementation plan
- Current working directory must be in a git repository
- GitHub CLI (gh) must be installed and authenticated

## Architecture

```
/erk:plan-enrich (orchestrator)
  ↓
  ├─→ Validate prerequisites (git repo, gh auth)
  ├─→ Validate issue number argument
  ├─→ Fetch plan from GitHub issue via gh CLI
  ├─→ Launch plan-extractor agent (enriched mode)
  │     ↓
  │     Agent enriches plan with context + questions
  │     Agent returns markdown: # Plan: ... with Enrichment Details
  │     (Agent has NO Edit/Write tools - structurally safe)
  └─→ Present enriched plan via ExitPlanMode
```

---

## Command Instructions

You are executing the `/erk:plan-enrich` command. Follow these steps carefully:

### Step 1: Validate Prerequisites

@../../docs/erk/includes/planning/validate-prerequisites.md

### Step 2: Validate Issue Number Argument

The command requires an issue number as argument. Parse the command input to extract the issue number.

**Expected input format:** `/erk:plan-enrich <issue-number>`

**Validation:**

```bash
# Issue number must be a positive integer
if [[ ! "$issue_number" =~ ^[0-9]+$ ]]; then
    echo "❌ Error: Invalid issue number"
fi
```

**Error handling:**

If no issue number provided:

```
❌ Error: Issue number required

Usage: /erk:plan-enrich <issue-number>

Example: /erk:plan-enrich 456
```

If invalid format:

```
❌ Error: Invalid issue number: "[input]"

Issue number must be a positive integer.

Example: /erk:plan-enrich 456
```

### Step 3: Fetch Plan from GitHub Issue

Use GitHub CLI to fetch the issue body:

```bash
# Fetch issue body (the plan content)
plan_content=$(gh issue view "$issue_number" --json body --jq '.body')

# Fetch issue title for reference
issue_title=$(gh issue view "$issue_number" --json title --jq '.title')
```

**Validation:**

- Check that the issue exists
- Check that the body contains content (not empty)

**Error handling:**

If issue doesn't exist:

```
❌ Error: Issue #[number] not found

Verify the issue number and try again.
```

If issue body is empty:

```
❌ Error: Issue #[number] has no content

The issue body is empty. Ensure the issue contains an implementation plan.
```

### Step 4: Launch Plan-Extractor Agent (Enriched Mode)

Use the Task tool to launch the specialized agent with the fetched plan content:

```json
{
  "subagent_type": "plan-extractor",
  "description": "Enrich plan from GitHub issue",
  "prompt": "Enrich the implementation plan fetched from GitHub issue with semantic understanding.\n\nInput:\n{\n  \"mode\": \"enriched\",\n  \"plan_content\": \"[plan content from GitHub issue]\",\n  \"guidance\": \"\"\n}\n\nThe plan was fetched from GitHub issue #[issue_number]: [issue_title]\n\nYour job:\n1. Ask clarifying questions via AskUserQuestion tool\n2. Extract semantic understanding (8 categories) from the plan content\n3. Return markdown output with enrichment details.\n\nNote: This plan was fetched from a GitHub issue, not from conversation context. Extract what context you can from the plan content itself.\n\nExpected output: Markdown with # Plan: title, Enrichment Details section, and full enriched plan content.",
  "model": "haiku"
}
```

**What the agent does:**

1. Receives plan content from GitHub issue
2. Asks clarifying questions via AskUserQuestion tool
3. Extracts semantic understanding (8 categories) from plan content
4. Returns enriched markdown output

@../../docs/erk/includes/planning/plan-extractor-agent-restrictions.md

### Step 5: Present Enriched Plan via ExitPlanMode

After receiving the enriched plan from the agent, use the **ExitPlanMode** tool to present the plan to the user and store it in session logs.

**Critical:** This step makes the enriched plan available for subsequent `/erk:plan-save` command.

```
Call ExitPlanMode with the enriched markdown content from the agent.
```

The user will see the enriched plan in the conversation and can:

1. Review the enrichment
2. Run `/erk:plan-enrich [guidance]` again to iterate (using session-plan-enrich for session-based)
3. Run `/erk:plan-save` to save to a new GitHub issue

### Step 6: Display Summary

After presenting the plan, display a summary:

```
✅ Plan enriched and ready for review

**Source:** GitHub issue #[issue_number]: [issue_title]
**Enrichment:** [N] context categories extracted, [M] questions asked

**Next steps:**

Save enriched plan to new GitHub issue:
    /erk:plan-save

Iterate with additional guidance (session-based):
    /erk:session-plan-enrich "Add retry logic"

View original issue:
    gh issue view [issue_number]
```

## Error Scenarios

### Issue Not Found

```
❌ Error: Issue #[number] not found

Verify the issue number and repository. You can list issues with:
    gh issue list
```

### Agent Error

```
❌ Error: [agent error message]

The plan-extractor agent encountered an error during enrichment.
[Display agent error details]
```

### Empty Plan Content

```
❌ Error: Issue #[number] has no content

The issue body is empty. Ensure the issue contains an implementation plan.
```

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Fetching:**
✅ GitHub issue fetched successfully
✅ Issue body contains plan content

**Enrichment:**
✅ Plan-extractor agent enriches plan with context
✅ Clarifying questions asked (if needed)
✅ Semantic understanding extracted

**Presentation:**
✅ Enriched plan presented via ExitPlanMode
✅ Plan stored in session logs for subsequent commands
✅ Summary displayed with next steps

## Development Notes

**For maintainers:**

This command demonstrates the **issue-based enrichment pattern**:

1. Command fetches plan from external source (GitHub issue)
2. Command launches specialized agent for enrichment
3. Agent enriches plan (structurally safe)
4. Command presents via ExitPlanMode (enables composition)
5. User can iterate or save

**Related commands:**

- `/erk:session-plan-enrich [guidance]` - Enrich plan from current session
- `/erk:plan-save` - Save plan from session logs to GitHub issue

**Agent file:** `.claude/agents/erk/plan-extractor.md`
