# Plan: Extract Plan Path from Context in /erk:plan-save

## Problem

Multiple Claude sessions share `~/.claude/plans/`, so `get_latest_plan()` picks whichever plan was most recently modified, even if it's from a different session.

## Solution

The `/erk:plan-save` command should extract the plan path from the conversation context. When plan mode is active, the system prompt contains:

> `Plan File Info: A plan file already exists at /Users/schrockn/.claude/plans/purring-wiggling-biscuit.md`

Claude should extract this path and pass it to the kit CLI. The user doesn't need to pass anything - it just works.

## Changes Required

### 1. `plan_save_to_issue.py` - Add `--plan-file` option

```python
@click.option(
    "--plan-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to specific plan file (default: most recent in ~/.claude/plans/)",
)
def plan_save_to_issue(ctx, output_format, plan_file):
    if plan_file:
        plan = plan_file.read_text(encoding="utf-8")
    else:
        plan = get_latest_plan(str(cwd), session_id=None)
```

### 2. `/erk:plan-save` command - Auto-extract plan path from context

Update `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-save.md` to instruct Claude to:

1. Look for `Plan File Info:` in the conversation context
2. Extract the plan file path (e.g., `/Users/.../purring-wiggling-biscuit.md`)
3. Pass it to the kit CLI:

```bash
# Extract plan path from context, then call:
dot-agent run erk plan-save-to-issue --plan-file <extracted-path> --format json
```

4. If no plan path found in context, fall back to calling without `--plan-file`

## Files to Modify

1. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/plan_save_to_issue.py`
2. `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/plan-save.md`

## User Experience

- User just runs `/erk:plan-save` with no arguments
- Claude automatically extracts plan path from context
- Correct plan is saved even with multiple sessions running