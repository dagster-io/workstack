# Plan: Add --dangerous and --yolo options to craft-plan output

## Summary

Update the `/erk:craft-plan` command to display additional "Next steps" entries for dangerous and yolo implementation modes after a plan is saved to GitHub.

## Current State

The `craft-plan.md` command (lines 115-127) displays a hardcoded "Next steps" section:

```
✅ Plan created and saved to GitHub

**Issue:** [issue_url]

**Next steps:**

View the plan:
    gh issue view [issue_number] --web

Implement the plan:
    erk implement [issue_number]
```

## Desired Output

Add two additional entries after "Implement the plan":

```
✅ Plan created and saved to GitHub

**Issue:** [issue_url]

**Next steps:**

View the plan:
    gh issue view [issue_number] --web

Implement the plan:
    erk implement [issue_number]

Implement with plan with --dangerously-skip-permissions:
    erk implement [issue_number] --dangerous

Implement with plan with --dangerous and then submit as pr:
    erk implement [issue_number] --yolo
```

## Implementation

### File to Modify

`/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/craft-plan.md`

### Change

Update lines 115-127 to add the two new entries after the existing "Implement the plan" entry.