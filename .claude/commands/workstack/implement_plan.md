---
description: Execute the implementation plan from .PLAN.md in current directory
---

# /workstack:implement_plan

This command reads and executes the `.PLAN.md` file from the current directory. It is designed to be run after switching to a worktree created by `/workstack:create_from_plan`.

## Usage

```bash
/workstack:implement_plan
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
- Code changes made following CLAUDE.md standards
- Clear progress tracking and completion summary

---

## Agent Instructions

You are executing the `/workstack:implement_plan` command. Follow these steps carefully:

### Step 1: Verify .PLAN.md Exists

Check that `.PLAN.md` exists in the current directory.

If not found:

```
❌ Error: No .PLAN.md file found in current directory

This command must be run from a worktree directory that contains a .PLAN.md file.

To create a worktree with a plan:
1. Run /workstack:create_from_plan to save your plan and create a worktree
2. Run: workstack switch <worktree-name>
3. Then run: claude --permission-mode acceptEdits "/workstack:implement_plan"
```

### Step 2: Read the Plan File

Read `.PLAN.md` from the current directory to get the full implementation plan.

Parse the plan to understand:

- Overall goal and context
- Individual phases or tasks
- Dependencies between tasks
- Success criteria
- Any special requirements or constraints

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
3. **Check relevant coding standards** from CLAUDE.md
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
   - If plan mentions tests, follow patterns in tests/CLAUDE.md
5. **Verify implementation** against standards
6. **Mark phase as completed** when done
7. **Report progress**: what was done and what's next
8. **Move to next phase**

### Step 5: Follow Workstack Coding Standards

The standards in CLAUDE.md OVERRIDE any conflicting guidance in the plan.

Key standards:

- Exception handling: LBYL, not EAFP
- Type annotations: Modern Python 3.13+ syntax
- Path operations: Check .exists() first
- Dependency injection: ABC, not Protocol
- Imports: Absolute only
- CLI: Use click.echo()
- Code style: Max 4 indentation levels

See [CLAUDE.md](../../../CLAUDE.md) for complete standards.

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

### Step 8: Run CI Checks

After implementing the plan, verify all code quality checks pass:

1. Run the `/ensure-ci` slash command to execute all CI checks
2. The command will iteratively fix any issues until all checks pass
3. This ensures the implementation meets code quality standards

If CI checks reveal issues with the implementation:

- Fix them as part of the implementation process
- Update todo list to track CI-related fixes
- Only proceed once all checks pass

**Note**: This step creates a hard dependency on the `/ensure-ci` command, which is specific to the current repository. When this command is packaged as a proper kit for distribution, this approach will need to be reassessed to work with arbitrary projects that may have different CI tooling.

### Step 9: Output Format

Structure your output clearly:

- **Start**: "Executing implementation plan from .PLAN.md"
- **Each phase**: "Phase X: [brief description]" with code changes
- **Progress updates**: Regular status reports
- **CI verification**: "Running CI checks to verify implementation"
- **End**: "Plan execution complete. All CI checks passed. [Summary of what was implemented]"

## Requesting Clarification

If clarification is needed during execution:

1. Explain what has been completed so far
2. Clearly state what needs clarification
3. Suggest what information would help proceed
4. Wait for user response before continuing

## Important Notes

- **No time estimates**: Never provide time-based estimates or completion predictions
- **Standards first**: CLAUDE.md standards override plan instructions
- **Sequential execution**: Complete phases in order unless plan specifies otherwise
- **Progress tracking**: Keep todo list updated throughout
- **User communication**: Provide clear, concise progress updates
