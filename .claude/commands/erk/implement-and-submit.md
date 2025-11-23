---
description: Implement plan from .impl/, run CI, and submit branch as PR
---

# /erk:implement-and-submit

This command combines the full implementation workflow with CI validation and automatic branch submission. It provides an explicit opt-in alternative to `/erk:implement-plan` for users who want their changes automatically committed and submitted as a PR after successful implementation and testing.

## Usage

```bash
# Navigate to worktree first
erk checkout my-feature-branch

# Run the complete workflow (implement → CI → submit)
claude --permission-mode acceptEdits "/erk:implement-and-submit"
```

## What This Command Does

Executes the complete local development workflow:

1. **Implementation (Steps 1-8):** Reads `.impl/plan.md`, executes phases sequentially, updates progress in `.impl/progress.md`
2. **CI Validation (Step 9):** Runs `/fast-ci` iteratively (max 5 attempts) to ensure all tests and type checks pass
3. **Branch Submission (Step 10):** Delegates to `gt-branch-submitter` agent to commit, squash, generate message, and create PR
4. **Status Report (Step 11):** Provides comprehensive summary with PR URL and next steps

**Key Differences from /erk:implement-plan:**

- Adds mandatory CI validation before submission
- Automatically submits branch as PR on success
- Only works in `.impl/` folders (local development)
- Fails entire command if CI or submission fails (no partial success)

## Prerequisites

- Must be in a worktree directory that contains `.impl/` folder
- Typically run after `erk checkout <branch>`
- `.impl/plan.md` should contain a valid implementation plan
- Working directory should have clean git state or staged changes ready to commit

## Expected Outcome

- Implementation executed according to plan
- All CI checks passing (tests, type checking)
- Branch submitted as PR with auto-generated commit message
- PR URL provided for review
- `.impl/` folder remains for reference

## Troubleshooting

### "No plan folder found in current directory"

**Cause:** Not in a worktree with `.impl/` folder
**Solution:**

1. Run /erk:save-context-enriched-plan to create plan
2. Run /erk:create-wt-from-plan-file to create worktree
3. Run: erk checkout <branch>
4. Then run: claude --permission-mode acceptEdits "/erk:implement-and-submit"

### "CI validation failed after 5 attempts"

**Cause:** Tests or type checks failing repeatedly
**Solution:**

1. Review CI error output carefully
2. Fix issues manually
3. Run /fast-ci to verify fixes
4. Once passing, run /gt:submit-squashed-branch to complete submission

### "Branch submission failed"

**Cause:** Git/Graphite error during PR creation
**Solution:**

1. Implementation and CI passed, so code is ready
2. Check git status: git status
3. Check Graphite stack: gt log short
4. Try manual submission: gt branch submit
5. If issues persist, check Graphite documentation

### "This command only works in .impl/ folders"

**Cause:** Attempted to run in `.worker-impl/` or other directory
**Solution:**

- This command is for local development only
- .worker-impl/ folders auto-submit via /erk:implement-plan
- Ensure you're in a worktree with .impl/ folder

---

## Agent Instructions

You are executing the `/erk:implement-and-submit` command. Follow these steps carefully:

### Step 1: Verify .impl/plan.md Exists

Check that `.impl/plan.md` exists in the current directory.

If not found:

```
❌ Error: No plan folder found in current directory

This command must be run from a worktree directory that contains a .impl/ folder with plan.md.

To create a worktree with a plan:
1. Run /erk:save-context-enriched-plan to save your enhanced plan to disk
2. Run /erk:create-wt-from-plan-file to create a worktree from the plan
3. Run: erk checkout <branch>
4. Then run: claude --permission-mode acceptEdits "/erk:implement-and-submit"
```

### Step 2: Read the Plan File

Read `.impl/plan.md` from the current directory to get the full implementation plan.

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

The `.impl/progress.md` file tracks implementation progress using checkboxes AND YAML front matter (for files created after 2025-01-17).

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

### Step 2.6: Check for GitHub Issue Reference

Progress tracking via GitHub comments is available if `.impl/issue.json` exists.
The kit CLI commands handle all logic automatically - no manual setup required.

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
   - Edit `.impl/progress.md` to change checkbox from `- [ ]` to `- [x]`
   - If front matter exists (file starts with `---`):
     - Count total checked boxes in the entire file
     - Edit the `completed_steps:` line in front matter with new count
     - Do NOT change the `total_steps:` line
   - If no front matter exists, skip the front matter update
7. **Post progress comment to GitHub issue** (if enabled):

   ```bash
   dot-agent run erk post-progress-comment --step-description "Phase 1: Create abstraction" 2>/dev/null || true
   ```

   Note: Command fails silently if issue tracking not enabled. This is intentional.

8. **Report progress**: what was done and what's next
9. **Move to next phase**

**IMPORTANT - Progress Tracking:**

The new `.impl/` folder structure separates concerns:

1. **`.impl/plan.md` (immutable reference)**: Contains Objective, Context & Understanding, Implementation Steps/Phases, Testing. This file should NEVER be edited during implementation.

2. **`.impl/progress.md` (mutable tracking)**: Contains checkboxes for all steps extracted from plan.md. This is the ONLY file that should be updated during implementation.

When updating progress:

- Only edit `.impl/progress.md` - never touch `.impl/plan.md`
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
5. **Post final completion comment to GitHub issue** (if enabled):

   ```bash
   dot-agent run erk post-completion-comment --summary "Brief implementation summary" 2>/dev/null || true
   ```

   Note: Command fails silently if issue tracking not enabled. This is intentional.

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

### Step 9: Run CI Iteratively Until Pass

**Check folder type first:**

- If current directory contains `.worker-impl/` → Skip this step (worker flows handle their own CI)
- If current directory contains `.impl/` → Proceed with CI validation

**Iterative CI Process (max 5 attempts):**

For attempt in 1..5:

1. Run `/fast-ci` command (unit tests + pyright)
2. If all checks pass → Break out of loop, proceed to Step 10
3. If checks fail:
   - Read error output carefully
   - Analyze failures
   - Fix the issues
   - Increment attempt counter
4. If attempt == 5 and checks still failing:
   - Exit with error message
   - DO NOT proceed to submission

**Error Output (if max attempts reached):**

```
❌ Error: CI validation failed after 5 attempts

Details: Implementation is complete but tests/type checks are failing

Suggested action:
  1. Review CI failures above
  2. Fix issues manually
  3. Run /fast-ci again to verify fixes
  4. Once passing, run /gt:submit-squashed-branch to submit
```

**Success Output (CI passed):**

```
✅ CI validation passed

Implementation complete and verified. Proceeding to branch submission...
```

### Step 10: Submit Branch as PR

**Prerequisites:**

- Steps 1-8 completed (implementation done)
- Step 9 completed (CI passed)
- Only executing if in `.impl/` folder (not `.worker-impl/`)

**Delegate to gt-branch-submitter:**

Use the Task tool to delegate the complete submission workflow:

```
Task(
    subagent_type="gt-branch-submitter",
    description="Submit branch workflow",
    prompt="Execute the complete submit-branch workflow for the current branch"
)
```

The agent will:

1. Check for uncommitted changes and commit if needed
2. Squash commits on current branch
3. Analyze all changes and generate commit message
4. Amend commit with generated message
5. Submit branch and create/update PR
6. Report PR URL and results

**Error Handling:**

If submission fails, the gt-branch-submitter agent will report errors. DO NOT proceed to Step 11. Exit immediately with the agent's error message.

**Success Output:**

```
✅ Branch submitted successfully

PR: [URL from agent]
```

### Step 11: Final Status Report

Provide comprehensive summary covering all workflow phases:

```
✅ Implementation and submission complete

Summary:
- Implementation: [N] phases completed
- Progress tracking: Updated in .impl/progress.md
- CI validation: All checks passed
- Branch submission: PR created successfully

PR URL: [URL from gt-branch-submitter]

Next steps:
- Review PR on GitHub
- Address any review comments
- Merge when ready

Note: .impl/ folder remains in worktree for your reference.
You can delete it manually if desired: rm -rf .impl/
```

**If any phase failed, report partial status:**

```
❌ Workflow incomplete

Completed:
- [✓/✗] Implementation
- [✓/✗] CI validation
- [✓/✗] Branch submission

Error: [specific error from failed phase]

Suggested action: [phase-specific guidance]
```

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
- **CI is mandatory**: Unlike /erk:implement-plan, CI must pass before submission
- **All-or-nothing**: If any phase fails, command fails (no partial success)
