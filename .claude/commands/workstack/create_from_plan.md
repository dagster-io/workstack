---
description: Create a workstack worktree from an implementation plan in context (with optional guidance)
---

# /workstack:create_from_plan

⚠️ **CRITICAL: This command ONLY sets up the workspace - it does NOT implement code!**

**What this command does:**

- ✅ Find plan in conversation
- ✅ Apply optional guidance to plan
- ✅ Save plan to disk
- ✅ Create worktree with `workstack create --plan`

**What happens AFTER (in separate command):**

- ⏭️ Switch to worktree: `workstack switch <name>`
- ⏭️ Implement the plan: `/workstack:implement_plan`

## What Happens

When you run this command, these 8 steps occur:

1. **Verify Scope** - Confirm we're in a git repository with workstack available
2. **Detect Plan** - Search last 5-10 messages for implementation plan
3. **Apply Guidance** - Merge optional guidance into plan (if provided)
4. **Generate Filename** - Derive filename from plan title
5. **Detect Root** - Find worktree root directory
6. **Save Plan** - Write plan to disk as markdown file
7. **Create Worktree** - Run `workstack create --plan` command
8. **Display Next Steps** - Show commands to switch and implement

## Usage

```bash
/workstack:create_from_plan [guidance]
```

**Examples:**

- `/workstack:create_from_plan` - Create worktree from plan as-is
- `/workstack:create_from_plan "Make error handling more robust and add retry logic"` - Apply guidance before creating worktree
- `/workstack:create_from_plan "Fix: Use LBYL instead of try/except throughout"` - Apply corrections to plan

## Prerequisites

- An implementation plan must exist in recent conversation (last 5-10 messages)
- Current working directory must be in a workstack repository
- The plan should not already be saved to disk at repository root
- (Optional) Guidance text for final corrections/additions to the plan

## Success Criteria

This command succeeds when ALL of the following are true:

✅ Implementation plan extracted from conversation context
✅ Guidance applied (if provided) and merged into plan
✅ Plan saved to `<worktree-root>/<filename>-plan.md`
✅ Worktree created with `workstack create --plan`
✅ Worktree contains `.PLAN.md` file (moved by workstack)
✅ User shown command to switch and implement

**Verification:**
After command completes, these should be true:

- File exists: `<worktree-root>/<filename>-plan.md`
- Worktree listed in: `workstack list`
- Next command ready: `workstack switch <name> && claude "/workstack:implement_plan"`

## Performance Notes

**Expected execution time:** 10-30 seconds

**Breakdown:**

- Plan detection: 2-5 seconds (depends on context size)
- Guidance application: 3-10 seconds (AI processing, if used)
- File operations: < 1 second
- Worktree creation: 2-10 seconds (depends on repository size)
- JSON parsing: < 1 second

**Factors affecting speed:**

- Conversation length (for plan detection)
- Guidance complexity (for AI merging)
- Repository size (for worktree creation)
- Disk I/O speed

**If command takes > 60 seconds:** Something is wrong

- Check if workstack create is hanging
- Verify disk space and permissions
- Check git repository health: `git fsck`

## Troubleshooting

### "No plan found in context"

**Cause:** Plan not in recent conversation or doesn't match detection patterns
**Solution:**

- Ensure plan is in last 5-10 messages
- Plan should have headers like "## Implementation Plan" or numbered steps
- Must contain at least 2 implementation keywords: "implement", "create", "update", "refactor", "test", "code", "function", "class"
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

### Guidance not applied correctly

**Cause:** Ambiguous guidance or AI misinterpretation
**Solution:**

- Be specific: "Change Step 3 to use pathlib" not "use pathlib"
- Use clear action words: "Fix:", "Add:", "Change:", "Reorder:"
- Or skip guidance and edit the .PLAN.md file after creation

---

## Agent Instructions

You are executing the `/workstack:create_from_plan` command. Follow these steps carefully:

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
2. Apply guidance modifications if provided
3. Save plan to disk as markdown file
4. Run `workstack create --plan <file>`
5. Display next steps to user

**FORBIDDEN ACTIONS:**

- Writing ANY code files (.py, .ts, .js, etc.)
- Making ANY edits to existing codebase
- Running ANY commands except `git rev-parse` and `workstack create`
- Implementing ANY part of the plan

This command sets up the workspace. Implementation happens in the worktree via `/workstack:implement_plan`.

### Step 2: Detect Implementation Plan in Context

Search the last 5-10 messages in conversation for an implementation plan:

**Search strategy:**

1. Work backwards from most recent messages
2. Stop at first complete plan found
3. Look for markdown content with structure

**What constitutes a complete plan:**

- Minimum 100 characters
- Contains headers (# or ##) OR numbered lists OR bulleted lists
- Must include at least 2 implementation keywords: "implement", "create", "update", "refactor", "test", "code", "function", "class"
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
  2. Plan should have headers and implementation keywords
  3. Re-paste plan in conversation if needed
```

**Plan validation:**

- Must be at least 100 characters
- Must contain structure (numbered lists, bulleted lists, or multiple headers)
- Must contain implementation keywords
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
  2. Then run: /workstack:create_from_plan "your guidance here"
```

**Multi-line guidance limitation:**
Note: Guidance must be provided as a single-line string in quotes. Multi-line guidance is not supported.

If no guidance provided: use the original plan as-is

**Output:** Final plan content (original or modified) ready for Step 4 processing

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

**Fallback for invalid names:**
If cleanup results in empty string or no alphanumeric chars: use "implementation-plan.md"

**Example transformations:**

- "User Authentication System" → `user-authentication-system-plan.md`
- "Fix: Database Connection Issues" → `fix-database-connection-issues-plan.md`
- "🚀 Awesome Feature!!!" → `awesome-feature-plan.md`
- Very long title (200 chars) → Truncated to 100 chars + `-plan.md`
- "###" (only special chars) → `implementation-plan.md`

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
- Content: Full plan markdown content
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

Execute: `workstack create --plan <worktree-root>/<filename> --json`

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

After successful worktree creation, provide clear instructions.

**IMPORTANT:** You have NOT implemented any code. Implementation happens after the user switches to the worktree.

Use the following output format:

```markdown
✅ Worktree created: **<worktree-name>**

Plan: `<filename>`
Branch: `<branch-name>`
Location: `<worktree-path>`

**Next step:**

`workstack switch <worktree-name> && claude "/workstack:implement_plan"`
```

**Note:** The final output the user sees should be the single copy-pasteable command above. No additional text after that command.

## Important Notes

- 🔴 **This command does NOT write code** - only creates workspace with plan
- Searches last 5-10 messages for implementation plans
- Plan must be at least 100 characters with structure and implementation keywords
- Guidance is classified as Correction, Addition, Clarification, or Reordering
- Filename derived from plan title, max 100 chars, fallback to "implementation-plan.md"
- All errors follow consistent template with details and suggested actions
- This command does NOT switch directories or execute the plan
- User must manually run `workstack switch` and `/workstack:implement_plan` to begin implementation
- Always provide clear feedback at each step
