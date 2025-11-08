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

**Plan Mode Handling:**

This command cannot run while in plan mode. The workflow is:

1. User presents a plan (optionally in plan mode)
2. User invokes `/workstack:create-from-plan`
3. If in plan mode, command informs user to exit plan mode and rerun, then aborts
4. If not in plan mode, extracts, enhances, and saves the plan to disk
5. Creates worktree with the plan
6. User runs: `workstack switch <name> && claude --permission-mode acceptEdits "/workstack:implement-plan"`
7. Implementation happens in the new worktree

**Remember:** This command only prepares the workspace - actual code implementation happens after switching to the worktree.

### Step 1: Check Plan Mode and Abort (If Active)

**Check if currently in plan mode:**

Plan mode is indicated by the presence of an explicit system reminder tag in the **CURRENT user message context** (not historical messages).

**How to detect plan mode:**

Check for this **exact system reminder tag** in the **MOST RECENT system reminders** (those appearing immediately before/with the user's current request):

```
<system-reminder>
Plan mode is active. The user indicated that they do not want you to execute yet...
</system-reminder>
```

**Detection logic:**

- If this system reminder tag appears in the CURRENT message context → Plan mode is ACTIVE
- If this system reminder tag is absent from recent context → Plan mode is NOT active
- **CRITICAL**: Ignore system reminders from earlier in conversation history
- Only check reminders that appear with or immediately before the current command invocation
- Do NOT use conversation content, context, or other heuristics to determine plan mode status
- ONLY the presence of this explicit system tag in CURRENT context indicates plan mode

**If in plan mode:**

1. Do NOT proceed with any other steps
2. Display this message to the user:

```
⚠️ This command cannot run in plan mode.

Please exit plan mode first, then rerun this command:

/workstack:create-from-plan
```

3. STOP execution immediately - do NOT continue to Step 2

**If NOT in plan mode:**

- Skip this step and proceed directly to Step 2

This ensures the command only runs in execution mode, not planning mode.

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

### Step 5: Apply Semantic Understanding

Apply the semantic understanding principles from the "Semantic Understanding & Context Preservation" section above when enhancing the plan. This includes capturing API quirks, architectural insights, domain logic, reasoning trails, and known pitfalls that would be expensive for the implementing agent to rediscover.

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

**Important:**

- Ask all clarifying questions in one interaction (batch them)
- Make questions specific and provide examples
- Allow user to skip questions if they prefer ambiguity

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

Include semantic understanding captured during planning (see section above)

### Implementation Steps

1. **[Action]**: [What to do] in `[exact/file/path]`
   - Success: [How to verify]
   - On failure: [Recovery action]

2. [Continue pattern...]

### Testing

- Tests are integrated within implementation steps
- Final validation: Run `/ensure-ci`
```

**For Multi-Phase Plans:**

```markdown
## Implementation Plan: [Title]

### Context & Understanding

[Semantic understanding sections as above]

### Phase 1: [Name]

**Branch**: feature-1 (base: main)
**Goal**: [Single objective]

**Steps:**

1. [Action] in [file]
2. Add tests in [test file]
3. Validate with `/ensure-ci`

### Phase 2: [Name]

**Branch**: feature-2 (stacks on: feature-1)
[Continue pattern...]
```

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

**No length restriction:** DO NOT truncate the base name. Workstack will handle truncation after adding the date prefix to ensure worktree and branch names match at exactly 30 characters. Your job is only to convert the title to valid kebab-case format.

**Resulting names:**

- Filename: `<kebab-case-base>-plan.md` (any length - no LLM truncation)
- Worktree name: `YY-MM-DD-<kebab-case-base>` truncated to 30 chars by workstack
- Branch name: `YY-MM-DD-<kebab-case-base>` truncated to 30 chars by workstack (matches worktree)

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
  - Base: `user-authentication-system` (24 chars, no shortening needed)
  - Filename: `user-authentication-system-plan.md`
  - Worktree & Branch: `user-authentication-system`

- "Fix: Database Connection Issues" →
  - Base: `fix-database-connection-issues` (29 chars, no shortening needed)
  - Filename: `fix-database-connection-issues-plan.md`
  - Worktree & Branch: `fix-database-connection-issues`

- "Refactor Commands to Use GraphiteOps Abstraction" →
  - Base: `refactor-commands-graphite-ops` (30 chars, intelligently shortened)
  - Rationale: Removed filler words "to", "use"; kept key terms "refactor", "commands", "graphite", "ops"
  - Alternative valid approaches: `refactor-cmds-graphite-ops` (26 chars), `refactor-graphiteops-abstr` (26 chars)
  - Filename: `refactor-commands-graphite-ops-plan.md`
  - Worktree & Branch: `refactor-commands-graphite-ops`

- "🚀 Awesome Feature!!!" →
  - Base: `awesome-feature` (15 chars, emojis removed)
  - Filename: `awesome-feature-plan.md`
  - Worktree & Branch: `awesome-feature`

- "This Is A Very Long Feature Name That Definitely Exceeds The Thirty Character Limit" →
  - Base: `very-long-feature-name` (22 chars, intelligently shortened)
  - Rationale: Removed redundant words "this", "is", "a", "that", "definitely", "exceeds", etc.; kept meaningful core
  - Alternative valid approaches: `long-feature-exceeds-limit` (26 chars), `very-long-feature-exceeds` (25 chars)
  - Filename: `very-long-feature-name-plan.md`
  - Worktree & Branch: `very-long-feature-name`

- "Implement User Profile Settings Page with Dark Mode Support" →
  - Base: `user-profile-settings-dark` (26 chars, intelligently shortened)
  - Rationale: Kept "user", "profile", "settings", "dark"; removed "implement", "page", "with", "mode", "support"
  - Alternative valid approaches: `impl-profile-settings-dark` (26 chars), `user-settings-dark-mode` (23 chars)
  - Filename: `user-profile-settings-dark-plan.md`
  - Worktree & Branch: `user-profile-settings-dark`

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

```

```
