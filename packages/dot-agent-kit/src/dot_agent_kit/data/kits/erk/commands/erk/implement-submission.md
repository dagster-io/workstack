---
description: Execute the implementation plan from .submission/ folder (remote AI implementation via GitHub Actions)
---

# /erk:implement-submission

This command reads and executes the `.submission/plan.md` file from the current directory. It is designed to run in GitHub Actions CI environment after `erk submit` has copied `.plan/` to `.submission/`.

## Usage

```bash
/erk:implement-submission
```

## Prerequisites

- Must be in a worktree directory that contains `.submission/` folder
- Typically runs in GitHub Actions CI environment
- `.submission/plan.md` should contain a valid implementation plan
- **DO NOT run this locally** - use `/erk:implement-plan` for local implementation

## What Happens

When you run this command:

1. Verifies `.submission/plan.md` exists in the current directory
2. Reads and parses the implementation plan
3. Creates todo list for tracking progress
4. Executes each phase of the plan sequentially
5. Updates `.submission/progress.md` with step completions
6. Runs iterative CI validation (max 5 attempts)
7. Cleans up `.submission/` folder after success
8. Creates or updates pull request with results

## Expected Outcome

- Implementation plan executed according to specifications
- Code changes follow project coding standards (if defined)
- All CI checks pass after iterative fixes
- Pull request created or updated with "ai-generated" label
- `.submission/` folder removed after completion

---

## Agent Instructions

You are executing the `/erk:implement-submission` command. Follow these steps carefully:

### Step 1: Verify .submission/plan.md Exists

Check that `.submission/plan.md` exists in the current directory.

If not found:

```
❌ Error: No submission folder found in current directory

This command must be run from a worktree directory that contains a .submission/ folder with plan.md.

This typically means:
1. This command is being run in the wrong environment (should be GitHub Actions)
2. The .submission/ folder was already cleaned up from a previous run
3. `erk submit` was not run before this command

For local implementation:
1. Use `/erk:implement-plan` command instead
2. This command is only for remote implementation via GitHub Actions
```

### Step 2: Read the Plan File

Read `.submission/plan.md` from the current directory to get the full implementation plan.

Parse the plan to understand:

- Overall goal and context
- **Context & Understanding sections** - Extract valuable discoveries and insights:
  - **API/Tool Quirks**: Undocumented behaviors, timing issues, edge cases
  - **Architectural Insights**: WHY decisions were made, not just what
  - **Domain Logic & Business Rules**: Non-obvious requirements and constraints
  - **Complex Reasoning**: Approaches considered, rejected alternatives and why
  - **Known Pitfalls**: What looks right but causes problems
- Individual phases or tasks
- **Critical warnings** marked with `[CRITICAL:]` tags in implementation steps
- **Related Context subsections** that link steps to Context & Understanding
- Dependencies between tasks
- Success criteria
- Any special requirements or constraints

**IMPORTANT - Context Consumption:**

The Context & Understanding section contains expensive discoveries made during planning. Ignoring this context may cause:

- Implementing solutions that were already proven not to work
- Missing security vulnerabilities or race conditions
- Violating discovered constraints (API limitations, timing requirements)
- Making mistakes that were explicitly documented as pitfalls

Pay special attention to:

- `[CRITICAL:]` tags in steps - these are must-not-miss warnings
- "Related Context:" subsections - these explain WHY and link to detailed context
- "DO NOT" items in Known Pitfalls - these prevent specific bugs
- Rejected approaches in Complex Reasoning - these explain what doesn't work

### Step 2.5: Understanding Progress.md Structure

The `.submission/progress.md` file tracks implementation progress using checkboxes AND YAML front matter (for files created after 2025-01-17).

**Front Matter Format:**

```yaml
---
completed_steps: N
total_steps: M
---

# Progress Tracking

- [ ] 1. First step
- [x] 2. Second step (completed)
- [ ] 3. Third step
```

**Key Points:**

- **Checkboxes are source of truth**: `- [ ]` (incomplete) and `- [x]` (complete)
- **Front matter must stay synchronized**: The `completed_steps` field must match the count of checked boxes
- **Progress emoji indicators**: Used by `erk status` to show: ⚪ (0%), 🟡 (1-99%), 🟢 (100%)
- **Backward compatibility**: Older progress.md files may lack front matter - this is OK, just skip front matter updates for those files

**When to Update Front Matter:**

When marking a step complete, you MUST:

1. Change the checkbox from `- [ ]` to `- [x]`
2. IF the file starts with `---` (has front matter):
   - Count the total number of checked boxes in the entire file
   - Update the `completed_steps:` line with the new count
   - DO NOT change the `total_steps:` line
3. IF the file doesn't start with `---` (no front matter):
   - Skip the front matter update entirely
   - Just update the checkbox

This keeps progress indicators accurate in real-time during plan execution.

### Step 3: Create TodoWrite Entries

Create todo list entries for each major phase in the plan to track progress.

- Use clear, descriptive task names
- Set all tasks to "pending" status initially
- Include both `content` and `activeForm` for each task

Example:

```json
[
  {
    "content": "Create noun-based command structure",
    "status": "pending",
    "activeForm": "Creating noun-based command structure"
  },
  {
    "content": "Merge init and install commands",
    "status": "pending",
    "activeForm": "Merging init and install commands"
  }
]
```

### Step 4: Execute Each Phase Sequentially

For each phase in the plan:

1. **Mark phase as in_progress** before starting
2. **Read task requirements** carefully
3. **Check relevant coding standards** from project documentation (if available)
4. **Implement the code** following these standards:
   - NEVER use try/except for control flow - use LBYL (Look Before You Leap)
   - Use Python 3.13+ type syntax (list[str], str | None, NOT List[str] or Optional[str])
   - NEVER use `from __future__ import annotations`
   - Use ABC for interfaces, never Protocol
   - Check path.exists() before path.resolve() or path.is_relative_to()
   - Use absolute imports only
   - Use click.echo() in CLI code, not print()
   - Add check=True to subprocess.run()
   - Keep indentation to max 4 levels - extract helpers if deeper
   - If plan mentions tests, follow patterns in project test documentation (if available)
5. **Verify implementation** against standards
6. **Mark phase as completed** when done:
   - Edit `.submission/progress.md` to change checkbox from `- [ ]` to `- [x]`
   - If front matter exists (file starts with `---`):
     - Count total checked boxes in the entire file
     - Edit the `completed_steps:` line in front matter with new count
     - Do NOT change the `total_steps:` line
   - If no front matter exists, skip the front matter update
7. **Report progress**: what was done and what's next
8. **Move to next phase**

**IMPORTANT - Progress Tracking:**

The new `.submission/` folder structure for remote execution:

1. **`.submission/plan.md` (immutable reference)**: Contains Objective, Context & Understanding, Implementation Steps/Phases, Testing. This file should NEVER be edited during implementation.

2. **`.submission/progress.md` (mutable tracking)**: Contains checkboxes for all steps extracted from plan.md. This is the ONLY file that should be updated during implementation.

When updating progress:

- Only edit `.submission/progress.md` - never touch `.submission/plan.md`
- Mark checkboxes as completed: `- [x]` instead of `- [ ]`
- Simple find-replace operation: no risk of corrupting the plan
- Progress format example:

  ```markdown
  # Progress Tracking

  - [ ] 1. Create module
  - [x] 2. Add tests
  - [ ] 3. Update documentation
  ```

**Example progress.md update:**

Before:

```yaml
---
completed_steps: 2
total_steps: 5
---

# Progress Tracking

- [x] 1. Create module
- [x] 2. Add tests
- [ ] 3. Update documentation  ← marking this complete
- [ ] 4. Add integration tests
- [ ] 5. Update changelog
```

After:

```yaml
---
completed_steps: 3  ← incremented from 2 to 3
total_steps: 5      ← unchanged
---

# Progress Tracking

- [x] 1. Create module
- [x] 2. Add tests
- [x] 3. Update documentation  ← marked complete
- [ ] 4. Add integration tests
- [ ] 5. Update changelog
```

### Step 5: Follow Erk Coding Standards

Project coding standards (if defined) OVERRIDE any conflicting guidance in the plan.

Key standards:

- Exception handling: LBYL, not EAFP
- Type annotations: Modern Python 3.13+ syntax
- Path operations: Check .exists() first
- Dependency injection: ABC, not Protocol
- Imports: Absolute only
- CLI: Use click.echo()
- Code style: Max 4 indentation levels

### Step 6: Report Progress

After completing each major phase, provide an update:

```
✅ Phase X complete: [Brief description]

Changes made:
- [Change 1]
- [Change 2]

Next: [What's coming next]
```

### Step 7: Final Verification

After all phases are complete:

1. Confirm all tasks were executed
2. Verify all success criteria are met
3. Note any deviations from the plan (with justification)
4. Provide summary of changes

### Step 8: Final Verification

After completing all implementation steps:

1. **Check for project documentation** at repository root:
   - Look for `CLAUDE.md` or `AGENTS.md` files
   - If found, read these files for CI/testing instructions
   - Follow any specific commands or workflows documented there

2. **Run project-specific CI checks**:
   - If documentation specifies CI commands, use those
   - Otherwise, run common checks if tools are available:
     - Linting: `ruff check .` or equivalent
     - Type checking: `pyright` or equivalent
     - Tests: `pytest` or equivalent
     - Formatting: `ruff format .` or equivalent

3. **Verify all tests pass** before considering implementation complete

4. **Address any failures** by returning to relevant implementation steps

### Step 9: Run CI and Fix Issues Iteratively (SUBMISSION WORKFLOW)

**CRITICAL: This step is ONLY for .submission/ folders (remote implementation)**

Check if current directory contains `.submission/` folder - you should already have verified this in Step 1.

**Iterative CI Process (max 5 attempts):**

For each attempt (numbered 1-5):

1. Run the fast CI checks: `/fast-ci` (unit tests + pyright)
2. If all checks pass: Break out of loop, proceed to Step 10
3. If checks fail: Read the error output carefully
4. Analyze the failures and fix them
5. Increment attempt counter
6. If max attempts reached (attempt 5 failed): Exit with error message, DO NOT proceed to cleanup

**Maximum Attempts Protection:**

- This prevents infinite loops in automated CI
- If you reach attempt 5 and tests still fail, stop and report the error
- Document which attempt failed and what the error was

### Step 10: Clean Up and Create/Update PR (SUBMISSION WORKFLOW)

**CRITICAL: Only run this step if CI passed in Step 9**

After CI passes:

1. **Delete .submission/ folder**: `rm -rf .submission/`
2. **Stage deletion**: `git add .submission/`
3. **Commit cleanup**: `git commit -m "Clean up submission artifacts after implementation"`
4. **Push changes**: `git push`
5. **Create or update PR** using gh CLI:

   ```bash
   gh pr create --fill --label "ai-generated" || gh pr edit --add-label "ai-generated"
   ```

**Success indicators:**

- `.submission/` folder no longer exists
- Changes committed and pushed
- PR created or updated with "ai-generated" label

### Step 11: Output Format

Structure your output clearly:

- **Start**: "Executing implementation plan from .submission/plan.md (remote submission workflow)"
- **Each phase**: "Phase X: [brief description]" with code changes
- **CI section**: "Running iterative CI validation (attempt N of 5)"
- **Progress updates**: Regular status reports
- **End**: "Plan execution complete. Submission workflow finished. [Summary of what was implemented and PR details]"

## Requesting Clarification

If clarification is needed during execution:

1. Explain what has been completed so far
2. Clearly state what needs clarification
3. Suggest what information would help proceed
4. Wait for user response before continuing

## Important Notes

- **No time estimates**: Never provide time-based estimates or completion predictions
- **Standards first**: Project coding standards (if defined) override plan instructions
- **Sequential execution**: Complete phases in order unless plan specifies otherwise
- **Progress tracking**: Keep todo list updated throughout
- **User communication**: Provide clear, concise progress updates
- **Remote-specific**: This command is optimized for GitHub Actions CI - do not run locally
