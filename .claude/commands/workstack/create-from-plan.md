---
description: Create a workstack worktree from an implementation plan in context (with interactive enhancement for autonomous execution)
---

# /workstack:create-from-plan

⚠️ **CRITICAL: This command ONLY sets up the workspace - it does NOT implement code!**

## Goal

**The primary objective of this command is to create a detailed, thorough implementation plan that enables a downstream agent to execute autonomously with confidence.**

A well-structured plan eliminates ambiguity, reduces back-and-forth clarifications, and allows the implementing agent to work efficiently without human intervention. Every enhancement we make - from asking clarifying questions to structuring phases - serves this goal of autonomous execution.

**Key principles for autonomous-ready plans:**

- **Zero ambiguity**: Every file path, function name, and operation is explicit
- **Clear success criteria**: Each step has measurable outcomes
- **Self-contained phases**: Complex work is broken into independently testable chunks
- **Test-driven**: Every change includes test requirements for validation
- **Failure handling**: Plans anticipate and address potential issues

**What this command does:**

- ✅ Find plan in conversation
- ✅ Interactively enhance plan for autonomous execution
- ✅ Apply optional guidance to plan
- ✅ Structure complex plans into phases (when beneficial)
- ✅ Save enhanced plan to disk
- ✅ Create worktree with `workstack create --plan`

**What happens AFTER (in separate command):**

- ⏭️ Switch and implement: `workstack switch <name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`

## What Happens

When you run this command, these steps occur:

1. **Verify Scope** - Confirm we're in a git repository with workstack available
2. **Detect Plan** - Search last 5-10 messages for implementation plan
3. **Apply Guidance** - Merge optional guidance into plan (if provided)
4. **Interactive Enhancement** - Analyze plan for gaps, ask clarifying questions, suggest phases
5. **Generate Filename** - Derive filename from plan title
6. **Detect Root** - Find worktree root directory
7. **Save Plan** - Write enhanced plan to disk as markdown file
8. **Create Worktree** - Run `workstack create --plan` command
9. **Display Next Steps** - Show commands to switch and implement (with phase info if applicable)

## Usage

```bash
/workstack:create-from-plan [guidance]
```

**Examples:**

- `/workstack:create-from-plan` - Create worktree from plan with interactive enhancement
- `/workstack:create-from-plan "Make error handling more robust and add retry logic"` - Apply guidance then enhance
- `/workstack:create-from-plan "Fix: Use LBYL instead of try/except throughout"` - Apply corrections then enhance

## Prerequisites

- An implementation plan must exist in recent conversation (last 5-10 messages)
- Current working directory must be in a workstack repository
- The plan should not already be saved to disk at repository root
- (Optional) Guidance text for final corrections/additions to the plan

## Success Criteria

This command succeeds when ALL of the following are true:

✅ Implementation plan extracted from conversation context
✅ Plan enhanced through user interaction (gaps clarified, phases structured)
✅ Plan saved to `<worktree-root>/<filename>-plan.md`
✅ Worktree created with `workstack create --plan`
✅ Worktree contains `.PLAN.md` file (moved by workstack)
✅ User shown command to switch and implement
✅ Plans include "Context & Understanding" section when relevant
✅ API quirks documented with handling strategies
✅ Architectural decisions include rationale
✅ Complex reasoning preserved with alternatives
✅ Known pitfalls prevent common mistakes
✅ Semantic cache reduces implementing agent's discovery time

**Most importantly:** The enhanced plan is detailed and thorough enough that a downstream agent can execute it autonomously with confidence, without needing to ask clarifying questions or make assumptions. The semantic understanding captured saves the implementing agent from expensive rediscovery of insights.

**Most importantly:** The enhanced plan is detailed and thorough enough that a downstream agent can execute it autonomously with confidence, without needing to ask clarifying questions or make assumptions.

**Verification:**
After command completes, these should be true:

- File exists: `<worktree-root>/<filename>-plan.md`
- Worktree listed in: `workstack list`
- Plan has zero ambiguous file/function references
- Complex plans are structured in phases
- Each step has clear success criteria and failure handling
- Next command ready: `workstack switch <name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`

## Performance Notes

**Expected execution time:** 15-60 seconds

**Breakdown:**

- Plan detection: 2-5 seconds (depends on context size)
- Guidance application: 3-10 seconds (AI processing, if used)
- Interactive enhancement: 5-30 seconds (depends on clarifications needed)
- File operations: < 1 second
- Worktree creation: 2-10 seconds (depends on repository size)
- JSON parsing: < 1 second

**Factors affecting speed:**

- Conversation length (for plan detection)
- Number of clarifications needed
- Plan complexity (affects phase decomposition)
- Repository size (for worktree creation)
- Disk I/O speed

**If command takes > 90 seconds:** Something is wrong

- Check if workstack create is hanging
- Verify disk space and permissions
- Check git repository health: `git fsck`

## Troubleshooting

### "No plan found in context"

**Cause:** Plan not in recent conversation or doesn't match detection patterns
**Solution:**

- Ensure plan is in last 5-10 messages
- Plan should have headers like "## Implementation Plan" or numbered steps
- Re-paste plan in conversation if needed

### "Plan file already exists"

**Cause:** File with same name exists at repository root
**Solution:**

- Change plan title to generate different filename
- Delete existing file: `rm <worktree-root>/<filename>-plan.md`

### "Worktree already exists"

**Cause:** Worktree with derived name already exists
**Solution:**

- List worktrees: `workstack list`
- Remove existing: `workstack remove <name>`
- Or switch to existing: `workstack switch <name>`

### "Failed to parse workstack output"

**Cause:** Workstack version doesn't support --json flag
**Solution:**

- Check version: `workstack --version`
- Update: `uv pip install --upgrade workstack`

### Enhancement suggestions not applied correctly

**Cause:** Ambiguous user responses or misinterpretation
**Solution:**

- Be specific in responses to clarifying questions
- Use clear action words: "Fix:", "Add:", "Change:", "Reorder:"
- Or skip enhancement and edit the .PLAN.md file after creation

---

## Examples: Capturing Semantic Understanding

### Example 1: API Deep Understanding

**Before (surface level):**

```markdown
### Implementation Steps

1. Call Stripe API to process payment
2. Update order status
3. Send confirmation email
```

**After (with semantic understanding):**

```markdown
### Context & Understanding

**API/Tool Quirks Discovered**:

- Stripe API: Webhooks can arrive before API response
  - Why it matters: Payment status could be updated twice, causing duplicate confirmations
  - How to handle: Use DB locks when updating payment status (see step 2)
  - Watch out for: Race conditions between webhook handler and API response handler

### Implementation Steps

1. Call Stripe API to process payment
2. Update order status with database lock (prevents webhook race condition)
3. Send confirmation email (check for duplicates first)
```

### Example 2: Architectural Insight

**Before (surface level):**

```markdown
### Implementation Steps

1. Add new endpoint to API router
2. Create handler function
3. Add tests
```

**After (with semantic understanding):**

```markdown
### Context & Understanding

**System Architecture Insights**:

- API uses dependency injection for all external services (DB, cache, etc.)
- Implication: Cannot directly instantiate services in handlers, must use DI container

**Reasoning Trail**:

- Considered: Direct database connection in handler
  - Pros: Simpler, fewer abstractions
  - Cons: Breaks testing isolation, violates architecture
- Rejected because: All other handlers use DI, would break consistency
- Chose: Follow existing DI pattern
  - Tradeoff accepted: More boilerplate, but maintains testability

### Implementation Steps

1. Add new endpoint to API router with DI annotations
2. Create handler function accepting injected dependencies
3. Add tests using mock dependencies
```

### Example 3: Complex Business Logic

**Before (surface level):**

```markdown
### Implementation Steps

1. Update pricing calculation
2. Apply discounts
3. Calculate tax
```

**After (with semantic understanding):**

```markdown
### Context & Understanding

**Domain Logic & Constraints**:

- Discount order matters: Volume discounts apply before percentage discounts
  - Rationale: Prevents gaming the system with stacked discounts
  - Edge case: Customer has both loyalty discount and bulk order
  - Validation: Total discount cannot exceed 50% (business rule)

**Known Pitfalls**:
| Don't Do This | Why It Seems Right | Why It's Wrong | Do This Instead |
|---|---|---|---|
| Apply tax to discounted price | Standard calculation | Tax law requires pre-discount price | Calculate tax on full price, then apply discount |

### Implementation Steps

1. Update pricing calculation with original price tracking
2. Apply discounts in order: volume → percentage → cap at 50%
3. Calculate tax on original price, then apply to final total
```

---

## Agent Instructions

You are executing the `/workstack:create-from-plan` command. Follow these steps carefully:

### Step 1: Verify Scope and Constraints

**Error Handling Template:**
All errors must follow this format:

```
❌ Error: [Brief description in 5-10 words]

Details: [Specific error message, relevant context, or diagnostic info]

Suggested action: [1-3 concrete steps to resolve]
```

**YOUR ONLY TASKS:**

1. Extract implementation plan from conversation
2. Interactively enhance plan for autonomous execution
3. Apply guidance modifications if provided
4. Save enhanced plan to disk as markdown file
5. Run `workstack create --plan <file>`
6. Display next steps to user

**FORBIDDEN ACTIONS:**

- Writing ANY code files (.py, .ts, .js, etc.)
- Making ANY edits to existing codebase
- Running ANY commands except `git rev-parse` and `workstack create`
- Implementing ANY part of the plan

This command sets up the workspace. Implementation happens in the worktree via `/workstack:implement-plan`.

**CRITICAL: Understanding the ExitPlanMode → create-from-plan Workflow**

If you just used the ExitPlanMode tool, you saw this message:

> "User has approved your plan. You can now start coding"

**DO NOT start coding!** In this workflow, that message means:

- ✅ "You can now start creating the worktree with the plan"
- ❌ NOT "You should implement the code now"

**The typical workflow is:**

1. User asks for a plan in plan mode
2. You present a plan and call ExitPlanMode
3. ExitPlanMode returns: "User has approved your plan. You can now start coding"
4. User immediately invokes `/workstack:create-from-plan`
5. **This command** extracts the approved plan, enhances it, saves to disk, creates worktree
6. User manually runs `workstack switch <name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`
7. **That's when** the actual code implementation happens

The ExitPlanMode message is generic and doesn't know about the workstack workflow. When followed by this command, interpret "start coding" as "start the worktree creation workflow," NOT "write code files now."

Your role: Extract the plan → enhance it → save it → create worktree → tell user how to switch and implement.

### Step 2: Detect Implementation Plan in Context

Search the last 5-10 messages in conversation for an implementation plan:

**Search strategy:**

1. Work backwards from most recent messages
2. Stop at first complete plan found
3. Look for markdown content with structure

**What constitutes a complete plan:**

- Minimum 100 characters
- Contains headers (# or ##) OR numbered lists OR bulleted lists
- Has title/overview AND implementation steps

**Common plan patterns:**

- Markdown with "Implementation Plan:", "Overview", "Implementation Steps"
- Structured task lists or step-by-step instructions
- Headers containing "Plan", "Tasks", "Steps", "Implementation"

**If no plan found:**

```
❌ Error: No implementation plan found in recent conversation

Details: Searched last 5-10 messages but found no valid implementation plan

Suggested action:
  1. Ensure plan is in recent conversation (not too far back)
  2. Plan should have headers and structure
  3. Re-paste plan in conversation if needed
```

**Plan validation:**

- Must be at least 100 characters
- Must contain structure (numbered lists, bulleted lists, or multiple headers)
- If invalid, show error:

```
❌ Error: Plan content is too minimal or invalid

Details: Plan lacks structure or implementation details

Suggested action:
  1. Provide a more detailed implementation plan
  2. Include specific tasks, steps, or phases
  3. Use headers and lists to structure the plan
```

### Step 3: Apply Optional Guidance to Plan

**Check for guidance argument:**

If guidance text is provided as an argument to this command:

**Guidance Classification and Merging Algorithm:**

1. **Correction** - Fixes errors in approach
   - Pattern: "Fix:", "Correct:", "Use X instead of Y"
   - Action: Update relevant sections in-place
   - Example: "Fix: Use LBYL not try/except" → Replace exception handling approaches throughout

2. **Addition** - New requirements or features
   - Pattern: "Add:", "Include:", "Also implement"
   - Action: Add new subsections or steps
   - Example: "Add retry logic to API calls" → Insert new step or enhance existing API steps

3. **Clarification** - More detail or specificity
   - Pattern: "Make X more", "Ensure", "Specifically"
   - Action: Enhance existing steps with details
   - Example: "Make error messages user-friendly" → Add detail to error handling sections

4. **Reordering** - Priority or sequence changes
   - Pattern: "Do X before Y", "Prioritize", "Start with"
   - Action: Restructure order of steps
   - Example: "Do validation before processing" → Move validation steps earlier

**Integration Process:**

1. Parse guidance to identify type(s)
2. Find relevant sections in plan
3. Apply transformations contextually (not just appending)
4. Preserve plan structure and formatting
5. Maintain coherent flow

**Edge cases:**

**Guidance without plan in context:**

```
❌ Error: Cannot apply guidance - no plan found in context

Details: Guidance provided: "[first 100 chars of guidance]"

Suggested action:
  1. First create or present an implementation plan
  2. Then run: /workstack:create-from-plan "your guidance here"
```

**Multi-line guidance limitation:**
Note: Guidance must be provided as a single-line string in quotes. Multi-line guidance is not supported.

If no guidance provided: use the original plan as-is

**Output:** Final plan content (original or modified) ready for Step 3.5 processing

### Context Preservation Principle: The Semantic Cache

When planning complex implementations, the planning agent often discovers valuable insights that would be expensive for the implementing agent to re-derive:

**What is Semantic Understanding?**

- **NOT just file paths and locations** (those are cheap to find)
- **NOT just "what to do"** (that's the basic plan)
- **IS the "why" and "how"** discovered through exploration
- **IS the non-obvious quirks, constraints, and gotchas**

**Types of Understanding Worth Preserving:**

1. **API/Tool Deep Understanding**
   - Rate limits, retry strategies, undocumented behaviors
   - Authentication flows and token management
   - Race conditions, ordering requirements
   - Example: "Stripe webhooks can arrive before API response returns"

2. **Architectural Insights**
   - WHY code is structured certain ways (not just how)
   - Design boundaries and their rationale
   - Performance vs. maintainability tradeoffs
   - Example: "Config is split across files because of circular import issues"

3. **Domain Logic & Business Rules**
   - Non-obvious invariants that must be maintained
   - Edge cases that matter and why
   - Regulatory or compliance requirements
   - Example: "Never delete audit records, only mark as archived"

4. **Complex Reasoning Chains**
   - Alternatives considered and explicitly rejected
   - Multi-step logic that led to decisions
   - Dependencies between choices
   - Example: "Can't use async here because parent caller is sync"

5. **Known Pitfalls & Anti-patterns**
   - Things that seem right but cause problems
   - Framework-specific gotchas
   - Performance traps unique to this codebase
   - Example: "Don't use .resolve() before checking .exists()"

**Relevance Filter - Only Include if:**

- It took >5 minutes to discover/understand
- It would change HOW something is implemented (not just what)
- Missing it would likely cause bugs or rework
- It's non-obvious from reading the code

**How to Capture:**

- Use the "Context & Understanding" section in plan templates
- Be specific with concrete examples, not abstract descriptions
- Link each insight to specific implementation steps
- Include "why it matters" and "how to handle"

### Step 3.5: Interactive Plan Enhancement

**CRITICAL:** This is where we transform a generic plan into one optimized for autonomous agent execution.

**Remember the goal:** We are creating a detailed, thorough implementation plan that enables a downstream agent to execute autonomously with confidence. Every question we ask and every enhancement we suggest should serve this goal. If the plan already has enough detail for autonomous execution, don't add unnecessary complexity.

#### Plans Should Describe WHAT, Not Include HOW (Code)

**Core principle:** Implementation plans should describe behavior, requirements, and architectural decisions - NOT include exact code snippets or implementation details.

**Why:**

- Plans describe **intent and behavior**, code implements the details
- Exact code snippets in plans become stale quickly
- Code snippets constrain the implementing agent unnecessarily
- Plans are for humans and agents to understand goals, not copy-paste

**Exception - When code snippets ARE appropriate:**

Only include exact code in plans for high-stakes scenarios where precision is critical:

1. **Security-critical code**: Authentication, authorization, encryption implementations
2. **Public APIs**: Interface signatures that cannot change without breaking consumers
3. **Critical interfaces**: Database schema changes, protocol definitions, contract boundaries
4. **Bug fixes**: When demonstrating the exact before/after change for a subtle bug

**What to include instead:**

- File paths: "Update `src/models/user.py`"
- Function names: "Modify `validate_credentials()` function"
- Behavior: "Return 401 when authentication fails, 403 when authorized but forbidden"
- Requirements: "Use LBYL pattern for path validation"
- Success criteria: "All existing authentication tests pass, plus new edge cases"

**Example comparison:**

❌ **Too specific (code snippet):**

```
Add this code to src/auth.py:
def validate_user(user_id: str | None) -> User:
    if user_id is None:
        raise ValueError("user_id cannot be None")
    if user_id not in user_cache:
        raise UserNotFoundError(f"User {user_id} not found")
    return user_cache[user_id]
```

✅ **Right level of detail (behavioral):**

```
Update validate_user() in src/auth.py:
- Use LBYL pattern: check user_id is not None before proceeding
- Check user exists in cache before accessing
- Raise ValueError for None, UserNotFoundError for missing users
- Return User object from cache when found
```

#### Phase 1: Analyze Plan for Gaps

Examine the plan for ambiguities that would block autonomous execution:

**Common gaps to identify:**

1. **Vague file references**: "the config file", "update the model", "modify the API"
   - Need: Exact file paths

2. **Unclear operations**: "improve", "optimize", "refactor", "enhance"
   - Need: Specific actions and metrics

3. **Missing success criteria**: Steps without clear completion conditions
   - Need: Testable outcomes

4. **Unspecified dependencies**: External services, APIs, packages mentioned without details
   - Need: Availability, versions, fallbacks

5. **Large scope indicators**:
   - More than 200 lines of expected changes
   - More than 3 distinct features
   - Multiple unrelated components
   - Need: Phase decomposition

6. **Missing reasoning context**: "use the better approach", "handle carefully"
   - Need: Which approach was chosen and WHY
   - Need: What "carefully" means specifically

7. **Vague constraints**: "ensure compatibility", "maintain performance"
   - Need: Specific versions, standards, or metrics
   - Need: Quantifiable requirements

8. **Hidden complexity**: Steps that seem simple but aren't
   - Need: Document discovered complexity
   - Need: Explain non-obvious requirements

#### Phase 2: Ask Clarifying Questions

For each gap identified, ask the user specific questions. Use the AskUserQuestion tool to get answers.

**Question format examples:**

```markdown
I need to clarify a few details to ensure the plan can be executed autonomously:

**File Locations:**
The plan mentions "update the user model" - which specific file contains this model?

- Example: `models/user.py` or `src/database/models.py`

**Success Criteria:**
Phase 2 mentions "improve performance" - what specific metrics should I target?

- Example: "Response time < 200ms" or "Memory usage < 100MB"

**External Dependencies:**
The plan references "the payments API" - which service is this?

- Example: "Stripe API v2" or "Internal billing service at /api/billing"
```

**Important:**

- Ask all clarifying questions in one interaction (batch them)
- Make questions specific and provide examples
- Allow user to skip questions if they prefer ambiguity

#### Phase 2.5: Capture Semantic Understanding

After clarifying questions but before suggesting phases, assess whether you discovered valuable context during planning:

**Self-Assessment Questions** (planning agent asks itself):

1. Did I spend significant time understanding an external API or tool?
2. Did I discover non-obvious architectural patterns or constraints?
3. Did I reason through multiple approaches before choosing one?
4. Did I uncover edge cases or gotchas that would surprise someone?
5. Did I learn something that changes HOW (not just what) to implement?

**If YES to any**, prompt the user:

```markdown
I discovered important context while planning that would help the implementing agent:

**[Type of Understanding]**: [Brief description]

Specific insights:

- [Concrete example or quirk]
- Why it matters: [Impact on implementation]
- How to handle: [Recommended approach]

Should I include this in the 'Context & Understanding' section? This would prevent the implementing agent from having to rediscover these insights.
```

**Examples of Semantic Understanding to Capture:**

- **API Quirk**: "GitHub API returns 404 for private repos even with valid token - must check permissions separately"
- **Architecture**: "Can't modify BaseClass directly - all customization through dependency injection"
- **Business Logic**: "Order status must transition through 'pending' - direct jump to 'completed' breaks audit trail"
- **Performance**: "Batch size >100 causes OOM on production servers despite working locally"

#### Phase 3: Suggest Phase Decomposition

For complex plans, suggest breaking into phases:

**Decomposition triggers:**

- Plan has 3+ distinct features
- Expected changes exceed 200 lines
- Multiple components with different concerns
- Sequential dependencies between major parts

**IMPORTANT - Testing and validation:**

- Testing and validation are ALWAYS bundled within implementation phases
- Never create separate phases for "add tests" or "run validation"
- Each phase is an independently testable commit with its own tests
- Only decompose when business logic complexity genuinely requires it
- Tests are part of the deliverable for each phase, not afterthoughts

**Phase structure suggestion:**

```markdown
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

Each phase will be a separate branch that can be tested independently.
Would you like to structure the plan this way? (I can adjust the phases if needed)
```

#### Phase 4: Incorporate Enhancements

Based on user responses:

1. **Update file references** with exact paths
2. **Replace vague terms** with specific actions
3. **Add success criteria** to each major step
4. **Structure into phases** if approved
5. **Add test requirements** to each phase
6. **Include `/ensure-ci` validation** checkpoints

**Enhanced plan format for phases:**

````markdown
## Implementation Plan: [Title]

### Execution Mode: Phased Implementation with Graphite Stack

### Context & Understanding

<!-- Semantic cache of expensive-to-derive knowledge -->

**System Architecture Insights**:

- [Key insight about WHY system works this way]
- Implication: [How this affects implementation]

**API/Tool Quirks Discovered**:

- [Tool/API name]: [Non-obvious behavior]
  - Why it matters: [Impact on implementation]
  - How to handle: [Specific approach]
  - Watch out for: [Common mistake]

**Domain Logic & Constraints**:

- [Business rule or constraint]
  - Rationale: [Why this exists]
  - Edge case: [Non-obvious scenario]
  - Validation: [How to verify correctness]

**Reasoning Trail** (if complex decisions were made):

- Considered: [Alternative approach]
  - Pros: [Benefits]
  - Cons: [Drawbacks]
- Rejected because: [Specific reason]
- Chose: [Selected approach]
  - Tradeoff accepted: [What we're giving up]

### Known Pitfalls

<!-- Anti-patterns and mistakes to avoid -->

| Don't Do This  | Why It Seems Right | Why It's Wrong   | Do This Instead    |
| -------------- | ------------------ | ---------------- | ------------------ |
| [Anti-pattern] | [Intuitive reason] | [Actual problem] | [Correct approach] |

### Codebase Navigation

<!-- ONLY paths/patterns directly referenced in implementation steps -->

**Files to Modify** (linked to steps below):

- `[path]`: Phase [X] - [What to change]

**Reference Implementations** (for "similar to" mentions):

- `[file:line]`: Phase [Y] - [Pattern to follow]

**Import Paths** (for functions used in plan):

```python
# Only imports needed for implementation
from workstack.core.config import [specifics]
```
````

### Phase 1: [descriptive-name]

**Branch**: feature-1 (base: main)
**Objective**: [Single, clear goal]
**Success Criteria**:

- [Specific, measurable outcome]
- All tests pass
- `/ensure-ci` validation passes

**Implementation Steps:**

1. [Specific action] in [exact file path]
2. Add tests for [specific functionality] in [test file path]
3. [Additional specific steps...]

**Validation**: Run `/ensure-ci` to verify all tests pass

---

### Phase 2: [descriptive-name]

**Branch**: feature-2 (stacks on: feature-1)
**Objective**: [Single, clear goal]
[Continue pattern...]

````

**Enhanced plan format for single-phase:**

```markdown
## Implementation Plan: [Title]

### Objective

[Clear, specific goal statement]

### Success Criteria

- [Measurable outcome 1]
- [Measurable outcome 2]
- All tests pass
- `/ensure-ci` validation passes

### Context & Understanding
<!-- Semantic cache of expensive-to-derive knowledge -->

**System Architecture Insights**:
- [Key insight about WHY system works this way]
- Implication: [How this affects implementation]

**API/Tool Quirks Discovered**:
- [Tool/API name]: [Non-obvious behavior]
  - Why it matters: [Impact on implementation]
  - How to handle: [Specific approach]
  - Watch out for: [Common mistake]

**Domain Logic & Constraints**:
- [Business rule or constraint]
  - Rationale: [Why this exists]
  - Edge case: [Non-obvious scenario]
  - Validation: [How to verify correctness]

**Reasoning Trail** (if complex decisions were made):
- Considered: [Alternative approach]
  - Pros: [Benefits]
  - Cons: [Drawbacks]
- Rejected because: [Specific reason]
- Chose: [Selected approach]
  - Tradeoff accepted: [What we're giving up]

### Known Pitfalls
<!-- Anti-patterns and mistakes to avoid -->

| Don't Do This | Why It Seems Right | Why It's Wrong | Do This Instead |
|---|---|---|---|
| [Anti-pattern] | [Intuitive reason] | [Actual problem] | [Correct approach] |

### Codebase Navigation
<!-- ONLY paths/patterns directly referenced in implementation steps -->

**Files to Modify** (linked to steps below):
- `[path]`: Step [X] - [What to change]

**Reference Implementations** (for "similar to" mentions):
- `[file:line]`: Step [Y] - [Pattern to follow]

**Import Paths** (for functions used in plan):
```python
# Only imports needed for implementation
from workstack.core.config import [specifics]
````

### Implementation Steps

1. **[Action]**: [Specific operation] in `[exact/file/path]`
   - Success indicator: [How to verify this step worked]
   - If fails: [Fallback or error handling]

2. **[Action]**: [Specific operation] in `[exact/file/path]`
   - Success indicator: [How to verify this step worked]
   - If fails: [Fallback or error handling]

[Continue pattern...]

### Testing Requirements

- Unit tests: [Specific test files to create/modify]
- Integration tests: [If applicable]
- Validation: Run `/ensure-ci` after implementation

````

#### Phase 4.5: Apply Tiered Disclosure for Complex Topics

For detailed technical explanations that might overwhelm the main flow, use collapsible sections:

**Template for Complex Steps:**

```markdown
### Implementation Steps

1. **[High-level step description]**
   - [Key action 1]
   - [Key action 2]

   <details>
   <summary>Deep Dive: [Complex Topic]</summary>

   **Why this complexity exists:**
   [Explanation of underlying issues]

   **Detailed implementation:**
   ```python
   # Code examples if helpful
````

**Edge cases to handle:**

- [Edge case 1]: [How to handle]
- [Edge case 2]: [How to handle]

**Recovery strategies:**

- If [error X]: [Recovery approach]
- If [error Y]: [Recovery approach]

   </details>

`````

**Guidelines for Tiered Disclosure:**

- **Main content**: 2-3 lines per step (always visible)
- **Deep dive**: Unlimited but focused (collapsible)
- **Use when**: Technical detail exceeds 10 lines
- **Always include**: "Why this matters" in deep dive
- **Link to steps**: Reference which implementation step needs this detail

**Example:**

````markdown
1. **Configure webhook endpoint**
   - Register endpoint with external service
   - Set up retry logic for resilience

   <details>
   <summary>Deep Dive: Webhook Race Conditions</summary>

   **Why this complexity exists:**
   The webhook can arrive before the API call returns, causing duplicate processing.

   **How to handle:**
   - Use database locks on payment ID
   - Check payment status before processing
   - Implement idempotency keys

   **Code approach:**

   ```python
   with database.lock(f"payment_{payment_id}"):
       if payment.status != "pending":
           return  # Already processed
       process_payment(payment)
`````

````

   </details>
```

#### Phase 5: Final Review

Present a final review of potential execution issues (not a quality score):

```markdown
## Plan Review - Potential Execution Issues

🟡 **Ambiguous reference: "the main configuration"**
Impact: Agent won't know which file to modify
Suggested fix: Specify exact path (e.g., `config/settings.py`)
[Fix Now] [Continue Anyway]

🟡 **No test coverage specified for new endpoints**
Impact: Can't verify implementation works correctly
Suggested fix: Add test requirements for each endpoint
[Add Tests] [Skip]

🔴 **Database migration lacks rollback strategy**
Impact: Failed migration could leave database in broken state
Suggested fix: Include rollback procedure or backup strategy
[Add Rollback] [Accept Risk]
```

**Key principles:**

- Only flag issues that would genuinely block execution
- Provide concrete impact statements
- Let users dismiss warnings
- Don't use percentages or scores
- Focus on actionability

**Output:** Final enhanced plan content ready for Step 4 processing

### Step 4: Generate Filename from Plan

**Filename Extraction Algorithm:**

1. **Try H1 header** - Look for `# Title` at start of document
2. **Try H2 header** - Look for `## Title` if no H1
3. **Try prefix patterns** - Look for text after "Plan:", "Implementation Plan:"
4. **Fallback to first line** - Use first non-empty line as last resort

**Validation and Cleanup:**

1. Extract raw title using above priority
2. Convert to lowercase
3. Replace spaces with hyphens
4. Remove all special characters except hyphens and alphanumeric
5. Handle Unicode: Normalize to NFC, remove emojis/special symbols
6. Truncate to 100 characters max (excluding -plan.md suffix)
7. Ensure at least one alphanumeric character remains

**If extraction fails:**

If cleanup results in empty string or no alphanumeric chars, prompt the user:

```
❌ Error: Could not extract valid plan name from title

Details: Plan title contains only special characters or is empty

Suggested action:
  1. Add a clear title to your plan (e.g., # Feature Name)
  2. Or provide a name: What would you like to name this plan?
```

Use AskUserQuestion tool to get the plan name from the user if extraction fails.

**Example transformations:**

- "User Authentication System" → `user-authentication-system-plan.md`
- "Fix: Database Connection Issues" → `fix-database-connection-issues-plan.md`
- "🚀 Awesome Feature!!!" → `awesome-feature-plan.md`
- Very long title (200 chars) → Truncated to 100 chars + `-plan.md`
- "###" (only special chars) → Prompt user for name

### Step 5: Detect Worktree Root

Execute: `git rev-parse --show-toplevel`

This returns the absolute path to the root of the current worktree. Store this as `<worktree-root>` for use in subsequent steps.

**If the command fails:**

```
❌ Error: Could not detect worktree root

Details: Not in a git repository or git command failed

Suggested action:
  1. Ensure you are in a valid git repository
  2. Run: git status (to verify git is working)
  3. Check if .git directory exists
```

### Step 6: Save Plan to Disk

**Pre-save validation:**

Check if file already exists at `<worktree-root>/<derived-filename>`:

```
❌ Error: Plan file already exists

Details: File exists at: <worktree-root>/<derived-filename>

Suggested action:
  1. Change plan title to generate different filename
  2. Or delete existing: rm <worktree-root>/<derived-filename>
  3. Or choose different plan name
```

**Save the plan:**

Use the Write tool to save:

- Path: `<worktree-root>/<derived-filename>`
- Content: Full enhanced plan markdown content
- Verify file creation

**If save fails:**

```
❌ Error: Failed to save plan file

Details: [specific write error from tool]

Suggested action:
  1. Check file permissions in repository root
  2. Verify available disk space
  3. Ensure path is valid: <worktree-root>/<derived-filename>
```

### Step 7: Create Worktree with Plan

Execute: `workstack create --plan <worktree-root>/<filename> --json --stay`

**Parse JSON output:**

Expected JSON structure:

```json
{
  "worktree_name": "feature-name",
  "worktree_path": "/path/to/worktree",
  "branch_name": "feature-branch",
  "plan_file": "/path/to/.PLAN.md",
  "status": "created"
}
```

**Validate all required fields exist:**

- `worktree_name` (string, non-empty)
- `worktree_path` (string, valid path)
- `branch_name` (string, non-empty)
- `plan_file` (string, path to .PLAN.md)
- `status` (string: "created" or "exists")

**Handle errors:**

**Missing fields in JSON:**

```
❌ Error: Invalid workstack output - missing required fields

Details: Missing: [list of missing fields]

Suggested action:
  1. Check workstack version: workstack --version
  2. Update if needed: uv pip install --upgrade workstack
  3. Report issue if version is current
```

**JSON parsing fails:**

```
❌ Error: Failed to parse workstack create output

Details: [parse error message]

Suggested action:
  1. Check workstack version: workstack --version
  2. Ensure --json flag is supported (v0.2.0+)
  3. Try running manually: workstack create --plan <file> --json
```

**Worktree already exists (status = "exists"):**

```
❌ Error: Worktree already exists: <worktree_name>

Details: A worktree with this name already exists from a previous plan

Suggested action:
  1. View existing: workstack status <worktree_name>
  2. Switch to it: workstack switch <worktree_name>
  3. Or remove it: workstack remove <worktree_name>
  4. Or modify plan title to generate different name
```

**Command execution fails:**

```
❌ Error: Failed to create worktree

Details: [workstack error message from stderr]

Suggested action:
  1. Check git repository health: git fsck
  2. Verify workstack is installed: workstack --version
  3. Check plan file exists: ls -la <plan-file>
```

**CRITICAL: Claude Code Directory Behavior**

🔴 **Claude Code CANNOT switch directories.** After `workstack create` runs, you will remain in your original directory. This is **NORMAL and EXPECTED**. The JSON output gives you all the information you need about the new worktree.

**Do NOT:**

- ❌ Try to verify with `git branch --show-current` (shows the OLD branch)
- ❌ Try to `cd` to the new worktree (will just reset back)
- ❌ Run any commands assuming you're in the new worktree

**Use the JSON output directly** for all worktree information.

### Step 8: Display Next Steps

After successful worktree creation, provide clear instructions based on plan structure.

**IMPORTANT:** You have NOT implemented any code. Implementation happens after the user switches to the worktree.

**For single-phase plans:**

```markdown
✅ Worktree created: **<worktree-name>**

Plan: `<filename>`
Branch: `<branch-name>`
Location: `<worktree-path>`

**Next step:**

`workstack switch <worktree_name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`
```

**For multi-phase plans:**

```markdown
✅ Worktree created: **<worktree-name>**

Plan: `<filename>` (structured in <number> phases)
Branch: `<branch-name>`
Location: `<worktree-path>`

**Phases to be implemented:**

- Phase 1: <phase-name> (branch: <branch-name>)
- Phase 2: <phase-name> (stacks on: <previous-branch>)
- Phase 3: <phase-name> (stacks on: <previous-branch>)

Each phase will be implemented as a separate branch with CI verification.

**Next step:**

`workstack switch <worktree_name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`
```

**Note:** The final output the user sees should be the single copy-pasteable command above. No additional text after that command.

## Important Notes

- 🎯 **Primary Goal:** Create a detailed, thorough implementation plan that enables autonomous agent execution with confidence
- 🔴 **This command does NOT write code** - only creates workspace with enhanced plan
- Searches last 5-10 messages for implementation plans
- Interactively enhances plans through clarifying questions
- Suggests phase decomposition for complex plans (200+ lines or 3+ features)
- Each phase gets its own branch with test requirements and CI validation
- All enhancements are optional - users can dismiss suggestions
- Filename derived from plan title, max 100 chars, prompts user if extraction fails
- All errors follow consistent template with details and suggested actions
- This command does NOT switch directories or execute the plan
- User must manually run `workstack switch` and `/workstack:implement-plan` to begin implementation
- The `--permission-mode acceptEdits` flag is included to automatically accept edits during implementation
- Plans are optimized for autonomous agent execution with zero ambiguity
- Always provide clear feedback at each step
````
