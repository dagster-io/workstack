---
description: Enhance an implementation plan from context with clarifying questions and semantic preservation
---

# /workstack:enhance-plan

## Goal

**Extract and enhance an implementation plan from conversation context for clarity and autonomous execution.**

This command finds a plan in the conversation, optionally applies guidance, asks clarifying questions, preserves semantic understanding, and outputs an enhanced plan as markdown text.

**What this command does:**

- ✅ Find plan in conversation
- ✅ Apply optional guidance to plan
- ✅ Interactively enhance plan through clarifying questions
- ✅ Preserve semantic understanding and context
- ✅ Structure complex plans into phases (when beneficial)
- ✅ Output enhanced plan as markdown text

**What this command does NOT do:**

- ❌ Save plan to disk
- ❌ Create worktree
- ❌ Check plan mode (works in ANY mode)

## What Happens

When you run this command, these steps occur:

1. **Detect Plan** - Search conversation for implementation plan
2. **Apply Guidance** - Merge optional guidance into plan (if provided)
3. **Extract Semantic Understanding** - Preserve valuable context discovered during planning
4. **Interactive Enhancement** - Analyze plan and ask clarifying questions if needed
5. **Output Enhanced Plan** - Display the enhanced plan as markdown text

## Usage

```bash
/workstack:enhance-plan [guidance]
```

**Examples:**

- `/workstack:enhance-plan` - Enhance plan from context
- `/workstack:enhance-plan "Make error handling more robust and add retry logic"` - Apply guidance to plan
- `/workstack:enhance-plan "Fix: Use LBYL instead of try/except throughout"` - Apply corrections to plan

**Next step after enhancement:**
Use `/workstack:create-plan-stack` to save the enhanced plan and create a worktree.

## Prerequisites

- An implementation plan must exist in conversation
- (Optional) Guidance text for final corrections/additions to the plan

## Semantic Understanding & Context Preservation

**Why This Matters:** Planning agents often discover valuable insights that would be expensive for implementing agents to re-derive. Capturing this context saves time and prevents errors.

**What to Capture:**

1. **API/Tool Quirks**
   - Undocumented behaviors, race conditions, timing issues
   - Example: "Stripe webhooks can arrive before API response returns"
   - Include: Why it matters, how to handle, what to watch for

2. **Architectural Insights**
   - WHY code is structured certain ways (not just how)
   - Design boundaries and their rationale
   - Example: "Config split across files due to circular imports"

3. **Domain Logic & Business Rules**
   - Non-obvious invariants, edge cases, compliance requirements
   - Example: "Never delete audit records, only mark as archived"
   - Include: Rationale, validation criteria, edge cases

4. **Complex Reasoning**
   - Alternatives considered and rejected with reasons
   - Dependencies between choices
   - Example: "Can't use async here because parent caller is sync"

5. **Known Pitfalls**
   - Anti-patterns that seem right but cause problems
   - Framework-specific gotchas
   - Example: "Don't use .resolve() before checking .exists()"

**Relevance Filter:** Only include if it:

- Took significant time to discover
- Would change HOW something is implemented
- Would likely cause bugs if missed
- Isn't obvious from reading the code

**How It's Used:** This understanding gets captured in the "Context & Understanding" section of enhanced plans, linked to specific implementation steps.

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Enhancement:**
✅ Implementation plan extracted from conversation context
✅ If guidance provided, it has been applied to the plan
✅ Semantic understanding preserved in Context & Understanding section
✅ Clarifying questions asked and incorporated (if needed)
✅ Plan structured into phases (if beneficial)

**Output:**
✅ Enhanced plan displayed as markdown text
✅ User informed about next step (`/workstack:create-plan-stack`)

## Troubleshooting

### "No plan found in context"

**Cause:** Plan not in conversation or doesn't match detection patterns
**Solution:**

- Ensure plan is in conversation history
- Plan should have headers like "## Implementation Plan" or numbered steps
- Re-paste plan in conversation if needed

### Enhancement suggestions not applied correctly

**Cause:** Ambiguous user responses or misinterpretation
**Solution:**

- Be specific in responses to clarifying questions
- Use clear action words: "Fix:", "Add:", "Change:", "Reorder:"
- Re-run command with clearer guidance

---

## Agent Instructions

You are executing the `/workstack:enhance-plan` command. Follow these steps carefully:

### Step 1: Detect Implementation Plan in Context

Search conversation history for an implementation plan:

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
❌ Error: No implementation plan found in conversation

Details: Could not find a valid implementation plan in conversation history

Suggested action:
  1. Ensure plan is in conversation
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

### Step 2: Apply Optional Guidance to Plan

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
  2. Then run: /workstack:enhance-plan "your guidance here"
```

**Multi-line guidance limitation:**
Note: Guidance must be provided as a single-line string in quotes. Multi-line guidance is not supported.

If no guidance provided: use the original plan as-is

### Step 3: Extract and Preserve Semantic Understanding

Analyze the planning discussion to extract valuable context that implementing agents would find expensive to rediscover. Use the structured template sections to organize discoveries.

**Context Preservation Criteria:**
Include items that meet ANY of these:

- Took time to discover and aren't obvious from code
- Would change implementation if known vs. unknown
- Would cause bugs if missed (especially subtle or delayed bugs)
- Explain WHY decisions were made, not just WHAT was decided

**For each dimension, systematically check the planning discussion:**

#### 1. API/Tool Quirks

Look for discoveries about external systems, libraries, or tools:

Questions to ask:

- Did we discover undocumented behaviors or edge cases?
- Are there timing issues, race conditions, or ordering constraints?
- Did we find version-specific gotchas or compatibility issues?
- Are there performance characteristics that affect design?

Examples to extract:

- "Stripe webhooks often arrive BEFORE API response returns to client"
- "PostgreSQL foreign keys must be created in dependency order within same migration"
- "WebSocket API doesn't guarantee message order for sends <10ms apart"
- "SQLite doesn't support DROP COLUMN in versions before 3.35"

#### 2. Architectural Insights

Look for WHY behind design decisions:

Questions to ask:

- Why was this architectural pattern chosen over alternatives?
- What constraints led to this design?
- How do components interact in non-obvious ways?
- What's the reasoning behind the sequencing or phasing?

Examples to extract:

- "Zero-downtime deployment requires 4-phase migration to maintain rollback capability"
- "State machine pattern prevents invalid state transitions from webhook retries"
- "Webhook handlers MUST be idempotent because Stripe retries for up to 3 days"
- "Database transactions scoped per-webhook-event, not per-API-call, to prevent partial updates"

#### 3. Domain Logic & Business Rules

Look for non-obvious requirements and rules:

Questions to ask:

- Are there business rules that aren't obvious from code?
- What edge cases or special conditions apply?
- Are there compliance, security, or regulatory requirements?
- What assumptions about user behavior or data affect implementation?

Examples to extract:

- "Failed payments trigger 7-day grace period before service suspension, not immediate cutoff"
- "Admin users must retain ALL permissions during migration - partial loss creates security incident"
- "Default permissions for new users during migration must be fail-closed, not empty"
- "Tax calculation must happen before payment intent creation to ensure correct amounts"

#### 4. Complex Reasoning

Look for alternatives considered and decision rationale:

Questions to ask:

- What approaches were considered but rejected?
- Why were certain solutions ruled out?
- What tradeoffs were evaluated?
- How did we arrive at the chosen approach?

Format as:

- **Rejected**: [Approach]
  - Reason: [Why it doesn't work]
  - Also: [Additional concerns]
- **Chosen**: [Selected approach]
  - [Why this works better]

Examples to extract:

- "**Rejected**: Synchronous payment confirmation (waiting for webhook in API call)
  - Reason: Webhooks can take 1-30 seconds, creates timeout issues
  - Also: Connection failures would lose webhook delivery entirely"
- "**Rejected**: Database-level locking (SELECT FOR UPDATE)
  - Reason: Lock held during entire edit session causes head-of-line blocking"
- "**Chosen**: Optimistic locking with version numbers
  - Detects conflicts without blocking, better for real-time collaboration"

#### 5. Known Pitfalls

Look for specific gotchas and anti-patterns:

Questions to ask:

- What looks correct but actually causes problems?
- Are there subtle bugs waiting to happen?
- What mistakes did we avoid during planning?
- What would be easy to get wrong during implementation?

Format as "DO NOT [anti-pattern] - [why it breaks]"

Examples to extract:

- "DO NOT use payment_intent.succeeded event alone - fires even for zero-amount test payments. Check amount > 0."
- "DO NOT store Stripe objects directly in database - schema changes across API versions. Extract needed fields only."
- "DO NOT assume webhook delivery order - charge.succeeded might arrive before payment_intent.succeeded"
- "DO NOT use document.updated_at for version checking - clock skew and same-ms races cause false conflicts"
- "DO NOT migrate superuser permissions first - if migration fails, you've locked out recovery access"

#### Extraction Process

1. **Review the planning conversation** from start to current point
2. **Identify valuable discoveries** using criteria above
3. **Organize into appropriate categories** (API Quirks, Insights, Logic, Reasoning, Pitfalls)
4. **Write specific, actionable items** - not vague generalizations
5. **Link to implementation steps** - ensure every context item connects to at least one step
6. **Flag orphaned context** - context without corresponding steps is probably not relevant

### Step 4: Interactive Plan Enhancement

Analyze the plan for common ambiguities and ask clarifying questions when helpful. Focus on practical improvements that make implementation clearer.

#### Code in Plans: Behavioral, Not Literal

**Rule:** Plans describe WHAT to do, not HOW to code it.

**Include in plans:**

- File paths and function names
- Behavioral requirements
- Success criteria
- Error handling approaches

**Only include code snippets for:**

- Security-critical implementations
- Public API signatures
- Bug fixes showing exact before/after
- Database schema changes

**Example:**
❌ Wrong: `def validate_user(user_id: str | None) -> User: ...`
✅ Right: "Update validate_user() in src/auth.py to use LBYL pattern, check for None, raise appropriate errors"

#### Analyze Plan for Gaps

Examine the plan for common ambiguities:

**Common gaps to look for:**

1. **Vague file references**: "the config file", "update the model", "modify the API"
   - Need: Exact file paths

2. **Unclear operations**: "improve", "optimize", "refactor", "enhance"
   - Need: Specific actions and metrics

3. **Missing success criteria**: Steps without clear completion conditions
   - Need: Testable outcomes

4. **Unspecified dependencies**: External services, APIs, packages mentioned without details
   - Need: Availability, versions, fallbacks

5. **Large scope indicators**:
   - Multiple distinct features
   - Multiple unrelated components
   - Complex interdependencies
   - Need: Consider phase decomposition

6. **Missing reasoning context**: "use the better approach", "handle carefully"
   - Need: Which approach was chosen and WHY
   - Need: What "carefully" means specifically

7. **Vague constraints**: "ensure compatibility", "maintain performance"
   - Need: Specific versions, standards, or metrics
   - Need: Quantifiable requirements

8. **Hidden complexity**: Steps that seem simple but aren't
   - Need: Document discovered complexity
   - Need: Explain non-obvious requirements

#### Ask Clarifying Questions

For gaps identified, ask the user specific questions. Use the AskUserQuestion tool to get answers.

**Question format examples:**

```markdown
I need to clarify a few details to improve the plan:

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

**Reasoning and Context Discovery:**

Beyond file paths and metrics, probe for valuable reasoning and discoveries:

```markdown
**Discovered Constraints:**
During planning, did you discover any constraints that aren't obvious from the code?

- Example: "API doesn't support bulk operations, must process items individually"
- Example: "Database doesn't support transactions across schemas"
- Answers: [Will be included in Context & Understanding section]

**Surprising Interdependencies:**
Did you discover any non-obvious connections between components or requirements?

- Example: "Can't change user model without updating 3 other services due to shared schema"
- Example: "Email sending must complete before payment finalization for audit trail"
- Answers: [Will be included in Context & Understanding section]

**Known Pitfalls:**
Did you discover anything that looks correct but actually causes problems?

- Example: "Using .filter().first() looks safe but returns None without error, use .get() instead"
- Example: "Webhook signature must be verified with raw body, not parsed JSON"
- Answers: [Will be included in Context & Understanding section]

**Rejected Approaches:**
Were any approaches considered but rejected? If so, why?

- Example: "Tried caching at API layer but race conditions made it unreliable, moved to database layer"
- Example: "Considered WebSocket for real-time updates but polling simpler and more reliable for our scale"
- Answers: [Will be included in Context & Understanding section]
```

**Important:**

- Ask all clarifying questions in one interaction (batch them)
- Make questions specific and provide examples
- Allow user to skip questions if they prefer ambiguity
- Context questions should focus on discoveries made during planning, not theoretical concerns

#### Check for Semantic Understanding

After clarifying questions, check if you discovered valuable context during planning. If relevant, include it in the plan's "Context & Understanding" section.

#### Suggest Phase Decomposition (When Helpful)

For complex plans with multiple distinct features or components, suggest breaking into phases:

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

#### Incorporate Enhancements

Based on user responses:

1. **Update file references** with exact paths
2. **Replace vague terms** with specific actions
3. **Add success criteria** to each major step
4. **Structure into phases** if helpful
5. **Include test requirements** where appropriate

#### Plan Templates

**For Single-Phase Plans:**

```markdown
## Implementation Plan: [Title]

### Objective

[Clear goal statement]

### Context & Understanding

Preserve valuable context discovered during planning. Include items that:

- Took time to discover and aren't obvious from code
- Would change implementation if known vs. unknown
- Would cause bugs if missed (especially subtle or delayed bugs)

#### API/Tool Quirks

[Undocumented behaviors, timing issues, version constraints, edge cases]

Example:

- Stripe webhooks often arrive BEFORE API response returns
- PostgreSQL foreign keys must be created in dependency order

#### Architectural Insights

[Why design decisions were made, not just what was decided]

Example:

- Zero-downtime deployment requires 4-phase migration to allow rollback
- State machine pattern prevents invalid state transitions from retries

#### Domain Logic & Business Rules

[Non-obvious requirements, edge cases, compliance rules]

Example:

- Failed payments trigger 7-day grace period, not immediate suspension
- Admin users must retain all permissions during migration (security)

#### Complex Reasoning

[Alternatives considered and why some were rejected]

Example:

- **Rejected**: Synchronous payment confirmation (waiting for webhook)
  - Reason: Webhooks take 1-30s, creates timeout issues
- **Chosen**: Async webhook-driven flow
  - Handles timing correctly regardless of webhook delay

#### Known Pitfalls

[What looks right but causes problems - specific gotchas]

Example:

- DO NOT use payment_intent.succeeded alone - fires for zero-amount tests
- DO NOT store Stripe objects directly - schema changes across API versions

### Implementation Steps

Use hybrid context linking:

- Inline [CRITICAL:] tags for must-not-miss warnings
- "Related Context:" subsections for detailed explanations

1. **[Action]**: [What to do] in `[exact/file/path]`
   [CRITICAL: Any security or breaking change warnings]
   - Success: [How to verify]
   - On failure: [Recovery action]

   Related Context:
   - [Why this approach was chosen]
   - [What constraints or gotchas apply]
   - [Link to relevant Context & Understanding sections above]

2. [Continue pattern...]

### Testing

- Tests are integrated within implementation steps
- Final validation: Run `/ensure-ci`
```

**For Multi-Phase Plans:**

```markdown
## Implementation Plan: [Title]

### Context & Understanding

[Same sections as single-phase plan]

### Phase 1: [Name]

**Branch**: feature-1 (base: main)
**Goal**: [Single objective]

**Steps:**

[Same step format as single-phase]

### Phase 2: [Name]

**Branch**: feature-2 (stacks on: feature-1)
[Continue pattern...]
```

#### Apply Hybrid Context Linking

Before finalizing the plan, ensure context is properly linked to implementation steps:

**Linking Strategy:**

1. **Inline [CRITICAL:] tags** - For must-not-miss warnings in steps
   - Security vulnerabilities
   - Breaking changes
   - Data loss risks
   - Irreversible operations
   - Race conditions or timing requirements

2. **"Related Context:" subsections** - For detailed explanations
   - Link to relevant Context & Understanding sections
   - Explain WHY this approach was chosen
   - Document discovered constraints or gotchas
   - Reference rejected alternatives

**Validation Checklist:**

Before proceeding, verify:

- [ ] Every complex or critical implementation step has appropriate context
- [ ] Security-critical operations have inline [CRITICAL:] warnings
- [ ] Each Context & Understanding item is referenced by at least one step
- [ ] No orphaned context (context without corresponding steps)
- [ ] Context items are specific and actionable, not vague generalizations

**Orphaned Context Handling:**

If context items don't map to any implementation step:

- Either: Add implementation steps that use this context
- Or: Remove the context item (it's probably not relevant)

Context should drive implementation. If context doesn't connect to steps, it's either missing steps or irrelevant.

#### Final Review

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

### Step 5: Output Enhanced Plan

Display the complete enhanced plan to the user as markdown text:

```markdown
## Enhanced Implementation Plan

[Full enhanced plan content with all sections]

---

✅ **Plan enhanced successfully!**

This enhanced plan is now ready to be saved and used to create a worktree.

**Next steps:**

1. Exit plan mode if currently active
2. Run: `/workstack:create-plan-stack`

This will save the plan to disk and create a new worktree for implementation.
```

## Important Notes

- 🟢 **Works in ANY mode** - No plan mode detection or restrictions
- Focuses on enhancement only - no file operations
- All enhancements are optional - users can dismiss suggestions
- Context preservation helps implementing agents avoid re-discovery
- Output is markdown text ready for `/workstack:create-plan-stack`
- Always provide clear feedback at each step
