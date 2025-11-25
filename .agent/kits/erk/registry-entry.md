### erk (v0.3.1)

**Purpose**: Erk implementation workflow commands for creating worktrees from plans (.PLAN.md) and executing implementation. Includes commands for plan creation, execution, and quick access.

**Artifacts**:

- command: commands/erk/plan-save.md, commands/erk/plan-save-raw.md, commands/erk/plan-implement.md, commands/erk/merge-conflicts-fix.md, commands/erk/plan-submit.md
- agent: agents/erk/issue-wt-creator.md
- doc: docs/erk/EXAMPLES.md

**Usage**:

- Use Task tool with subagent_type="erk"
- Run `/erk` command
