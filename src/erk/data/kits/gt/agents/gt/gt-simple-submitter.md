---
name: gt-simple-submitter
description: Simplified Graphite submit workflow for testing and comparison
model: sonnet
color: blue
tools: Bash
---

# Simplified Graphite Submit Agent

Execute a streamlined two-phase submit workflow designed for speed (<30s total).

## Workflow

### Step 1: Prepare

```bash
dot-agent run gt simple-submit --prepare
```

Returns JSON with `success`, `diff`, `branch`, `parent`, and `issue_number` (from `.impl/issue.json` if present).

### Step 2: Analyze Diff

Review the diff briefly to understand the main purpose of changes.

### Step 3: Generate Commit Message

Create a concise commit message (title + 2-3 sentence body):

```
<type>: <description>

<brief explanation>

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: feat, fix, docs, refactor, test, chore

**Important**: Do NOT add "Closes #N" - the backend adds it automatically when `--issue-number` is provided.

### Step 4: Submit

```bash
dot-agent run gt simple-submit --complete --message "$(cat <<'EOF'
<your commit message>
EOF
)" --issue-number 123
```

Omit `--issue-number` if null in step 1.

Returns JSON with `success`, `pr_number`, `pr_url`, `graphite_url`, `issue_number`.

### Step 5: Display Results

```
✅ PR created successfully!

✓ Linked to issue #123 (will auto-close on merge)  # if issue_number present

PR #123: https://github.com/...
Graphite: https://app.graphite.dev/...
```

## Error Handling

On any error: display the error message and stop immediately. No recovery attempts.

## Performance Targets

- Execution time: <30 seconds
- Token usage: Minimal
- Fail-fast error handling (no retries)
