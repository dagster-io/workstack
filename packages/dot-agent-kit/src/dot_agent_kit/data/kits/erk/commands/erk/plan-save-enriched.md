---
description: Enrich plan from context and save to new GitHub issue
---

# /erk:plan-save-enriched

## Goal

**Take a plan from `~/.claude/plans/`, enrich it with semantic understanding, and save to a new GitHub issue.**

This command combines the enrichment and save steps for plans already in context (from `~/.claude/plans/`).

**What this command does:**

- ✅ Extract plan from `~/.claude/plans/` (created via ExitPlanMode)
- ✅ Interactively enhance plan for autonomous execution
- ✅ Extract semantic understanding and context (8 categories)
- ✅ Present enriched plan for user review in conversation
- ✅ Save enriched plan to a **NEW** GitHub issue (after confirmation)

**What this command CANNOT do:**

- ❌ Edit files on current branch (structurally impossible - agent lacks tools)
- ❌ Implement code (agent has no Write/Edit capabilities)
- ❌ Make commits (agent restricted from git mutations)

**Workflow:**

```
[Plan already in ~/.claude/plans/ from ExitPlanMode]
  ↓
/erk:plan-save-enriched
  ↓
Agent asks clarifying questions
  ↓
Enriched plan displayed for review
  ↓
User confirms → NEW GitHub issue created
```

**Comparison with related commands:**

| Command                    | Source             | Enrichment | Destination       |
| -------------------------- | ------------------ | ---------- | ----------------- |
| `/erk:plan-enrich [issue]` | GitHub issue #X    | ✅         | Updates issue #X  |
| `/erk:plan-save-enriched`  | `~/.claude/plans/` | ✅         | Creates NEW issue |
| `/erk:plan-save`           | `~/.claude/plans/` | ❌         | Creates NEW issue |

## Usage

```bash
/erk:plan-save-enriched
```

**Note:** This command takes no arguments. It reads the plan from `~/.claude/plans/`.

## Prerequisites

- An implementation plan must exist in `~/.claude/plans/` (created with ExitPlanMode)
- Current working directory must be in a git repository
- GitHub CLI (gh) must be installed and authenticated

## Architecture

```
/erk:plan-save-enriched (orchestrator)
  ↓
  ├─→ Validate prerequisites (git repo, gh auth)
  ├─→ Extract plan from ~/.claude/plans/ via kit CLI
  │     ↓
  │     dot-agent run erk save-plan-from-session --extract-only
  │     Returns JSON: {plan_content, title}
  ├─→ Launch plan-extractor agent (enriched mode)
  │     ↓
  │     Agent enriches plan with context + questions
  │     Agent returns markdown: # Plan: ... with Enrichment Details
  │     (Agent has NO Edit/Write tools - structurally safe)
  ├─→ Display enriched plan in conversation for review
  ├─→ Ask user for confirmation (AskUserQuestion)
  └─→ Save enriched plan to NEW GitHub issue
```

---

## Command Instructions

You are executing the `/erk:plan-save-enriched` command. Follow these steps carefully:

### Step 1: Validate Prerequisites

@../../docs/erk/includes/planning/validate-prerequisites.md

### Step 2: Extract Plan from Plans Directory

@../../docs/erk/includes/planning/extract-plan-from-session.md

### Step 3: Launch Plan-Extractor Agent (Enriched Mode)

@../../docs/erk/includes/planning/launch-plan-extractor-agent.md

### Step 4: Display Enriched Plan for Review

@../../docs/erk/includes/planning/display-enriched-plan.md

**Source description:** `Plan from ~/.claude/plans/`

### Step 5: Ask User for Confirmation

Use the **AskUserQuestion** tool to confirm before creating a new GitHub issue:

```json
{
  "questions": [
    {
      "question": "Save this enriched plan to a new GitHub issue?",
      "header": "Save plan",
      "options": [
        {
          "label": "Yes, save to GitHub",
          "description": "Create a new GitHub issue with the enriched plan"
        },
        {
          "label": "No, cancel",
          "description": "Do not save - you can copy the plan above if needed"
        }
      ],
      "multiSelect": false
    }
  ]
}
```

**If user selects "No, cancel":**

```
Plan not saved. The enriched plan is displayed above for reference.

To save without enrichment:
    /erk:plan-save

To re-run enrichment:
    /erk:plan-save-enriched
```

Then STOP - do not proceed to Step 6.

**If user selects "Yes, save to GitHub":** Proceed to Step 6.

### Step 6: Save Enriched Plan to GitHub Issue

Create a new GitHub issue with the enriched plan content:

```bash
# Write enriched plan to temp file
temp_plan=$(mktemp)
cat > "$temp_plan" <<'PLAN_EOF'
[enriched plan content from agent]
PLAN_EOF

# Create GitHub issue
gh issue create \
  --title "[plan title from enriched plan]" \
  --body-file "$temp_plan" \
  --label "erk-plan"

# Clean up
rm "$temp_plan"
```

**Extract the new issue number and URL from the output.**

**Error handling:**

If issue creation fails:

```
❌ Error: Failed to create GitHub issue

[gh error output]

Common causes:
- Repository has issues disabled
- Network connectivity issue
- GitHub API rate limit
```

### Step 7: Display Success Summary

```
✅ Enriched plan saved to GitHub

**Issue:** #[issue_number]: [issue_title]
**URL:** [issue_url]
**Enrichment:** [N] context categories extracted, [M] questions asked

**Next steps:**

View the plan:
    gh issue view [issue_number]

Implement the plan:
    erk implement [issue_number]

Implement with auto-confirmation (yolo mode):
    erk implement [issue_number] --yolo

Re-enrich the plan (update in place):
    /erk:plan-enrich [issue_number]
```

## Error Scenarios

### No Plan Found

```
❌ Error: No plan found in ~/.claude/plans/

This command requires a plan created with ExitPlanMode. To fix:

1. Create a plan (enter Plan mode if needed)
2. Exit Plan mode using the ExitPlanMode tool
3. Run this command again

The plan will be extracted from ~/.claude/plans/ automatically.
```

### Agent Error

```
❌ Error: [agent error message]

The plan-extractor agent encountered an error during enrichment.
[Display agent error details]
```

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Extraction:**
✅ Implementation plan extracted from `~/.claude/plans/`
✅ Kit CLI extraction returns valid JSON with plan_content

**Enrichment:**
✅ Plan-extractor agent enriches plan with context
✅ Clarifying questions asked (if needed)
✅ Semantic understanding extracted

**Review:**
✅ Enriched plan displayed in conversation
✅ User confirmation obtained via AskUserQuestion

**Saving:**
✅ New GitHub issue created with enriched plan
✅ Issue has `erk-plan` label applied
✅ Success summary displayed with next steps

## Development Notes

**For maintainers:**

This command demonstrates the **context-to-issue enrichment pattern**:

1. Command extracts plan from `~/.claude/plans/`
2. Command launches specialized agent for enrichment
3. Agent enriches plan (structurally safe)
4. Command displays enriched plan for user review
5. Command asks user for confirmation
6. Command creates NEW GitHub issue

**Key design choice:** This command takes a plan from context (not GitHub) and saves to a NEW issue. Use `/erk:plan-enrich [issue]` if you want to enrich an existing issue and update it in place.

**Related commands:**

- `/erk:plan-enrich [issue]` - Fetch from GitHub issue, enrich, UPDATE same issue
- `/erk:plan-save` - Save plan from `~/.claude/plans/` to GitHub issue (no enrichment)

**Agent file:** `.claude/agents/erk/plan-extractor.md`
