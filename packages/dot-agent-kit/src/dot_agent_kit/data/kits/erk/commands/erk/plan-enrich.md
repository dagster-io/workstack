---
description: Enrich plan from GitHub issue and update it in place
---

# /erk:plan-enrich

## Goal

**Fetch an implementation plan from a GitHub issue, enrich it with semantic understanding, and update the same issue in place.**

This command enables plan refinement by fetching a plan from GitHub, enriching it with context extraction, and updating the original issue with the enriched version.

**What this command does:**

- ✅ Fetch plan content from GitHub issue
- ✅ Interactively enhance plan for autonomous execution
- ✅ Extract semantic understanding and context (8 categories)
- ✅ Present enriched plan for user review in conversation
- ✅ **Update the SAME GitHub issue** with enriched content (after confirmation)

**What this command CANNOT do:**

- ❌ Edit files on current branch (structurally impossible - agent lacks tools)
- ❌ Implement code (agent has no Write/Edit capabilities)
- ❌ Make commits (agent restricted from git mutations)

**Workflow:**

```
/erk:plan-enrich [issue]    ← issue number optional (uses context if omitted)
  ↓
Agent asks clarifying questions
  ↓
Enriched plan displayed for review
  ↓
User confirms → Issue #[issue] UPDATED in place
```

## Usage

```bash
/erk:plan-enrich [issue-number]
```

**Examples:**

- `/erk:plan-enrich 456` - Fetch and enrich plan from issue #456
- `/erk:plan-enrich` - Use the most recently mentioned issue from conversation context

## Prerequisites

- A GitHub issue containing an implementation plan
- Current working directory must be in a git repository
- GitHub CLI (gh) must be installed and authenticated

## Architecture

```
/erk:plan-enrich (orchestrator)
  ↓
  ├─→ Validate prerequisites (git repo, gh auth)
  ├─→ Resolve issue number (argument or conversation context)
  ├─→ Fetch plan from GitHub issue via gh CLI
  ├─→ Launch plan-extractor agent (enriched mode)
  │     ↓
  │     Agent enriches plan with context + questions
  │     Agent returns markdown: # Plan: ... with Enrichment Details
  │     (Agent has NO Edit/Write tools - structurally safe)
  ├─→ Display enriched plan in conversation for review
  ├─→ Ask user for confirmation (AskUserQuestion)
  └─→ UPDATE the SAME GitHub issue with enriched content
```

---

## Command Instructions

You are executing the `/erk:plan-enrich` command. Follow these steps carefully:

### Step 1: Validate Prerequisites

@../../docs/erk/includes/planning/validate-prerequisites.md

### Step 2: Resolve Issue Number

Determine the issue number from argument or conversation context.

**Resolution order:**

1. **Explicit argument** - If `/erk:plan-enrich 456` was invoked, use `456`
2. **Conversation context** - If no argument, check if a GitHub issue was recently created or discussed in this session (look for issue numbers like `#1259` or `issue 1259` mentioned in recent messages)
3. **Error** - If neither available, show error

**Resolution logic:**

```
1. Parse command arguments for issue number
2. If no argument provided:
   a. Search conversation context for recently mentioned GitHub issue numbers
   b. Look for patterns like "#1259", "issue #1259", "Issue 1259",
      "created issue 1259", "gh issue view 1259"
   c. Use the most recently mentioned issue number
3. Validate the resolved number is a positive integer
```

**When using context:**

Display confirmation before proceeding:

```
📋 Using issue #[number] from conversation context

Proceeding to fetch and enrich...
```

**Error handling:**

If no issue number provided AND none found in context:

```
❌ Error: Issue number required

No issue number was provided and none found in conversation context.

Usage: /erk:plan-enrich <issue-number>

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

@../../docs/erk/includes/planning/launch-plan-extractor-agent.md

### Step 5: Display Enriched Plan for Review

@../../docs/erk/includes/planning/display-enriched-plan.md

**Source description:** `GitHub issue #[issue_number]: [issue_title]`

### Step 6: Ask User for Confirmation

Use the **AskUserQuestion** tool to confirm before updating the GitHub issue:

```json
{
  "questions": [
    {
      "question": "Update issue #[issue_number] with this enriched plan?",
      "header": "Update issue",
      "options": [
        {
          "label": "Yes, update issue",
          "description": "Replace the issue body with the enriched plan"
        },
        {
          "label": "No, cancel",
          "description": "Do not update - you can copy the plan above if needed"
        }
      ],
      "multiSelect": false
    }
  ]
}
```

**If user selects "No, cancel":**

```
Issue not updated. The enriched plan is displayed above for reference.

To re-run enrichment:
    /erk:plan-enrich [issue_number]
```

Then STOP - do not proceed to Step 7.

**If user selects "Yes, update issue":** Proceed to Step 7.

### Step 7: Update GitHub Issue with Enriched Plan

Update the **same** GitHub issue with the enriched plan content:

```bash
# Write enriched plan to temp file
temp_plan=$(mktemp)
cat > "$temp_plan" <<'PLAN_EOF'
[enriched plan content from agent]
PLAN_EOF

# Update the existing GitHub issue
gh issue edit "$issue_number" --body-file "$temp_plan"

# Clean up
rm "$temp_plan"
```

**Note:** This updates the issue in place, preserving the issue number, URL, comments, and labels.

**Error handling:**

If issue update fails:

```
❌ Error: Failed to update GitHub issue #[issue_number]

[gh error output]

Common causes:
- Insufficient permissions to edit the issue
- Network connectivity issue
- GitHub API rate limit
```

### Step 8: Display Success Summary

```
✅ Issue #[issue_number] updated with enriched plan

**Issue:** #[issue_number]: [issue_title]
**URL:** [issue_url]
**Enrichment:** [N] context categories extracted, [M] questions asked

@../../docs/erk/includes/planning/next-steps-output.md
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

**Review:**
✅ Enriched plan displayed in conversation
✅ User confirmation obtained via AskUserQuestion

**Updating:**
✅ Original GitHub issue updated with enriched plan
✅ Issue number, URL, comments, and labels preserved
✅ Success summary displayed with next steps

## Development Notes

**For maintainers:**

This command demonstrates the **in-place enrichment pattern**:

1. Command fetches plan from GitHub issue
2. Command launches specialized agent for enrichment
3. Agent enriches plan (structurally safe)
4. Command displays enriched plan for user review
5. Command asks user for confirmation
6. Command **updates the same issue** with enriched content

**Key design choice:** This command updates the issue in place rather than creating a new one. This preserves issue number, URL, comments, labels, and any other metadata.

**Related commands:**

- `/erk:plan-save-enriched` - Enrich plan from `~/.claude/plans/` and save to NEW issue
- `/erk:plan-save` - Save plan from `~/.claude/plans/` to GitHub issue (no enrichment)

**Agent file:** `.claude/agents/erk/plan-extractor.md`
