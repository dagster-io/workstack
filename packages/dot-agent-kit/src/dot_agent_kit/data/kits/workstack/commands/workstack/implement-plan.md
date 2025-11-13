---
description: Execute the implementation plan from .PLAN.md in current directory
---

# /workstack:implement-plan

This command reads and executes the `.PLAN.md` file from the current directory. It is designed to be run after switching to a worktree created by `/workstack:create-planned-stack`.

## Usage

```bash
/workstack:implement-plan
```

## Prerequisites

- Must be in a worktree directory that contains `.PLAN.md`
- Typically run after `workstack switch <worktree-name>`
- `.PLAN.md` should contain a valid implementation plan

## What Happens

When you run this command:

1. Verifies `.PLAN.md` exists in the current directory
2. Reads and parses the implementation plan
3. Creates todo list for tracking progress
4. Executes each phase of the plan sequentially
5. Provides progress updates and summary

## Expected Outcome

- Implementation plan executed according to specifications
- Code changes follow project coding standards (if defined)
- Clear progress tracking and completion summary

---

## Agent Instructions

You are executing the `/workstack:implement-plan` command. Follow these steps carefully:

### Step 1: Verify .PLAN.md Exists

Check that `.PLAN.md` exists in the current directory.

If not found:

```
❌ Error: No .PLAN.md file found in current directory

This command must be run from a worktree directory that contains a .PLAN.md file.

To create a worktree with a plan:
1. Run /workstack:create-planned-stack to save your plan and create a worktree
2. Run: workstack switch <worktree-name>
3. Then run: claude --permission-mode acceptEdits "/workstack:implement-plan"
```

### Step 2: Read the Plan File

Read `.PLAN.md` from the current directory to get the full implementation plan.

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
6. **Mark phase as completed** when done
7. **Report progress**: what was done and what's next
8. **Move to next phase**

**IMPORTANT - Progress Tracking:**

The `.PLAN.md` file has two distinct sections:

1. **Main body (static reference material)**: Contains Objective, Context & Understanding, Implementation Steps/Phases, Testing. This section should NEVER be edited during implementation.

2. **Progress Tracking section** (at the bottom): Contains Current Status, Last Updated, phase/step checkboxes, and overall progress metrics. This is the ONLY section that should be updated during implementation.

When updating progress:

- Only edit the "Progress Tracking" section at the bottom of `.PLAN.md`
- Update "Current Status" field with current phase/step
- Update "Last Updated" timestamp
- Mark checkboxes as completed: `- [x]` instead of `- [ ]`
- Update "Overall Progress" metrics
- NEVER modify the main plan body (Objective, Context, Implementation Steps, etc.)

### Step 5: Follow Workstack Coding Standards

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

### Step 9: Output Format

Structure your output clearly:

- **Start**: "Executing implementation plan from .PLAN.md"
- **Each phase**: "Phase X: [brief description]" with code changes
- **Progress updates**: Regular status reports
- **End**: "Plan execution complete. [Summary of what was implemented]"

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
