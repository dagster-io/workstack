---
description: Create a workstack worktree from an implementation plan in context (with interactive enhancement for autonomous execution)
---

# /workstack:create-from-plan

⚠️ **CRITICAL: This command ONLY sets up the workspace - it does NOT implement code!**

## Goal

**Create a workstack worktree from an implementation plan, optionally enhancing it for clarity.**

This command extracts a plan from conversation context, saves it to disk, and creates a worktree for implementation. For complex or unclear plans, it can interactively enhance them through clarifying questions and phase structuring.

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

1. **Check Plan Mode** - If currently in plan mode, inform user to exit and rerun command, then abort
2. **Verify Scope** - Confirm we're in a git repository with workstack available
3. **Detect Plan** - Search conversation for implementation plan
4. **Apply Guidance** - Merge optional guidance into plan (if provided)
5. **Interactive Enhancement** - Analyze plan and ask clarifying questions if needed
6. **Generate Filename** - Derive filename from plan title
7. **Detect Root** - Find worktree root directory
8. **Save Plan** - Write enhanced plan to disk as markdown file
9. **Create Worktree** - Run `workstack create --plan` command
10. **Display Next Steps** - Show commands to switch and implement

## Usage

```bash
/workstack:create-from-plan [guidance]
```

**Examples:**

- `/workstack:create-from-plan` - Create worktree from plan
- `/workstack:create-from-plan "Make error handling more robust and add retry logic"` - Apply guidance to plan
- `/workstack:create-from-plan "Fix: Use LBYL instead of try/except throughout"` - Apply corrections to plan

**For detailed interaction examples, see [EXAMPLES.md](./EXAMPLES.md)**

## Prerequisites

- An implementation plan must exist in conversation
- Current working directory must be in a workstack repository
- The plan should not already be saved to disk at repository root
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

**Plan Extraction:**
✅ Implementation plan extracted from conversation context
✅ If guidance provided, it has been applied to the plan

**File & Worktree Creation:**
✅ Plan saved to `<worktree-root>/<filename>-plan.md`
✅ Worktree created with `workstack create --plan`
✅ Worktree contains `.PLAN.md` file (moved by workstack)
✅ Worktree listed in `workstack list`

**Next Steps:**
✅ Next command displayed: `workstack switch <name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`

## Troubleshooting

### "No plan found in context"

**Cause:** Plan not in conversation or doesn't match detection patterns
**Solution:**

- Ensure plan is in conversation history
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

## Agent Instructions

You are executing the `/workstack:create-from-plan` command. Follow these steps carefully:

### Step 1: Check Plan Mode and Abort (If Active)

**Detection Strategy:**

Plan mode blocks write operations. Test this directly by attempting a harmless write operation.

**How to Detect Plan Mode:**

1. **Generate unique temp filename:**
   - Use current timestamp or random string to ensure uniqueness
   - Format: `/tmp/claude-plan-test-{unique-id}.tmp`
   - Example: `/tmp/claude-plan-test-1699564832.tmp`

2. **Attempt to create test file:**
   - Use Write tool to create the temp file
   - Content: Single space character ` ` (minimal content)
   - This tests write capability without side effects

3. **Interpret the result:**
   - **If Write succeeds** → Plan mode is OFF
     - Immediately use Bash to delete: `rm /tmp/claude-plan-test-{unique-id}.tmp`
     - Proceed to Step 2
   - **If Write fails with ANY error** → Plan mode is ON
     - Display plan mode warning (below)
     - Abort execution immediately

**Why This Works:**

- **Deterministic**: Tests actual write capability, not proxy signals
- **Reliable**: Directly tests the restriction that matters for this command
- **No false positives**: If we can write to /tmp/, we can write plan files
- **No false negatives**: If plan mode blocks writes, this catches it
- **Safe**: /tmp/ location won't pollute repository or user files
- **Self-cleaning**: Temp file deleted immediately after successful test

**If Plan Mode is DETECTED (Write failed):**

Display this message and STOP execution immediately:

```
⚠️ Plan Mode Detected

This command cannot run while plan mode is active (write operations are blocked).

To proceed:
1. Exit plan mode by pressing Shift+Tab
2. Rerun this command: /workstack:create-from-plan

Note: This command requires file write permissions to save plans and create worktrees.
```

**DO NOT proceed to Step 2 if plan mode is detected.**

**If Plan Mode is NOT detected (Write succeeded):**

- Clean up temp file with: `rm /tmp/claude-plan-test-{unique-id}.tmp`
- Continue to Step 2 normally

### Step 2: Verify Scope and Constraints

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

### Step 3: Detect Implementation Plan in Context

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

### Step 4: Apply Optional Guidance to Plan

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

**Output:** Final plan content (original or modified) ready for Step 6 processing

### Step 5: Extract and Preserve Semantic Understanding

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

**Output:** Enhanced plan with populated Context & Understanding sections, ready for Step 6 interactive enhancement

### Step 6: Interactive Plan Enhancement

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

After clarifying questions, check if you discovered valuable context during planning (see "Semantic Understanding & Context Preservation" section). If relevant, include it in the plan's "Context & Understanding" section.

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

See EXAMPLES.md for complete examples of excellent context preservation.

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

Preserve valuable context discovered during planning. Include items that:

- Took time to discover and aren't obvious from code
- Would change implementation if known vs. unknown
- Would cause bugs if missed (especially subtle or delayed bugs)

See EXAMPLES.md for complete examples of excellent context preservation.

#### API/Tool Quirks

[Undocumented behaviors, timing issues, version constraints, edge cases]

#### Architectural Insights

[Why design decisions were made, not just what was decided]

#### Domain Logic & Business Rules

[Non-obvious requirements, edge cases, compliance rules]

#### Complex Reasoning

[Alternatives considered and why some were rejected]

#### Known Pitfalls

[What looks right but causes problems - specific gotchas]

### Phase 1: [Name]

**Branch**: feature-1 (base: main)
**Goal**: [Single objective]

**Steps:**

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

2. Add tests in [test file]
3. Validate with `/ensure-ci`

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

   Example:

   ```markdown
   1. **Create database migration**: Add migration 0001_initial.py
      [CRITICAL: Run backup BEFORE migration. Irreversible schema change.]
   ```

2. **"Related Context:" subsections** - For detailed explanations
   - Link to relevant Context & Understanding sections
   - Explain WHY this approach was chosen
   - Document discovered constraints or gotchas
   - Reference rejected alternatives

   Example:

   ```markdown
   Related Context:

   - Migration is 4-phase to allow rollback (see Architectural Insights)
   - Foreign keys must be created in dependency order (see API/Tool Quirks)
   - See Known Pitfalls for DROP COLUMN version constraint
   ```

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

**Output:** Final enhanced plan content ready for Step 7 processing

### Step 7: Generate Filename from Plan

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
6. Strip any trailing hyphens or slashes: `base_name = base_name.rstrip('-/')`
7. Ensure at least one alphanumeric character remains

**No length restriction:** DO NOT truncate the base name. The base name is limited to 30 characters by `sanitize_worktree_name()`, but the final name (with date suffix) can exceed 30 characters. Workstack no longer truncates after adding the date suffix.

**Resulting names:**

- Filename: `<kebab-case-base>-plan.md` (any length - no LLM truncation)
- Worktree name: `<kebab-case-base>-YY-MM-DD` (base ≤30 chars, final can be ~39 chars)
- Branch name: `<kebab-case-base>-YY-MM-DD` (matches worktree exactly)

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

- "User Authentication System" →
  - Base: `user-authentication-system` (27 chars)
  - Filename: `user-authentication-system-plan.md`
  - Worktree & Branch: `user-authentication-system-25-11-09` (36 chars - exceeds 30!)

- "Version-Specific Dignified Python Kits Structure" →
  - Base: `version-dignified-python-kits` (29 chars, intelligently shortened)
  - Rationale: Removed "specific", "structure"; kept key terms
  - Filename: `version-dignified-python-kits-plan.md`
  - Worktree & Branch: `version-dignified-python-kits-25-11-09` (38 chars - exceeds 30!)

- "Fix: Database Connection Issues" →
  - Base: `fix-database-connection-issues` (30 chars)
  - Filename: `fix-database-connection-issues-plan.md`
  - Worktree & Branch: `fix-database-connection-issues-25-11-09` (39 chars - at max!)

- "Refactor Commands to Use GraphiteOps Abstraction" →
  - Base: `refactor-commands-graphite-ops` (30 chars, intelligently shortened)
  - Rationale: Removed filler words "to", "use"; kept key terms "refactor", "commands", "graphite", "ops"
  - Alternative valid approaches: `refactor-cmds-graphite-ops` (26 chars), `refactor-graphiteops-abstr` (26 chars)
  - Filename: `refactor-commands-graphite-ops-plan.md`
  - Worktree & Branch: `refactor-commands-graphite-ops-25-11-09` (39 chars - at max!)

- "🚀 Awesome Feature!!!" →
  - Base: `awesome-feature` (15 chars, emojis removed)
  - Filename: `awesome-feature-plan.md`
  - Worktree & Branch: `awesome-feature-25-11-09` (24 chars)

- "This Is A Very Long Feature Name That Definitely Exceeds The Thirty Character Limit" →
  - Base: `very-long-feature-name` (22 chars, intelligently shortened)
  - Rationale: Removed redundant words "this", "is", "a", "that", "definitely", "exceeds", etc.; kept meaningful core
  - Alternative valid approaches: `long-feature-exceeds-limit` (26 chars), `very-long-feature-exceeds` (25 chars)
  - Filename: `very-long-feature-name-plan.md`
  - Worktree & Branch: `very-long-feature-name-25-11-09` (31 chars - slightly over 30!)

- "Implement User Profile Settings Page with Dark Mode Support" →
  - Base: `user-profile-settings-dark` (26 chars, intelligently shortened)
  - Rationale: Kept "user", "profile", "settings", "dark"; removed "implement", "page", "with", "mode", "support"
  - Alternative valid approaches: `impl-profile-settings-dark` (26 chars), `user-settings-dark-mode` (23 chars)
  - Filename: `user-profile-settings-dark-plan.md`
  - Worktree & Branch: `user-profile-settings-dark-25-11-09` (35 chars - exceeds 30!)

- "###" (only special chars) → Prompt user for name

### Step 8: Detect Worktree Root

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

### Step 9: Save Plan to Disk

**Pre-save validation:**

1. **Verify filename base length** (CRITICAL):
   - Extract base name from `<derived-filename>` (remove `-plan.md` suffix)
   - MUST be ≤ 30 characters
   - If > 30 characters, this is an implementation bug - the filename generation in Step 7 failed

```
❌ Error: Internal error - filename base exceeds 30 characters

Details: Generated base name '<base>' is <length> characters (max: 30)

This is a bug in the filename generation algorithm. The base should have been
truncated to 30 characters in Step 7.

Suggested action:
  1. Report this as a bug in /workstack:create-from-plan
  2. Manually truncate the plan title and rerun the command
```

2. **Check if file already exists** at `<worktree-root>/<derived-filename>`:

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

### Step 10: Create Worktree with Plan

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

### Step 11: Display Next Steps

After successful worktree creation, provide clear instructions based on plan structure.

**IMPORTANT:** You have NOT implemented any code. Implementation happens after the user switches to the worktree.

**For single-phase plans:**

```markdown
✅ Worktree created: **<worktree-name>**

Plan:

<full-plan-markdown-content>

Branch: `<branch-name>`
Location: `<worktree-path>`

**Next step:**

`workstack switch <worktree_name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`
```

**For multi-phase plans:**

```markdown
✅ Worktree created: **<worktree-name>**

Plan:

<full-plan-markdown-content>

Branch: `<branch-name>`
Location: `<worktree-path>`

**Next step:**

`workstack switch <worktree_name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`
```

**Template Variable Clarification:**

- `<full-plan-markdown-content>` refers to the final enhanced plan markdown that was saved in Step 9
- Output the complete plan text verbatim (all headers, sections, steps)
- This is the same content that was written to `<worktree-root>/<derived-filename>`
- The plan content is already in memory from previous steps - no additional file reads required
- Preserve all markdown formatting (headers, lists, code blocks)
- Do not truncate or summarize the plan

**Note:** The final output the user sees should be the single copy-pasteable command above. No additional text after that command.

## Important Notes

- 🔴 **This command does NOT write code** - only creates workspace with enhanced plan
- Searches conversation for implementation plans
- Enhances plans through clarifying questions when helpful
- Suggests phase decomposition for complex plans with multiple features
- All enhancements are optional - users can dismiss suggestions
- Filename derived from plan title, prompts user if extraction fails
- All errors follow consistent template with details and suggested actions
- This command does NOT switch directories or execute the plan
- User must manually run `workstack switch` and `/workstack:implement-plan` to begin implementation
- The `--permission-mode acceptEdits` flag is included to automatically accept edits during implementation
- Always provide clear feedback at each step
- **Plan mode detection uses write-test** - attempts temp file creation to verify write capability
