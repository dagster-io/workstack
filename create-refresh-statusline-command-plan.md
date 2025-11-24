## Create `/refresh-statusline` Command

**Objective:** Create a minimal slash command that triggers Claude Code's automatic status line refresh mechanism.

**Background:** 
- Claude Code refreshes the status line automatically every 300ms when conversation activity occurs
- No programmatic API exists to force a refresh
- Solution: Output a minimal message to trigger conversation activity, which causes the automatic refresh

**Implementation:**

Create single file: `.claude/commands/refresh-statusline.md`

**File structure:**
1. **Frontmatter** - Description for command listing
2. **User Documentation** - Explains purpose and usage
3. **Agent Instructions** - Directs agent to output minimal message

**Command behavior:**
- Invoked via `/refresh-statusline`
- Outputs: `🔄 Status line refreshed` 
- Intentionally minimal to avoid conversation clutter
- Triggers 300ms automatic refresh mechanism

**Use case:** Force immediate status line update after external changes (git operations, worktree switches, branch changes) without waiting for natural conversation flow.

**Files to create:**
- `.claude/commands/refresh-statusline.md` (follows kebab-case convention)

**No other changes needed** - Self-contained command leveraging existing Claude Code behavior.