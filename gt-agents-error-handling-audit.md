# GT Agents Error Handling Audit

**Date**: 2025-11-22
**Purpose**: Review all gt kit agents for ambiguous error guidance that might lead to automatic conflict resolution attempts

## Agents Reviewed

### 1. gt-branch-submitter

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/agents/gt/gt-branch-submitter.md`

**Issue**: Critical - Ambiguous error guidance for conflict resolution

**Severity**: CRITICAL (Fixed)

**Description**:
- Agent had detailed error resolution commands that were interpreted as executable actions
- No prominent "STOP" instructions at beginning of error handling
- Error handlers provided resolution commands without explicit "user must run" language
- The prohibition against auto-resolution (old line 332) was buried and easily overlooked

**Recommended Fix**: COMPLETED ✅
- Added prominent "STOP and Display" section before error handlers
- Reformatted all three error types (squash_conflict, submit_conflict, submit_merged_parent)
- Added "Conflict Resolution Policy" section with explicit prohibitions
- All error handlers now clearly state "The agent will NOT..." and "you must do this manually"

**Error Handlers Updated**:
1. `submit_merged_parent` - Now clearly states agent will NOT run sync commands
2. `squash_conflict` - Now clearly states agent will NOT resolve conflicts
3. `submit_conflict` - Now clearly states agent will NOT resolve conflicts, provides two prioritized options

---

### 2. gt-update-pr-submitter

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/agents/gt/gt-update-pr-submitter.md`

**Issue**: Moderate - Could benefit from enhanced format but not critically ambiguous

**Severity**: MODERATE

**Description**:
- Has simpler error handling structure (lines 52-89)
- The `restack_failed` error handler says "Resolve conflicts manually" (line 78) which is good
- However, lacks the prominent "STOP" instructions and explicit policy section
- Could be enhanced to match the new standard for consistency

**Current Format** (`restack_failed` at lines 74-81):
```markdown
For `restack_failed`:

❌ Conflicts occurred during restack

Resolve conflicts manually, then run this command again:
  /gt:update-pr
```

**Recommended Enhancement**:
- Add "STOP and Display" section similar to gt-branch-submitter
- Add "Conflict Resolution Policy" section
- Enhance error handlers to use new format:
  - "What happened" section
  - "What you need to do" section with explicit "you must do this manually" language
  - "The agent will NOT..." statement at the end

**Priority**: MEDIUM - Should be updated for consistency and to prevent future issues

---

## Summary

**Total Agents Reviewed**: 2

**Critical Issues**: 1 (gt-branch-submitter - FIXED ✅)

**Moderate Issues**: 1 (gt-update-pr-submitter - needs enhancement)

**Minor Issues**: 0

**No Issues**: 0

## Recommendations

1. **Immediate** (COMPLETED ✅): Fix gt-branch-submitter agent with enhanced error handling format
2. **Short-term**: Update gt-update-pr-submitter to match the new standard for consistency
3. **Long-term**: Create error handling standard documentation to guide future agent development
4. **Testing**: Manually test both agents with conflict scenarios to verify correct behavior

## Key Learnings

1. **LLMs interpret detailed commands as executable actions** unless explicitly marked otherwise
2. **"STOP" instructions must be prominent** and appear before detailed error handlers
3. **Prohibition statements must be repeated** in context, not just stated once at the end
4. **"User must run" language** is critical to prevent ambiguity
5. **Consistency across agents** helps establish patterns that LLMs recognize

## Standard Error Handler Format (Established)

Based on the improvements made to gt-branch-submitter, the standard format is:

### Section 1: STOP and Display (before all error handlers)
```markdown
## 🔴 CRITICAL: When Errors Occur - STOP and Display

**Your role when any step fails:**

1. ⛔ **STOP EXECUTION** - Do not attempt to fix the error
2. 📋 **PARSE THE ERROR** - Understand what failed from the JSON response
3. 💬 **DISPLAY TO USER** - Show the error message and resolution steps
4. ⏸️ **WAIT FOR USER** - Let the user take action and decide next steps
5. 🚫 **NEVER AUTO-RETRY** - Do not execute resolution commands yourself

**All resolution commands shown in error handlers are for the USER to run manually.**

You are an orchestrator, not a problem-solver. When things fail, inform the user and stop.
```

### Section 2: Conflict Resolution Policy
```markdown
## 🔴 Conflict Resolution Policy

**The agent will NEVER attempt to resolve conflicts automatically.**

This is a hard rule with no exceptions:

- ⛔ Do NOT execute git commands to resolve conflicts
- ⛔ Do NOT execute gt commands to fix merge issues
- ⛔ Do NOT execute erk commands to sync or rebase
- ⛔ Do NOT attempt to parse conflicts and suggest resolutions
- ⛔ Do NOT retry failed operations automatically

**When conflicts occur:** Display the error, show resolution steps, and STOP.

**Why this matters:** Automated conflict resolution can cause:
- Data loss from incorrect merge decisions
- Broken code from wrong conflict choices
- Security issues from merging incompatible changes
- Lost work from overwriting user edits

Manual resolution by a human ensures correctness and safety.
```

### Section 3: Individual Error Handlers
```markdown
#### `error_type` Error

❌ **Brief error description**

**What happened:** Explanation of what went wrong

**What you need to do:**

The agent has stopped and is waiting for you to resolve this. Follow these steps:

1. **Action description** (you must do this manually):
   ```bash
   command to run
   ```

2. **Next action** after completion

**The agent will NOT attempt to [specific action] for you.** Explanation of why manual action is required.
```

## Next Steps

1. ✅ Document this standard in formal documentation (Step 7)
2. ⬜ Consider updating gt-update-pr-submitter to match this standard
3. ⬜ Test both agents with conflict scenarios (Step 8)
4. ⬜ Review any future agents or updates against this standard
