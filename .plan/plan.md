## Implementation Plan: Fix Shell Integration Handler Bug

### Objective

Fix the bug where the shell integration handler crashes after `workstack consolidate --down` completes successfully, by adding proper validation before Path operations and making the consolidate command's "no script" case more explicit.

### Context & Understanding

#### API/Tool Quirks

- `CliRunner` from Click captures both stdout and stderr in `result.output`
- When commands only output to stderr (via `user_output()`), `result.output` may contain stderr text
- Path operations in Python raise `OSError: [Errno 63] File name too long` when given multi-line text as path
- Commands that use `machine_output()` write to stdout for shell integration
- Commands that use `user_output()` write to stderr for human consumption
- Shell integration expects stdout to contain either a script path or be empty

#### Architectural Insights

- Shell integration handler at line 92 assumes `result.output` is either a valid path or empty
- The handler was designed expecting commands to output script paths to stdout when in `--script` mode
- Commands like `jump`, `switch`, `up`, `down` always generate scripts when switching worktrees
- `consolidate` is unique: it may not switch worktrees (when consolidating into current)
- The separation of `user_output()` (stderr) and `machine_output()` (stdout) is intentional for shell integration

#### Domain Logic & Business Rules

- When `consolidate` runs with `--down` flag only (no `--name`), it consolidates branches into the current worktree
- No worktree switch means no activation script is needed
- Commands should output nothing to stdout when no script is generated
- User-facing messages should always go to stderr to avoid confusing shell integration

#### Complex Reasoning

- **Rejected**: Using try/except to catch Path errors
  - Reason: Violates codebase LBYL (Look Before You Leap) principle
  - Also: Hides root cause and could mask other Path-related bugs
- **Chosen**: Validate output looks like a path before Path operations
  - Follows LBYL pattern by checking conditions first
  - Makes invalid output handling explicit and debuggable

#### Known Pitfalls

- DO NOT assume `result.output.strip()` contains a valid path - it might contain multi-line user messages
- DO NOT use try/except for Path operations - violates LBYL principle
- DO NOT forget that empty string is a valid "no script" indicator - only non-empty invalid paths are problematic
- DO NOT modify how commands output to stdout/stderr without considering shell integration impact

#### Raw Discoveries Log

- Discovered: Bug occurs at handler.py line 96 when calling `Path(script_path).exists()`
- Confirmed: `consolidate --down` outputs nothing to stdout (correct behavior)
- Learned: Handler receives empty string in `result.output` when stdout is empty
- Checked: Other commands (jump.py, switch.py) always output script paths when in script mode
- Found: Handler already has logic for empty output at lines 100-101 but crashes before reaching it
- Verified: The crash message shows entire consolidate output as the "filename"
- Noted: consolidate.py lines 340-357 control when script paths are output
- Observed: Only outputs to stdout when `name is not None and script and not dry_run`
- Clarified: Current working directory is preserved across worktree operations
- Discovered: Path length limit on most systems is 4096 characters
- Found: Handler forwards stderr via `user_output(err.output)` at lines 88-89
- Verified: Exit code 0 with empty stdout is valid and expected for some commands

#### Planning Artifacts

**Code Examined:**
- Looked at handler.py lines 86-103 for crash location and logic
- Reviewed consolidate.py lines 340-357 for output behavior
- Checked jump.py lines 78-94 for comparison pattern
- Examined switch.py lines 57, 110 for output patterns

**Error Message:**
- `OSError: [Errno 63] File name too long:` followed by entire consolidate output

#### Implementation Risks

**Technical Debt:**
- Handler makes assumptions about output format without validation
- No explicit documentation about stdout/stderr conventions for commands

**Uncertainty Areas:**
- Other commands might have similar edge cases not yet discovered
- Test coverage for shell integration may be limited

### Implementation Steps

1. **Fix handler validation**: Update path validation in `src/workstack/cli/shell_integration/handler.py`
   [CRITICAL: Must follow LBYL pattern - check conditions before Path operations]
   - Success: Handler doesn't crash on multi-line output
   - On failure: Check if validation logic has syntax errors

   Related Context:
   - Comprehensive validation approach chosen per user preference
   - Check newlines, length limit, and path characteristics (see Known Pitfalls)
   - Must preserve existing behavior for valid paths

2. **Make consolidate explicit**: Add early return in `src/workstack/cli/commands/consolidate.py`
   - Success: Clear code path when no script needed
   - On failure: Verify logic conditions are correct

   Related Context:
   - Makes "no script" case explicit for future maintenance
   - Prevents confusion about when stdout should be empty
   - User chose to include this improvement

3. **Add handler test coverage**: Create tests in `tests/commands/shell/test_shell_integration.py`
   - Success: Tests pass for empty stdout and multi-line stderr cases
   - On failure: Check test fixtures and assertions

   Related Context:
   - Full integration testing chosen per user preference
   - Must test handler robustness against various output formats

4. **Add consolidate command tests**: Verify consolidate behavior with/without --name flag
   - Success: Tests confirm correct stdout/stderr output
   - On failure: Review consolidate command logic

   Related Context:
   - Ensures consolidate command behavior is properly documented via tests
   - Validates fix doesn't break existing functionality

5. **Verify other commands**: Test jump, switch, up, down commands still work
   - Success: All commands function correctly with shell integration
   - On failure: Check if validation is too restrictive

   Related Context:
   - Full integration approach ensures no regression
   - These commands should always output valid script paths

### Testing

- Run existing shell integration tests
- Run new tests for handler edge cases
- Test consolidate command manually with various flag combinations
- Final validation: Run project CI/validation checks

---

## Progress Tracking

**Current Status:** Plan created, ready for implementation

**Last Updated:** 2025-11-14

### Implementation Progress

- [ ] Step 1: Fix handler validation in handler.py
- [ ] Step 2: Make consolidate explicit with early return
- [ ] Step 3: Add handler test coverage
- [ ] Step 4: Add consolidate command tests
- [ ] Step 5: Verify other commands still work

### Overall Progress

**Steps Completed:** 0 / 5