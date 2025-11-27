---
description: Create a plan using Plan Mode and save to GitHub issue
---

# /erk:plan-create-v2

## Goal

**Create an implementation plan using Plan Mode, then automatically save to GitHub.**

This command orchestrates the full planning workflow:

1. Enter Plan Mode (leverage Claude's planning capabilities)
2. Create a structured implementation plan
3. Exit Plan Mode (plan saved to ~/.claude/plans/)
4. Save plan to GitHub issue automatically

## Command Instructions

You are executing `/erk:plan-create-v2`. Follow these phases:

### Phase 1: Enter Plan Mode

**IMMEDIATELY use the EnterPlanMode tool.**

Do not ask the user anything first. Just invoke EnterPlanMode now.

The user will approve the Plan Mode transition.

### Phase 2: Plan Creation (In Plan Mode)

Once in Plan Mode, ask the user:

> What would you like me to help you plan?

Then:

1. Explore the codebase to understand context
2. Ask clarifying questions as needed
3. Create a structured implementation plan
4. When the plan is complete, tell the user you're ready to save it

### Phase 3: Exit Plan Mode

When the user confirms the plan is ready, **use the ExitPlanMode tool**.

The plan will be saved to `~/.claude/plans/` automatically.

### Phase 4: Save to GitHub

**IMPORTANT: After ExitPlanMode completes, continue executing this command.**

Validate prerequisites:

- Verify git repository: `git rev-parse --is-inside-work-tree`
- Verify GitHub CLI: `gh auth status`

Save the plan to GitHub:

```bash
result=$(dot-agent run erk plan-save-to-issue --format json 2>&1)
```

Parse the result and display:

```
✅ Plan created and saved to GitHub

**Issue:** [issue_url]

**Next steps:**

View the plan:
    gh issue view [issue_number] --web

Implement the plan:
    erk implement [issue_number]
```

## Error Handling

If Phase 4 fails (e.g., command doesn't continue after ExitPlanMode):

```
Your plan has been saved to ~/.claude/plans/

To save it to GitHub, run:
    /erk:plan-save
```
