---
description: Save plan from session logs to GitHub issue (no enrichment)
---

# /erk:plan-save

## Goal

**Save the latest implementation plan from session logs to a GitHub issue.**

This command saves whatever plan is currently in session logs - raw or enriched - to GitHub. It does NOT perform enrichment. Use `/erk:session-plan-enrich` or `/erk:plan-enrich` to enrich plans before saving.

**What this command does:**

- ✅ Extract latest plan from session logs (ExitPlanMode markers)
- ✅ Detect enrichment status (raw vs enriched)
- ✅ Create GitHub issue with plan content
- ✅ Display enrichment status in output

**What this command does NOT do:**

- ❌ No plan enhancement or enrichment (use `/erk:session-plan-enrich`)
- ❌ No interactive clarifying questions
- ❌ No semantic understanding extraction
- ❌ No guidance parameter

**What this command CANNOT do:**

- ❌ Edit files on current branch
- ❌ Implement code
- ❌ Make commits

**Workflow Options:**

```
# Quick raw save (fast path - ~2 seconds)
Create plan → ExitPlanMode → /erk:plan-save → GitHub issue

# Enriched save (opt-in enrichment)
Create plan → ExitPlanMode → /erk:session-plan-enrich → /erk:plan-save → GitHub issue
```

## Usage

```bash
/erk:plan-save
```

**Note:** This command takes no arguments. Use `/erk:session-plan-enrich [guidance]` to apply guidance before saving.

## Prerequisites

- An implementation plan must exist in session logs (created with ExitPlanMode)
- Current working directory must be in a git repository
- GitHub CLI (gh) must be installed and authenticated
- Repository must have issues enabled

## Architecture

```
/erk:plan-save (orchestrator)
  ↓
  ├─→ Validate prerequisites (git repo, gh auth)
  ├─→ Extract plan from session logs via kit CLI
  │     ↓
  │     dot-agent run erk save-plan-from-session --extract-only
  │     Returns JSON: {plan_content, title}
  ├─→ Detect enrichment status (check for "Enrichment Details" section)
  ├─→ Save plan to temp file
  ├─→ Call kit CLI: dot-agent run erk create-enriched-plan-from-context --plan-file
  │     ↓
  │     Kit CLI creates GitHub issue
  └─→ Display results with enrichment status
```

**No Agent Required:** This command does not launch any agents. It simply reads from session logs and creates a GitHub issue.

---

## Command Instructions

You are executing the `/erk:plan-save` command. Follow these steps carefully:

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

### Step 3: Detect Enrichment Status

Check whether the plan has been enriched by looking for the "Enrichment Details" section:

```bash
# Check for enrichment markers in plan content
if echo "$plan_content" | grep -q "## Enrichment Details"; then
    enrichment_status="Enriched"
    enrichment_note="This plan includes semantic context (8 categories)"
else
    enrichment_status="Raw"
    enrichment_note="This plan has no enrichment. Use /erk:session-plan-enrich before saving to add context."
fi
```

**Note:** The enrichment status is informational only - the plan is saved regardless.

### Step 4: Save Plan to Temporary File

Write plan content to a temporary file for kit CLI:

```bash
# Create temp file
temp_plan=$(mktemp)

# Write plan content
cat > "$temp_plan" <<'PLAN_EOF'
[plan_content from session logs]
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

Common causes:
- Repository has issues disabled
- Network connectivity issue
- GitHub API rate limit
```

### Step 6: Display Success Output

#### Substep 6a: Generate and Display Execution Summary

After receiving the successful response from the kit CLI, generate a concise summary:

```
**Execution Summary:**

[One sentence overview of what was accomplished]

- [Key bullet point 1]
- [Key bullet point 2]
- [Key bullet point 3]
```

**Implementation note:** Extract summary from the plan_content. Look for major sections, objectives, or implementation phases.

#### Substep 6b: Display Issue URL, Enrichment Status, and Next Steps

```
✅ Plan saved to GitHub issue

**Enrichment status:** [Enriched/Raw]
[enrichment_note]

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
```

**Formatting requirements:**

- Use `✅` for success indicator
- Bold `**Enrichment status:**`, `**Issue:**`, and `**Next steps:**`
- Show enrichment status prominently
- Show actual issue URL (clickable)
- Show actual issue number in commands (not `<issue-number>`)

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
✅ Implementation plan extracted from session logs (ExitPlanMode markers)
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
2. Command extracts plan from session logs (no agent)
3. Command detects enrichment status
4. Command creates GitHub issue
5. Command displays results

**No agent is required** - this is a pure orchestration command that delegates mechanical work to kit CLI.

**Related commands:**

- `/erk:session-plan-enrich [guidance]` - Enrich plan from session before saving
- `/erk:plan-enrich <issue>` - Enrich plan from GitHub issue

**Breaking change note:** This command previously included inline enrichment. That functionality has moved to `/erk:session-plan-enrich`. The old guidance parameter is no longer supported.
