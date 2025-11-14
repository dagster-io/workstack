## Implementation Plan: Fix land-stack --down Flag Suggestions

### Objective

Fix the `workstack land-stack --down` error message to properly suggest `--down` flag in both the consolidate and retry commands when the original command used `--down`.

### Context & Understanding

#### API/Tool Quirks

- The `consolidate` command supports the same `--down` flag as `land-stack` with identical semantics
- Both commands use the same flag to limit operations to downstack branches only
- The error occurs when branches are checked out in multiple worktrees

#### Architectural Insights

- The validation logic is separated from the command entry point for modularity
- The `_validate_landing_preconditions()` function doesn't currently receive the `down` flag, which prevents it from customizing error messages
- Error messages are generated in the validation layer, not at the command level

#### Domain Logic & Business Rules

- When `--down` is specified, only downstack branches are processed
- The consolidate suggestion must match the scope of the original operation
- User confusion is reduced when suggested commands maintain the same scope

#### Complex Reasoning

- **Rejected**: Duplicating validation logic in command.py
  - Reason: Would violate separation of concerns
  - Also: Creates maintenance burden with duplicated code
- **Chosen**: Thread the `down` flag through to validation function
  - Maintains clean architecture while enabling contextual error messages

#### Known Pitfalls

- DO NOT forget to update both command suggestions (consolidate AND retry)
- DO NOT modify the validation logic itself, only the error message generation

#### Raw Discoveries Log

- Found validation function at line 116-138 in validation.py
- Discovered function signature lacks `down` parameter
- Confirmed consolidate command supports --down flag at line 33-35
- Located call site at line 115-117 in command.py
- Found existing test at line 72-75 in test_worktree_handling.py
- Verified both commands share the same --down semantics

#### Planning Artifacts

**Code Examined:**

- Looked at validation.py lines 116-138 for error message generation
- Reviewed command.py line 54 for `down` flag availability
- Checked consolidate.py lines 33-35 for flag support

#### Implementation Risks

**Testing Coverage:**

- Existing test only checks for basic error message presence
- Need to add test case for --down variant

### Implementation Steps

1. **Update validation function signature**: Add `down` parameter to `_validate_landing_preconditions()` in `src/workstack/cli/commands/land_stack/validation.py`
   - Add `down: bool` parameter after `branches_to_land`
   - Success: Function signature includes the new parameter
   - On failure: Check for syntax errors in parameter list

   Related Context:
   - The `down` flag determines the scope of operations (see Domain Logic & Business Rules)
   - Function currently at lines 76-82 of validation.py

2. **Update function call site**: Pass `down` flag when calling validation in `src/workstack/cli/commands/land_stack/command.py`
   - Add `down=down` to the function call at line 115-117
   - Success: Call includes the down parameter
   - On failure: Verify `down` variable is in scope

   Related Context:
   - The `down` variable is available at line 54 of command.py
   - Must maintain parameter order matching the updated signature

3. **Fix consolidate suggestion**: Update error message to conditionally include `--down` in `src/workstack/cli/commands/land_stack/validation.py`
   - Modify line ~133 to use: `f"workstack consolidate{' --down' if down else ''}"`
   - Success: Message includes --down when appropriate
   - On failure: Check string formatting syntax

   Related Context:
   - Line currently shows "Run: workstack consolidate"
   - Must conditionally append --down based on flag value

4. **Fix retry suggestion**: Update retry command to include `--down` in `src/workstack/cli/commands/land_stack/validation.py`
   - Modify line ~135 to use: `f"workstack land-stack{' --down' if down else ''}"`
   - Success: Retry command includes --down when appropriate
   - On failure: Check string formatting syntax

   Related Context:
   - Line currently shows "Then retry: workstack land-stack"
   - Both suggestions must be consistent in flag usage

5. **Add test for --down error message**: Create test case in `tests/commands/graphite/land_stack/test_worktree_handling.py`
   [CRITICAL: Test both with and without --down flag to ensure no regression]
   - Add new test function for --down variant
   - Verify both command suggestions include --down
   - Success: Test passes and verifies correct suggestions
   - On failure: Check test assertions and setup

   Related Context:
   - Existing test at line 72-75 validates basic error message
   - New test should follow same pattern but with --down flag

6. **Run existing tests**: Execute test suite to ensure no regression
   - Run: `pytest tests/commands/graphite/land_stack/`
   - Success: All existing tests pass
   - On failure: Review changes for unintended side effects

   Related Context:
   - Must maintain backward compatibility for non-down case
   - Existing tests validate current behavior

### Testing

- Tests are integrated within implementation steps
- Final validation: Run `pytest tests/commands/graphite/land_stack/test_worktree_handling.py`

---

## Progress Tracking

**Current Status:** Plan created, ready for implementation

**Last Updated:** 2025-11-14

### Implementation Progress

- [ ] Step 1: Update validation function signature in validation.py
- [ ] Step 2: Update function call site in command.py
- [ ] Step 3: Fix consolidate suggestion in validation.py
- [ ] Step 4: Fix retry suggestion in validation.py
- [ ] Step 5: Add test for --down error message
- [ ] Step 6: Run existing tests to ensure no regression

### Overall Progress

**Steps Completed:** 0 / 6
