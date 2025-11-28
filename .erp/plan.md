# Plan: Rename v2-plan-create.md to plan-craft.md

## Summary

Rename the erk command file from `v2-plan-create.md` to `plan-craft.md` and update the symlink.

## Changes Required

1. **Rename source file**:
   - From: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/v2-plan-create.md`
   - To: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-craft.md`

2. **Update internal references**: Change `/erk:v2-plan-create` to `/erk:plan-craft` within the file

3. **Update symlink in `.claude/commands/erk/`**:
   - Remove: `v2-plan-create.md` symlink
   - Create: `plan-craft.md` → `../../../packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-craft.md`

## Implementation Steps

1. Create new file `plan-craft.md` with updated content (replace `v2-plan-create` → `plan-craft`)
2. Delete old file `v2-plan-create.md`
3. Remove old symlink `.claude/commands/erk/v2-plan-create.md`
4. Create new symlink `.claude/commands/erk/plan-craft.md` using relative path pattern