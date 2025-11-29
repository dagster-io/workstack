# Plan: Rename erk:plan-craft to erk:craft-plan

## Summary

Rename the command from `erk:plan-craft` to `erk:craft-plan` for consistency with verb-noun naming.

## Changes Required

### 1. Rename the command file
- **From**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-craft.md`
- **To**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/craft-plan.md`

### 2. Update internal references in the command file
- Line 5: `# /erk:plan-craft` → `# /erk:craft-plan`
- Line 20: `` You are executing `/erk:plan-craft` `` → `` You are executing `/erk:craft-plan` ``

### 3. Update the symlink
- **Delete**: `.claude/commands/erk/plan-craft.md`
- **Create**: `.claude/commands/erk/craft-plan.md` → `../../../packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/craft-plan.md`

## No other references found
- No documentation files reference this command
- No Python source files reference this command
- No config files reference this command