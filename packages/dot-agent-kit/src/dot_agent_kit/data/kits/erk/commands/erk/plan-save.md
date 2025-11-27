---
description: Save plan from ~/.claude/plans/ to GitHub issue (no enrichment)
model: haiku
---

# /erk:plan-save

## Goal

**Save the latest implementation plan from `~/.claude/plans/` to a GitHub issue.**

This command saves whatever plan is currently in the plans directory - raw or enriched - to GitHub. It does NOT perform enrichment. Use `/erk:plan-save-enriched` or `/erk:plan-enrich` to enrich plans.

**What this command does:**

- ✅ Extract latest plan from `~/.claude/plans/`
- ✅ Detect enrichment status (raw vs enriched)
- ✅ Create GitHub issue with plan content
- ✅ Display enrichment status in output

**What this command does NOT do:**

- ❌ No plan enhancement or enrichment (use `/erk:plan-save-enriched`)
- ❌ No interactive clarifying questions
- ❌ No semantic understanding extraction

**What this command CANNOT do:**

- ❌ Edit files on current branch
- ❌ Implement code
- ❌ Make commits

**Workflow Options:**

```
# Quick raw save (fast path - ~2 seconds)
Create plan → ExitPlanMode → /erk:plan-save → GitHub issue

# Enriched save (opt-in enrichment)
Create plan → ExitPlanMode → /erk:plan-save-enriched → GitHub issue
```

## Usage

```bash
/erk:plan-save
```

**Note:** This command takes no arguments. Use `/erk:plan-save-enriched` to enrich and save in one step.

## Prerequisites

- An implementation plan must exist in `~/.claude/plans/` (created with ExitPlanMode)
- Current working directory must be in a git repository
- GitHub CLI (gh) must be installed and authenticated
- Repository must have issues enabled

## Architecture

```
/erk:plan-save (orchestrator)
  ↓
  ├─→ Validate prerequisites (git repo, gh auth)
  ├─→ Call kit CLI: dot-agent run erk plan-save-to-issue --format json
  │     ↓
  │     ├─→ Extracts plan from ~/.claude/plans/
  │     ├─→ Creates GitHub issue (schema v2)
  │     └─→ Returns JSON: {issue_number, issue_url, title, enriched}
  └─→ Display results with enrichment status
```

**No Agent Required:** This command does not launch any agents. It simply reads from `~/.claude/plans/` and creates a GitHub issue via a single kit CLI call.

---

## Command Instructions

You are executing the `/erk:plan-save` command. Follow these steps carefully:

### Step 1: Validate Prerequisites

@../../docs/erk/includes/planning/validate-prerequisites.md

### Step 2: Extract Plan and Create GitHub Issue

Use the combined kit CLI command that extracts the plan and creates the issue in one step:

```bash
# Call the combined kit CLI command
result=$(dot-agent run erk plan-save-to-issue --format json 2>&1)
```

**Parse the result:**

```bash
# Check if command succeeded
if echo "$result" | jq -e '.success' > /dev/null 2>&1; then
    # SUCCESS - extract values
    issue_number=$(echo "$result" | jq -r '.issue_number')
    issue_url=$(echo "$result" | jq -r '.issue_url')
    title=$(echo "$result" | jq -r '.title')
    enriched=$(echo "$result" | jq -r '.enriched')

    # Set enrichment status message
    if [ "$enriched" = "true" ]; then
        enrichment_status="Enriched"
        enrichment_note="This plan includes semantic context (8 categories)"
    else
        enrichment_status="Raw"
        enrichment_note="This plan has no enrichment. Use /erk:plan-save-enriched to add context."
    fi
else
    # FAILURE - extract error message
    error_msg=$(echo "$result" | jq -r '.error // "Unknown error"')
    echo "❌ Error: $error_msg"
    exit 1
fi
```

**Expected success output:**

```json
{
  "success": true,
  "issue_number": 123,
  "issue_url": "https://github.com/owner/repo/issues/123",
  "title": "Plan Title",
  "enriched": false
}
```

**Error handling:**

The kit CLI returns JSON with error details on failure:

```json
{
  "success": false,
  "error": "No plan found in ~/.claude/plans/"
}
```

Common error causes:

- No plan in `~/.claude/plans/` directory
- Repository has issues disabled
- Network connectivity issue
- GitHub API rate limit

### Step 3: Display Success Output

Display the issue URL, enrichment status, and next steps:

```
✅ Plan saved to GitHub issue

**Enrichment status:** [Enriched/Raw]
[enrichment_note]

**Issue:** [issue_url]

@../../docs/erk/includes/planning/next-steps-output.md
```

Where `[OPTIONAL_COMMANDS]` in the include expands to:

```
Submit plan to erk queue:
    erk submit [issue_number]
```

**Formatting requirements:**

- Use `✅` for success indicator
- Bold `**Enrichment status:**`, `**Issue:**`, and `**Next steps:**`
- Show enrichment status prominently
- Show actual issue URL (clickable)
- Show actual issue number in commands (not `<issue-number>`)

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

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Extraction:**
✅ Implementation plan extracted from `~/.claude/plans/`
✅ Kit CLI extraction returns valid JSON with plan_content
✅ Enrichment status detected correctly

**Issue Creation:**
✅ GitHub issue created with plan content
✅ Issue has `erk-plan` label applied
✅ Issue title matches plan title

**Output:**
✅ Enrichment status displayed
✅ JSON output provided with issue URL and number
✅ Copy-pastable commands displayed (view + implement variants)
✅ All commands use actual issue number, not placeholders
✅ Next steps clearly communicated to user

## Development Notes

**For maintainers:**

This command demonstrates the **raw save pattern**:

1. Command validates prerequisites
2. Command extracts plan from `~/.claude/plans/` (no agent)
3. Command detects enrichment status
4. Command creates GitHub issue
5. Command displays results

**No agent is required** - this is a pure orchestration command that delegates mechanical work to kit CLI.

**Related commands:**

- `/erk:plan-save-enriched` - Enrich plan and save to new issue in one step
- `/erk:plan-enrich <issue>` - Enrich plan from GitHub issue and update in place
