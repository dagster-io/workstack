# Plan: Rename clear-todos to todos-clear

## Summary

Rename the slash command from `/clear-todos` to `/todos-clear`.

## Changes

### 1. Rename the file

```
.claude/commands/clear-todos.md → .claude/commands/todos-clear.md
```

### 2. Update internal references

Update the command name inside the file:

- Line 5: `# /clear-todos` → `# /todos-clear`
- Line 12: `/clear-todos` → `/todos-clear`

## Files to Modify

- `.claude/commands/clear-todos.md` (rename to `todos-clear.md` and update contents)
