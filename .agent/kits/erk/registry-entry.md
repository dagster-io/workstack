### erk (v0.3.0)

**Purpose**: Erk implementation workflow commands for creating worktrees from plans (.PLAN.md) and executing implementation. Includes commands for plan creation, execution, and quick access.

**Artifacts**:

- command: commands/erk/save-plan-issue.md, commands/erk/save-raw-plan-issue.md, commands/erk/create-wt-from-plan-file.md, commands/erk/implement-plan.md, commands/erk/fix-merge-conflicts.md
- agent: agents/erk/issue-wt-creator.md
- doc: docs/erk/EXAMPLES.md

**Usage**:

- Use Task tool with subagent_type="erk"
- Run `/erk` command
