---
description: "[EXPERIMENTAL] Refine prompt and trigger remote planning via GitHub Actions"
---

# /erk:plan-remote

> **EXPERIMENTAL**: This command is experimental and may be removed.

## Goal

**Take a user's feature request, refine it with clarifying questions, and trigger remote planning.**

This command does lightweight prompt refinement locally (no codebase search), then triggers a GitHub Actions workflow where Claude will explore the codebase and create a detailed plan.

## Instructions

### Step 1: Get the User's Request

Ask the user what they want to build or implement. If they haven't provided a prompt yet, use AskUserQuestion:

"What feature or change would you like to plan? Provide a brief description."

### Step 2: Clarify (1-2 Questions Max)

Using your knowledge of the project from skills (dignified-python, fake-driven-testing), ask 1-2 clarifying questions. Examples:

- "Should this integrate with the existing X pattern or be standalone?"
- "Is this a CLI command, library function, or both?"
- "Should this include tests in the initial plan?"

**DO NOT search the codebase.** Use only skill knowledge.

### Step 3: Create Refined Prompt

Combine the user's request with clarifications into a refined prompt. Write to temp file:

```bash
cat > /tmp/refined-prompt.txt <<'EOF'
[Combined refined prompt here]
EOF
```

### Step 4: Trigger Remote Planning

```bash
erk plan create-remote /tmp/refined-prompt.txt
```

### Step 5: Report Success

```
Remote planning triggered!

**Workflow:** [URL from command output]

A new erk-plan issue will be created when planning completes.
You can monitor progress at the workflow URL above.
```
