---
description: Force immediate status line refresh
---

# Refresh Status Line Command

This command forces an immediate refresh of Claude Code's status line display by triggering conversation activity.

## Usage

```
/refresh-statusline
```

## Purpose

Use this command to update the status line immediately after external changes such as:
- Git operations (branch changes, commits, etc.)
- Worktree switches
- Any operation that modifies repository state

Claude Code automatically refreshes the status line every 300ms during conversation activity. This command provides a way to force that refresh without waiting for natural conversation flow.

---

## Agent Instructions

Output the following minimal message to trigger the status line refresh:

```
🔄 Status line refreshed
```

Do NOT perform any other actions. This command is intentionally minimal to avoid cluttering the conversation.
