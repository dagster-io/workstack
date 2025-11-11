# Workstack Plan Command Examples

This document provides examples of using the workstack plan enhancement and creation commands.

## Command Overview

- **`/workstack:enhance-plan`** - Enhance a plan with clarifying questions and context preservation (works in ANY mode)
- **`/workstack:create-plan-stack`** - Save an enhanced plan and create a worktree (requires execution mode)
- **`/workstack:create-from-plan`** - Legacy command that combines both (being phased out)

## Recommended Two-Command Workflow

### Example 1: Full Workflow (Plan Mode → Enhance → Exit → Create Stack)

```
User: [In plan mode] I want to add webhook support for Stripe payments

Agent: [Creates implementation plan...]
## Implementation Plan: Stripe Webhook Support

### Overview
Add webhook endpoint to handle Stripe payment events...

[Plan details...]

User: /workstack:enhance-plan

Agent: I need to clarify a few details to improve the plan:

**File Locations:**
The plan mentions "webhook handler" - which file should contain this?

[User provides answers via AskUserQuestion tool]

Agent: ## Enhanced Implementation Plan

[Shows enhanced plan with Context & Understanding sections]

✅ **Plan enhanced successfully!**

This enhanced plan is now ready to be saved and used to create a worktree.

**Next steps:**
1. Exit plan mode if currently active
2. Run: `/workstack:create-plan-stack`

User: [Exits plan mode]

User: /workstack:create-plan-stack

Agent: ✅ Worktree created: **stripe-webhook-support-25-11-10**

Plan saved to: `/Users/dev/project/stripe-webhook-support-plan.md`
Branch: `stripe-webhook-support-25-11-10`
Location: `/Users/dev/project-stacks/stripe-webhook-support-25-11-10`

**Next step:**

`workstack switch stripe-webhook-support-25-11-10 && claude --permission-mode acceptEdits "/workstack:implement-plan"`
```

### Example 2: Direct Execution Mode (No Plan Mode)

```
User: I have this implementation plan:

## Implementation Plan: Add User Authentication

1. Create auth middleware
2. Add login/logout endpoints
3. Implement JWT tokens
4. Add tests

User: /workstack:enhance-plan "Make sure to use refresh tokens"

Agent: [Asks clarifying questions, incorporates guidance...]

## Enhanced Implementation Plan

[Shows enhanced plan with refresh token details added]

✅ **Plan enhanced successfully!**

User: /workstack:create-plan-stack

Agent: ✅ Worktree created: **add-user-authentication-25-11-10**

[Shows worktree details and next command]
```

### Example 3: Using Guidance with Enhancement

```
User: [Shows plan for database migration]

User: /workstack:enhance-plan "Fix: Use zero-downtime migration approach with 4 phases"

Agent: [Applies the correction to the plan, asks clarifying questions about phases...]

## Enhanced Implementation Plan

### Context & Understanding

#### Architectural Insights
- Zero-downtime deployment requires 4-phase migration to maintain rollback capability
- Each phase must be independently deployable

[Rest of enhanced plan with 4-phase approach integrated]
```

### Example 4: Phase Decomposition

```
User: /workstack:enhance-plan

Agent: [After analyzing the plan...]

This plan would benefit from phase-based implementation. Here's a suggested breakdown:

**Phase 1: Data Layer** [branch: feature-data]
- Create models and migrations
- Add unit tests
- Deliverable: Working database schema with tests

**Phase 2: API Endpoints** [branch: feature-api]
- Implement REST endpoints
- Add integration tests
- Deliverable: Functional API with test coverage

**Phase 3: Frontend Integration** [branch: feature-ui]
- Update UI components
- Add e2e tests
- Deliverable: Complete feature with UI

Would you like to structure the plan this way?

User: Yes, that looks good

Agent: [Shows enhanced plan with phases]
```

## Context Preservation Examples

### Example: API Quirks Discovery

```
During planning discussion:
"I discovered that Stripe webhooks can arrive BEFORE the API response returns to the client"

Enhanced plan includes:

### Context & Understanding

#### API/Tool Quirks
- Stripe webhooks often arrive BEFORE API response returns
  - Impact: Cannot rely on webhook arrival order
  - Solution: Use idempotency keys and state tracking

### Implementation Steps

3. **Create webhook handler**: Implement in `src/webhooks/stripe.py`
   [CRITICAL: Handle out-of-order webhook delivery]

   Related Context:
   - Webhooks may arrive before API response (see API/Tool Quirks)
   - Must implement idempotent processing
```

### Example: Rejected Approaches

```
Enhanced plan includes:

#### Complex Reasoning

**Rejected**: Synchronous payment confirmation (waiting for webhook in API call)
- Reason: Webhooks can take 1-30 seconds, creates timeout issues
- Also: Connection failures would lose webhook delivery entirely

**Chosen**: Async webhook-driven flow with optimistic UI updates
- Returns immediately with pending status
- Updates via webhook when payment completes
- Handles failures gracefully with retry logic
```

## Error Scenarios

### Plan Mode Restriction

```
User: /workstack:create-plan-stack

Agent: ⚠️ This command cannot run in plan mode.

This command needs to write files to disk and create a worktree, which requires execution mode.

Please exit plan mode first, then rerun this command:

/workstack:create-plan-stack
```

### No Plan Found

```
User: /workstack:enhance-plan

Agent: ❌ Error: No implementation plan found in conversation

Details: Could not find a valid implementation plan in conversation history

Suggested action:
  1. Ensure plan is in conversation
  2. Plan should have headers and structure
  3. Re-paste plan in conversation if needed
```

### Worktree Already Exists

```
User: /workstack:create-plan-stack

Agent: ❌ Error: Worktree already exists: feature-auth-25-11-10

Details: A worktree with this name already exists from a previous plan

Suggested action:
  1. View existing: workstack status feature-auth-25-11-10
  2. Switch to it: workstack switch feature-auth-25-11-10
  3. Or remove it: workstack remove feature-auth-25-11-10
  4. Or modify plan title to generate different name
```

## Legacy Command (Being Phased Out)

### Using /workstack:create-from-plan

```
User: /workstack:create-from-plan

Agent: [If in plan mode]
[Runs /workstack:enhance-plan]
✅ Plan enhanced successfully!

⚠️ To save the plan and create a worktree, you need to:
1. Exit plan mode
2. Run: `/workstack:create-plan-stack`

[If not in plan mode]
[Runs both /workstack:enhance-plan and /workstack:create-plan-stack]
[Shows final worktree creation output]
```

## Best Practices

1. **Always enhance plans first** - Even if you think the plan is clear, enhancement often discovers important context
2. **Answer clarifying questions thoroughly** - The more specific, the better the autonomous execution
3. **Include discovered constraints** - If you found something non-obvious during planning, mention it
4. **Use guidance for corrections** - Pass guidance to apply specific fixes: "Fix: Use LBYL pattern"
5. **Exit plan mode before creating stack** - File operations require execution mode

## Tips for Effective Plans

### Good Plan Structure

```markdown
## Implementation Plan: [Clear Title]

### Objective

[One sentence goal]

### Implementation Steps

1. **Specific action**: Do X in `exact/file/path.py`
   - Success: [How to verify]
2. **Another action**: Create Y at `another/path.js`
   - Success: [Test passes]
```

### Vague Plan (Will Trigger Questions)

```markdown
## Plan

1. Update the model
2. Fix the API
3. Improve performance
```

The enhancement process will ask for:

- Which specific model file?
- What needs fixing in the API?
- What performance metrics to target?
