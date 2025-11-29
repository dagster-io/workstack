---
description: Clone an existing plan issue to a new issue with a new branch name
---

# /erk:plan-clone

## Goal

**Clone an existing plan issue to a new issue with a unique branch name, then close the original.**

This command enables quick recovery when a plan's worktree was deleted or the branch name collides, by creating a fresh copy with a new unique branch name while preserving the plan content.

**What this command does:**

- Fetch plan from source issue (title + plan-body from comment)
- Generate unique branch name with timestamp suffix (YYMMDD-HHMM format)
- Create NEW issue with same title and Schema V2 format
- Close original issue with comment linking to new issue
- Display success with new issue URL

**What this command CANNOT do:**

- Modify or enrich plan content during clone
- Keep the original issue open
- Clone closed issues

## Usage

```bash
/erk:plan-clone <issue-number>
```

**Arguments:**

- `<issue-number>` (required) - The source issue number to clone

**Examples:**

- `/erk:plan-clone 1346` - Clone plan from issue #1346 to a new issue

## Prerequisites

- Current working directory must be in a git repository
- GitHub CLI (gh) must be installed and authenticated
- Source issue must have `erk-plan` label
- Source issue must be OPEN

## Architecture

```
/erk:plan-clone (orchestrator)
  |
  |-> Validate prerequisites (git repo, gh auth)
  |-> Parse issue number from argument
  |-> Fetch source issue (title, state, labels, body)
  |-> Verify erk-plan label and OPEN state
  |-> Fetch plan content from first comment (plan-body block)
  |-> Generate new worktree name with timestamp suffix
  |-> Create new issue with Schema V2 format
  |-> Add plan-body comment to new issue
  |-> Close original issue with linking comment
  |-> Display success with new issue URL
```

---

## Command Instructions

You are executing the `/erk:plan-clone` command. Follow these steps carefully:

### Step 1: Validate Prerequisites

**Check git repository:**

```bash
git rev-parse --is-inside-work-tree 2>/dev/null || echo "NOT_GIT"
```

If output is "NOT_GIT":

```
Error: Not in a git repository

This command must be run from within a git repository.
```

**Check GitHub CLI authentication:**

```bash
gh auth status 2>&1 | head -5
```

If output contains "not logged in" or returns error:

```
Error: GitHub CLI not authenticated

To use this command, authenticate with GitHub:

    gh auth login

Then try again.
```

### Step 2: Parse Issue Number

Extract the issue number from the command argument.

**Validation:**

- Must be provided (no argument = error)
- Must be a positive integer

**Error handling:**

If no issue number provided:

```
Error: Issue number required

Usage: /erk:plan-clone <issue-number>

Example: /erk:plan-clone 1346
```

If invalid issue number:

```
Error: Invalid issue number '[value]'

Issue number must be a positive integer.

Usage: /erk:plan-clone <issue-number>
```

### Step 3: Fetch Source Issue

Use GitHub CLI to fetch the source issue:

```bash
# Fetch issue details as JSON
issue_data=$(gh issue view "$issue_number" --json title,state,labels,body)
```

Parse the JSON to extract:

- `title`: The issue title (will become the plan title)
- `state`: Must be "OPEN"
- `labels`: Must include "erk-plan"
- `body`: Contains the plan-header metadata block

**Error handling:**

If issue doesn't exist:

```
Error: Issue #[number] not found

Verify the issue number and try again.
```

### Step 4: Verify Prerequisites

**Check erk-plan label:**

```bash
has_label=$(echo "$issue_data" | jq -r '.labels[] | select(.name == "erk-plan") | .name' | head -1)
```

If label not found:

```
Error: Issue #[number] does not have erk-plan label

Only plan issues (with erk-plan label) can be cloned.
```

**Check OPEN state:**

```bash
state=$(echo "$issue_data" | jq -r '.state')
```

If state is not "OPEN":

```
Error: Issue #[number] is not open (state: [state])

Only open plan issues can be cloned. Use this command before the plan is implemented.
```

### Step 5: Fetch Plan Content from First Comment

The plan content is stored in the first comment (Schema V2 format).

```bash
# Fetch first comment
first_comment=$(gh api "repos/{owner}/{repo}/issues/$issue_number/comments" --jq '.[0].body // empty')
```

If no comment or empty:

```
Error: Issue #[number] has no plan content

The first comment should contain the plan-body metadata block.
```

**Extract plan content from plan-body block:**

The plan content is wrapped in a metadata block:

```
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>Implementation Plan</strong></summary>

[plan content here]

</details>
<!-- /erk:metadata-block:plan-body -->
```

Extract the content between the `<details>` tags (after the `<summary>` line).

If extraction fails:

```
Error: Could not extract plan content from issue #[number]

The first comment should contain a plan-body metadata block.
```

### Step 6: Generate New Worktree Name

Generate a unique worktree name by appending a timestamp suffix to the sanitized title.

**Timestamp format:** `-YYMMDD-HHMM` (e.g., `-251126-1430`)

**Process:**

1. Sanitize the issue title to get base worktree name
2. Append timestamp suffix

```bash
# Get current timestamp
timestamp=$(date +"%y%m%d-%H%M")

# The new worktree name will be: [sanitized-title]-[timestamp]
```

The sanitization follows the rules from `naming.py`:

- Lowercase
- Replace underscores with hyphens
- Replace non-alphanumeric characters with hyphens
- Collapse consecutive hyphens
- Strip leading/trailing hyphens
- Truncate to 31 characters if needed

### Step 7: Create New Issue with Schema V2 Format

Create the new issue with:

1. Same title as original
2. `erk-plan` label
3. Plan-header metadata block in body (with new worktree_name)

**Get current GitHub username:**

```bash
gh_user=$(gh api user --jq '.login')
```

**Get current timestamp:**

```bash
created_at=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
```

**Format the issue body (plan-header block):**

````markdown
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
schema_version: "2"
created_at: [created_at]
created_by: [gh_user]
worktree_name: [new_worktree_name]
last_dispatched_run_id: null
last_dispatched_at: null
```
````

</details>
<!-- /erk:metadata-block:plan-header -->
```

**Create the issue:**

```bash
# Write body to temp file
temp_body=$(mktemp)
cat > "$temp_body" <<'BODY_EOF'
[plan-header block content]
BODY_EOF

# Create issue with label
new_issue_url=$(gh issue create --title "$title" --body-file "$temp_body" --label "erk-plan")

# Extract issue number from URL
new_issue_number=$(echo "$new_issue_url" | grep -oE '[0-9]+$')

rm "$temp_body"
```

### Step 8: Add Plan Content Comment

Add the plan content as the first comment on the new issue:

```bash
# Write plan content to temp file (wrapped in plan-body block)
temp_comment=$(mktemp)
cat > "$temp_comment" <<'COMMENT_EOF'
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>Implementation Plan</strong></summary>

[extracted_plan_content]

</details>
<!-- /erk:metadata-block:plan-body -->
COMMENT_EOF

# Add comment to new issue
gh issue comment "$new_issue_number" --body-file "$temp_comment"

rm "$temp_comment"
```

### Step 8.5: Close Associated PR (if exists)

Check if there's an open PR associated with the original issue and close it before closing the issue.

**Derive branch name from title:**

The branch name is derived using the same logic as `sanitize_branch_component()` in `naming.py`:

```bash
# Derive branch name from title (matching naming.py logic)
branch_name=$(echo "$title" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._/-]/-/g' | sed 's/-\+/-/g' | sed 's/^[-\/]*//;s/[-\/]*$//')

# Truncate to 31 characters and strip trailing hyphens
if [ ${#branch_name} -gt 31 ]; then
    branch_name="${branch_name:0:31}"
    branch_name=$(echo "$branch_name" | sed 's/-*$//')
fi

# Use "work" if empty
if [ -z "$branch_name" ]; then
    branch_name="work"
fi
```

**Check if PR exists and close if open:**

```bash
# Check if PR exists for this branch
pr_check=$(gh pr view "$branch_name" --json state,number 2>&1)

if [ $? -eq 0 ]; then
    # PR exists - extract state and number
    pr_state=$(echo "$pr_check" | jq -r '.state')
    pr_number=$(echo "$pr_check" | jq -r '.number')

    if [ "$pr_state" = "OPEN" ]; then
        # Close the PR with explanatory comment
        gh pr close "$branch_name" --comment "Closing PR - issue cloned to #$new_issue_number with new worktree name: \`$new_worktree_name\`"
        echo "Closed associated PR #$pr_number for branch: $branch_name"
    else
        echo "Associated PR #$pr_number is already $pr_state (no action needed)"
    fi
else
    # No PR exists for this branch (this is normal)
    echo "No PR found for branch: $branch_name (continuing)"
fi
```

**Error handling:**

If the PR close operation fails, log a warning but continue with issue closure:

```bash
if ! gh pr close "$branch_name" --comment "..." 2>&1; then
    echo "Warning: Failed to close PR for branch $branch_name (continuing anyway)"
fi
```

### Step 9: Close Original Issue

Close the original issue with a comment linking to the new one:

```bash
# Add linking comment
gh issue comment "$issue_number" --body "Cloned to #$new_issue_number with new worktree name: \`$new_worktree_name\`"

# Close the original issue
gh issue close "$issue_number"
```

### Step 10: Display Success Output

```
Plan cloned successfully

**Original:** #[issue_number] (now closed)
**New issue:** #[new_issue_number]
**URL:** [new_issue_url]
**Worktree name:** [new_worktree_name]

**Next steps:**

View the new plan:
    gh issue view [new_issue_number]

Create worktree and implement:
    erk implement [new_issue_number]

Submit to erk queue:
    erk submit [new_issue_number]
```

## Error Scenarios

### Issue Not Found

```
Error: Issue #[number] not found

Verify the issue number and try again.
```

### Missing erk-plan Label

```
Error: Issue #[number] does not have erk-plan label

Only plan issues (with erk-plan label) can be cloned.
```

### Issue Not Open

```
Error: Issue #[number] is not open (state: [state])

Only open plan issues can be cloned. Use this command before the plan is implemented.
```

### No Plan Content

```
Error: Issue #[number] has no plan content

The first comment should contain the plan-body metadata block.
```

### GitHub API Error

```
Error: GitHub API error

[error details]

Check your authentication and network connection.
```

## Success Criteria

This command succeeds when ALL of the following are true:

**Validation:**

- Source issue exists and is accessible
- Source issue has `erk-plan` label
- Source issue is OPEN
- Source issue has plan content in first comment

**Cloning:**

- New issue created with same title
- New issue has `erk-plan` label
- New issue body contains plan-header with new worktree_name
- New issue first comment contains plan-body with exact plan content
- Original issue has linking comment
- Original issue is closed

**Output:**

- Success message displayed
- New issue URL shown
- New worktree name shown
- Next steps provided

## Development Notes

**For maintainers:**

This command demonstrates the **clone pattern**:

1. Validate source issue exists and meets prerequisites
2. Extract plan content from Schema V2 structure
3. Generate unique identifier (timestamp-based)
4. Create new issue preserving content structure
5. Link and close original for traceability

**Schema V2 Structure:**

- Issue body: Contains `plan-header` metadata block
- First comment: Contains `plan-body` metadata block with actual plan content

**Related commands:**

- `/erk:plan-save` - Save plan to NEW issue
- `/erk:plan-enrich` - Enrich plan in EXISTING issue
- `/erk:plan-save-enriched` - Enrich and save to NEW issue
