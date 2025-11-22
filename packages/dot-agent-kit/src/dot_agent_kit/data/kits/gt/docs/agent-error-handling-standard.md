# Agent Error Handling Standard

**Version**: 1.0
**Date**: 2025-11-22
**Applies to**: All workflow agents that execute git/gt/erk operations

## Philosophy

### Why Agents Must Stop on Errors

Workflow agents orchestrate operations but should NEVER attempt to resolve errors automatically, especially conflicts or merge issues. Here's why:

**The Problem:**
- LLMs interpret detailed command examples as executable actions unless explicitly told otherwise
- Error handlers that provide resolution steps can be misinterpreted as "do this now"
- Prohibition statements buried in documentation are easily overlooked during error handling

**The Solution:**
- Clear separation between agent actions and user actions
- Prominent "STOP" instructions before error handlers
- Explicit "user must run" language for all resolution commands
- Repeated prohibitions in context, not just stated once

**The Risk of Auto-Resolution:**
- **Data loss** from incorrect merge decisions
- **Broken code** from wrong conflict choices
- **Security issues** from merging incompatible changes
- **Lost work** from overwriting user edits

Manual resolution by a human ensures correctness and safety.

## Standard Format

### Section 1: STOP and Display Instructions

Place this section BEFORE individual error handlers, right after general error handling introduction:

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

**Why this works:**
- Numbered steps make it clear this is a sequential process
- Emoji markers make it visually distinct and memorable
- Final statement reinforces the orchestrator role
- Placed before error handlers so it's seen first

### Section 2: Conflict Resolution Policy

Add this section immediately after the STOP instructions, before specific error handlers:

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

**Why this works:**
- Explicit list of forbidden actions prevents creative reinterpretation
- "Why this matters" reinforces the importance with concrete consequences
- Appears twice (STOP section + dedicated policy) for emphasis
- Adapt the list of forbidden commands to your agent's tools

### Section 3: Individual Error Handlers

Use this template for each error type:

```markdown
#### `error_type` Error

❌ **Brief error description in bold**

**What happened:** Clear explanation of what went wrong and why

**What you need to do:**

The agent has stopped and is waiting for you to resolve this. Follow these steps:

1. **Action description** (you must do this manually):
   ```bash
   command to run
   ```

2. **Follow-up action** after first step completes

3. **Final action**, re-run the workflow:
   ```bash
   /command-name <args>
   ```

**The agent will NOT attempt to [specific action] for you.** Brief explanation of why manual action is required.
```

**Key elements:**

1. **Error emoji (❌)**: Visual indicator of error state
2. **Brief bold description**: Immediately communicates what failed
3. **"What happened" section**: Explains the error in user-friendly terms
4. **"What you need to do" section**:
   - States "agent has stopped and is waiting"
   - Lists explicit steps with "you must do this manually"
   - Uses numbered steps for clarity
   - Provides exact commands to run
5. **Final prohibition**: Restates agent will NOT do this action
   - Reinforces the boundary
   - Explains WHY manual action is important

### For Multiple Resolution Options

When there are multiple valid approaches, format like this:

```markdown
#### `error_type` Error

❌ **Brief error description**

**What happened:** Explanation of what went wrong

**What you need to do:**

The agent has stopped and is waiting for you to resolve this. Choose one approach:

**Option 1: Approach name** (recommended)
```bash
# Step description
command to run
# Then retry
/command-name <args>
```

**Option 2: Alternative approach**
```bash
# Step description
alternative command
# Then retry
/command-name <args>
```

**The agent will NOT attempt to [action] for you.** You must choose and execute one of these approaches.
```

**Important for multiple options:**
- Clearly prioritize recommendations ("recommended" label)
- Keep options to 2-3 maximum
- Each option should be complete (include retry command)
- Final statement emphasizes user choice: "You must choose"

## Anti-Patterns

### ❌ What NOT to Do

**1. Vague language about user actions:**

```markdown
# ❌ WRONG
You might want to run: gt sync -f
Consider resolving conflicts with: gt squash
```

**Why it fails:** Words like "might," "consider," or "you could" are interpreted as suggestions for the agent to execute. Use explicit "you must do this manually" language.

**2. Commands without "user must run" markers:**

```markdown
# ❌ WRONG
**Solution:**
```bash
gt sync -f
gt squash
```
```

**Why it fails:** Bare commands in a "Solution" section are interpreted as the agent's solution to execute. Always preface with "you must do this manually."

**3. Prohibition only at the end:**

```markdown
# ❌ WRONG
[Detailed error handlers with commands]
...
[At line 500]: Note: Never attempt to resolve conflicts automatically
```

**Why it fails:** By the time the agent reads the prohibition, it's already deep into error handling mode and interpreting commands as actions. Prohibition must come FIRST.

**4. Multiple resolution options without prioritization:**

```markdown
# ❌ WRONG
Try one of:
- gt sync -f
- gt restack
- gt stack fix
- erk sync
```

**Why it fails:** Agent may attempt all options or choose randomly. Provide clear, prioritized options with explanations of when to use each.

**5. Commands without context about re-running:**

```markdown
# ❌ WRONG
Run: gt sync -f
```

**Why it fails:** User resolves the issue but doesn't know what to do next. Always include "After resolution, re-run: /command-name"

## Implementation Checklist

When creating or updating an agent that handles errors:

- [ ] Add "STOP and Display" section before error handlers
- [ ] Add "Conflict Resolution Policy" section (if agent handles conflicts)
- [ ] Use ❌ emoji in error handler titles
- [ ] Include "What happened" section explaining the error
- [ ] Include "What you need to do" section with explicit "you must do this manually" language
- [ ] Number steps in resolution process
- [ ] Provide exact commands to run
- [ ] Include retry command at the end of resolution steps
- [ ] End with "The agent will NOT..." prohibition statement
- [ ] For multiple options: label recommended approach and limit to 2-3 options
- [ ] Test that prohibitions appear BEFORE error handlers in the document
- [ ] Verify no bare commands without "user must run" context

## Testing Error Handlers

### Manual Testing Approach

Since automated testing can't easily verify "agent doesn't do X," manual testing is required:

**Create test scenarios for each error type:**

1. **Setup**: Create conditions that trigger the error
2. **Execute**: Run the agent and trigger the error
3. **Observe**: Watch agent behavior carefully

**What to verify:**

- [ ] Agent displays error message to user
- [ ] Agent shows resolution steps clearly
- [ ] Agent STOPS execution (doesn't continue or retry)
- [ ] Agent does NOT execute git/gt/erk commands
- [ ] Error format matches standard template
- [ ] User can follow resolution steps and succeed

**Red flags during testing:**

- Agent executes commands after error occurs
- Agent says "let me try..." or "attempting to..."
- Agent runs gt/git/erk commands not explicitly requested by user
- Agent retries failed operations automatically
- Multiple attempts without user input

### Example Test Scenarios

**For conflict errors:**

1. Create branch with conflicting commits
2. Trigger squash operation that causes conflicts
3. Verify agent displays error and stops
4. Verify agent does NOT run `gt squash` automatically
5. Manually run suggested command and verify it works
6. Re-run agent workflow and verify success

**For sync errors:**

1. Simulate merged parent not reflected in local trunk
2. Trigger operation that detects this state
3. Verify agent displays error and stops
4. Verify agent does NOT run `gt sync -f` automatically
5. Manually run suggested command and verify it works
6. Re-run agent workflow and verify success

## Examples from Production

### gt-branch-submitter (Reference Implementation)

The gt-branch-submitter agent demonstrates the full standard:

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/agents/gt/gt-branch-submitter.md`

**Structure:**
1. Error handling introduction (lines 246-257)
2. STOP and Display section (lines 259-271)
3. Conflict Resolution Policy (lines 273-293)
4. Specific error handlers (lines 295+)

**Error handlers implemented:**
- `submit_merged_parent` - Parent branch merged, needs sync
- `squash_conflict` - Conflicts during commit squashing
- `submit_conflict` - Conflicts during branch submission

**Key features:**
- All three error handlers use consistent format
- Each has "What happened" and "What you need to do" sections
- All end with "The agent will NOT..." statement
- Commands clearly marked as "you must do this manually"
- Retry commands included in resolution steps

### gt-update-pr-submitter (Simpler Example)

The gt-update-pr-submitter agent has simpler error handling:

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/agents/gt/gt-update-pr-submitter.md`

**Structure:**
- Simpler error handling (lines 52-113)
- Could be enhanced with STOP section and policy section
- Current `restack_failed` handler is adequate but minimal

**Status**: Moderate severity - should be updated for consistency

## Future Considerations

### When to Apply This Standard

**MUST apply for:**
- Agents that execute git operations
- Agents that execute gt operations
- Agents that execute erk operations
- Agents that handle merge conflicts
- Agents that modify repository state

**SHOULD apply for:**
- Agents that orchestrate multi-step workflows
- Agents that call external commands
- Agents where errors require user decisions

**MAY skip for:**
- Simple read-only agents
- Agents that only display information
- Agents with no state-modifying operations

### Adapting the Standard

The standard is designed to be flexible:

**Keep these core principles:**
- STOP instructions before error handlers
- Explicit "user must run" language
- Repeated prohibitions in context
- Clear separation of agent vs user actions

**Adapt these details:**
- Specific commands to prohibit (git/gt/erk/other tools)
- Error types and handlers specific to your agent
- Number of resolution options (but keep ≤ 3)
- Level of detail in "Why this matters" sections

### Evolution

As we learn more about how LLMs interpret error guidance:

**Track:**
- Instances where agents still attempt auto-resolution despite prohibitions
- User feedback on clarity of error messages
- Success rate of manual resolution following our steps

**Update:**
- Format templates based on what works best
- Anti-patterns based on observed failures
- Examples from new agent implementations

**Document:**
- New anti-patterns discovered
- Better phrasing that prevents misinterpretation
- Edge cases that need special handling

## Version History

**v1.0 (2025-11-22)**
- Initial standard based on gt-branch-submitter improvements
- Established three-section format (STOP / Policy / Handlers)
- Documented anti-patterns and testing approach
- Created comprehensive examples and checklist
