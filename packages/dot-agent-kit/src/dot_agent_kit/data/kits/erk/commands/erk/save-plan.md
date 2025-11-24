---
description: Extract plan from conversation, fully enhance it, and create GitHub issue directly
---

# /erk:save-context-enriched-plan

⚠️ **CRITICAL: This command creates a GitHub issue with the plan - it does NOT create worktrees or implement code!**

## Goal

**Extract an implementation plan from conversation, enhance it for autonomous execution, and create a GitHub issue directly.**

This command extracts a plan from conversation context, optionally applies guidance, interactively enhances it through clarifying questions, and creates a GitHub issue with the enhanced plan content.

**What this command does:**

- ✅ Find plan in conversation
- ✅ Apply optional guidance to plan
- ✅ Interactively enhance plan for autonomous execution
- ✅ Extract semantic understanding and context
- ✅ Structure complex plans into phases (when beneficial)
- ✅ Create GitHub issue with enhanced plan

**What happens AFTER:**

- ⏭️ Implement directly: `erk implement <issue>`

## What Happens

When you run this command, these steps occur:

1. **Verify Scope** - Confirm we're in a git repository
2. **Detect Plan** - Search conversation for implementation plan
   3-5. **Enrichment Process** - Apply guidance, extract understanding, and enhance interactively
3. **Validate Repository** - Ensure GitHub CLI is available and repository has issues enabled
4. **Create GitHub Issue** - Create issue with enhanced plan content and `erk-plan` label

## Usage

```bash
/erk:save-context-enriched-plan [guidance]
```

**Examples:**

- `/erk:save-context-enriched-plan` - Create GitHub issue with enhanced plan
- `/erk:save-context-enriched-plan "Make error handling more robust and add retry logic"` - Apply guidance to plan
- `/erk:save-context-enriched-plan "Fix: Use LBYL instead of try/except throughout"` - Apply corrections to plan

## Prerequisites

- An implementation plan must exist in conversation
- Current working directory must be in a git repository
- GitHub CLI (gh) must be installed and authenticated
- Repository must have issues enabled
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

6. **Raw Discoveries Log**
   - Everything discovered during planning, even if minor
   - Examples: Version numbers, config formats, conventions observed

7. **Planning Artifacts**
   - Code snippets examined, commands run, configurations discovered
   - Example: "Checked auth.py lines 45-67 for validation pattern"

8. **Implementation Risks**
   - Technical debt, uncertainties, performance concerns, security considerations
   - Example: "No caching layer could cause issues at scale"

**Inclusion Philosophy:** Cast a wide net - over-document rather than under-document. Include anything that:

- Took ANY time to discover (even 30 seconds of research)
- MIGHT influence implementation decisions
- Could POSSIBLY cause bugs or confusion
- Wasn't immediately obvious on first glance
- Required any clarification or discussion
- Involved ANY decision between alternatives
- Required looking at documentation or examples

**Remember:** It's easier for implementing agents to skip irrelevant context than to rediscover missing context. When in doubt, include it.

**How It's Used:** This understanding gets captured in the "Context & Understanding" section of enhanced plans, linked to specific implementation steps.

## Success Criteria

This command succeeds when ALL of the following are true:

**Plan Extraction:**
✅ Implementation plan extracted from conversation context
✅ If guidance provided, it has been applied to the plan
✅ Semantic understanding extracted and integrated

**Issue Creation:**
✅ GitHub issue created with enhanced plan content
✅ Issue has `erk-plan` label applied
✅ Issue title matches plan title

**Output:**
✅ JSON output provided with issue URL and number
✅ Four copy-pastable commands displayed (1 view, 3 implement variants)
✅ All commands use actual issue number, not placeholders
✅ Next steps clearly communicated to user

## Troubleshooting

### "No plan found in context"

**Cause:** Plan not in conversation or doesn't match detection patterns
**Solution:**

- Ensure plan is in conversation history
- Plan should have headers like "## Implementation Plan" or numbered steps
- Re-paste plan in conversation if needed

### "GitHub authentication failed"

**Cause:** GitHub CLI not authenticated or credentials expired
**Solution:**

- Run `gh auth login` to authenticate
- Check authentication status: `gh auth status`
- Verify you have permission to create issues in the repository

### "Failed to create GitHub issue"

**Cause:** Network error, repository has issues disabled, or API failure
**Solution:**

- Check network connectivity
- Verify repository has issues enabled in GitHub settings
- Check GitHub API status: https://www.githubstatus.com
- Retry the command after resolving the issue

### Enhancement suggestions not applied correctly

**Cause:** Ambiguous user responses or misinterpretation
**Solution:**

- Be specific in responses to clarifying questions
- Use clear action words: "Fix:", "Add:", "Change:", "Reorder:"

---

## Agent Instructions

You are executing the `/erk:save-context-enriched-plan` command. Follow these steps carefully:

---

🔴 **CRITICAL: YOU ARE ONLY CREATING A GITHUB ISSUE - DO NOT IMPLEMENT**

- DO NOT use Edit or Write tools to modify codebase
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY create a GitHub issue with the enhanced plan

---

### Step 0: Verify Scope and Constraints

🔴 **REMINDER: YOU ARE ONLY CREATING A GITHUB ISSUE**

- DO NOT use Edit or Write tools to modify codebase
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY create a GitHub issue with the enhanced plan

**Error Handling Template:**
All errors must follow this format:

```
❌ Error: [Brief description in 5-10 words]

Details: [Specific error message, relevant context, or diagnostic info]

Suggested action: [1-3 concrete steps to resolve]
```

**YOUR ONLY TASKS:**

1. Extract implementation plan from conversation
2. Apply guidance modifications if provided
3. Extract semantic understanding from planning discussion
4. Interactively enhance plan for autonomous execution
5. Create GitHub issue with enhanced plan content
6. Provide JSON output with issue URL and number

**FORBIDDEN ACTIONS:**

- Writing ANY code files (.py, .ts, .js, etc.)
- Making ANY edits to existing codebase
- Creating ANY worktrees
- Implementing ANY part of the plan

**ALLOWED TOOLS ONLY:**

- ✅ Read (to examine conversation context)
- ✅ AskUserQuestion (for clarification)
- ✅ Bash (for git commands and kit CLI commands)

**IF YOU USE:** Edit, Write (to codebase files), Task, NotebookEdit, SlashCommand, etc.
→ 🔴 **YOU ARE IMPLEMENTING, NOT PLANNING. STOP IMMEDIATELY.**

This command only creates the GitHub issue. Implementation happens via `erk implement <issue>`.

### Step 1: Detect Implementation Plan in Context

🔴 **REMINDER: YOU ARE ONLY CREATING A GITHUB ISSUE**

- DO NOT use Edit or Write tools to modify codebase
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY create a GitHub issue with the enhanced plan

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

### Steps 2-4: Enrichment Process

@../docs/enrichment-process.md

Apply the complete enrichment process to enhance the extracted plan for autonomous execution. This includes:

- Step 1: Apply optional guidance (if provided as command argument)
- Step 2: Extract semantic understanding from planning discussion
- Step 3: Interactive enhancement with clarifying questions

[Continue with Step 5: Validate Repository...]

### Step 5: Validate Repository and GitHub CLI

🔴 **REMINDER: YOU ARE ONLY CREATING A GITHUB ISSUE**

- DO NOT use Edit or Write tools to modify codebase
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY create a GitHub issue with the enhanced plan

Execute: `git rev-parse --show-toplevel`

This confirms we're in a git repository and returns the repository root path.

**If the command fails:**

```
❌ Error: Could not detect repository root

Details: Not in a git repository or git command failed

Suggested action:
  1. Ensure you are in a valid git repository
  2. Run: git status (to verify git is working)
  3. Check if .git directory exists
```

**Verify GitHub CLI is available:**

Check that `gh` command is available and authenticated.

**If GitHub CLI is not available or not authenticated:**

```
❌ Error: GitHub CLI not available or not authenticated

Details: gh command failed or returned authentication error

Suggested action:
  1. Install GitHub CLI: https://cli.github.com/
  2. Authenticate with: gh auth login
  3. Verify authentication: gh auth status
```

### Step 6: Verify You Did Not Implement

🔴 **CRITICAL: VERIFY YOU ONLY GATHERED INFORMATION**

Before creating the GitHub issue, confirm you ONLY gathered information and did NOT implement anything.

**Check your tool usage in this session:**

- ✅ Did you use Read to examine conversation? → CORRECT
- ✅ Did you use AskUserQuestion for clarifications? → CORRECT
- ✅ Did you use Bash for git/kit commands? → CORRECT
- ❌ Did you use Edit on ANY file? → **VIOLATION - STOP**
- ❌ Did you use Write to modify codebase? → **VIOLATION - STOP**
- ❌ Did you use Task, SlashCommand, or other tools? → **VIOLATION - STOP**

**If you violated restrictions:**

```
❌ Error: Implementation attempted during plan creation

Details: You used [tool name] which is forbidden in /erk:save-context-enriched-plan

This command ONLY creates a GitHub issue. Implementation happens in erk implement.

Suggested action:
  1. Stop immediately - do NOT create the issue
  2. Report what tools you used incorrectly
  3. User should restart the command without implementing
```

**If all checks passed:** Proceed to Step 7 to create the GitHub issue.

### Step 7: Create GitHub Issue

🔴 **REMINDER: YOU ARE ONLY CREATING A GITHUB ISSUE**

- DO NOT use Edit or Write tools to modify codebase
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY create a GitHub issue with the enhanced plan

**Create the issue using kit CLI command:**

```bash
issue_url=$(dot-agent kit-command erk create-enriched-plan-from-context --plan-content "$enhanced_plan_content")
if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to create GitHub issue" >&2
    exit 1
fi
```

The kit CLI command:

- Reads plan content from --plan-content option
- Extracts title from plan for issue title
- Creates issue with `erk-plan` label
- Returns issue URL

**Extract issue number from URL:**

Parse the issue number from the returned URL (e.g., `https://github.com/org/repo/issues/123` → `123`)

**If issue creation fails:**

```
❌ Error: Failed to create GitHub issue

Details: [specific error from kit CLI command]

Suggested action:
  1. Verify GitHub CLI (gh) is installed and authenticated
  2. Check repository has issues enabled
  3. Verify network connectivity
  4. Check gh auth status
```

**Output success message (REQUIRED - MUST use this exact format):**

After creating the issue, you MUST:

1. Extract the issue number from the URL
2. Output the message below with the actual issue number substituted
3. Include ALL four copy-pastable commands

Format:

```markdown
✅ GitHub issue created: #<number>
<issue-url>

Next steps:

View Issue: gh issue view <number> --web
Interactive Execution: erk implement <number>
Dangerous Interactive Execution: erk implement <number> --dangerous
Yolo One Shot: erk implement <number> --yolo

---

{"issue_number": <number>, "issue_url": "<url>", "status": "created"}
```

**Verify Output Format:**

Before finishing, confirm your output includes:

- ✅ Issue number and URL on first line
- ✅ "Next steps:" header
- ✅ Four commands with actual issue number (not placeholder)
- ✅ JSON metadata with issue_number, issue_url, and status
- ❌ NO placeholders like <number> or <url> in final output

## Important Notes

- 🔴 **This command does NOT create worktrees** - only creates GitHub issue with enhanced plan
- Searches conversation for implementation plans
- Enhances plans through clarifying questions when helpful
- Suggests phase decomposition for complex plans with multiple features
- All enhancements are optional - users can dismiss suggestions
- GitHub issue title derived from plan title
- All errors follow consistent template with details and suggested actions
- User can edit the issue after creation using GitHub UI or `gh issue edit`
- Always provide clear feedback at each step
- Issue becomes immediate source of truth (no disk files involved)
