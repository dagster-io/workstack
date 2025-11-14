## Implementation Plan: Fix Deleted CWD Error

### Objective

Fix the FileNotFoundError that occurs when running workstack commands from a directory that has been deleted, implementing graceful fallback to repository root or home directory with proper user notification.

### Context & Understanding

#### API/Tool Quirks

- `Path.cwd()` internally calls `os.getcwd()` which raises `FileNotFoundError` when the current directory no longer exists on the filesystem
- This commonly occurs after `workstack remove` deletes a worktree while the user's shell is still in that directory
- Shell prompts cache the directory path and don't automatically detect when it's been deleted
- `Path.resolve()` and `Path.is_relative_to()` can also fail on missing paths and need defensive handling
- The error happens at CLI initialization before any command logic runs

#### Architectural Insights

- `create_context()` is the single entry point for context creation, called by all CLI commands at line 36 of `src/workstack/cli/cli.py`
- The codebase already has `regenerate_context()` for refreshing context after `os.chdir()` calls, but it also calls `create_context()` so fixing the latter fixes both
- `prepare_cwd_recovery_cmd` already handles missing cwd gracefully by checking `ctx.cwd.exists()` before operations
- `discover_repo_or_sentinel()` is already defensive - checks if cwd exists at lines 55-56 and returns `NoRepoSentinel` for missing paths
- Clean separation of concerns dictates warnings should be emitted at CLI layer, not in core context creation

#### Domain Logic & Business Rules

- Fallback behavior priority: (1) Try to find repository root from parent directories, (2) Fall back to home directory if no repo found
- User must be notified when fallback occurs to avoid confusion about working directory
- Commands should continue to work with fallback directory rather than failing entirely
- Shell integration scripts rely on exit codes and stdout/stderr separation - warnings must go to stderr

#### Complex Reasoning

- **Rejected**: Failing with better error message only
  - Reason: User can't easily recover - they're stuck in deleted directory
  - Also: Would break workflows and automation
- **Rejected**: Requiring shell integration to handle this
  - Reason: Not all users have shell integration installed
  - Also: Too brittle, varies by shell
- **Chosen**: Automatic fallback with warning
  - Graceful degradation maintains functionality
  - Clear notification prevents confusion
  - Works universally without special setup

#### Known Pitfalls

- DO NOT emit warnings directly in `create_context()` - violates separation of concerns between core logic and CLI presentation
- DO NOT use `Path.resolve()` without checking `.exists()` first - will fail with `FileNotFoundError` on missing paths
- DO NOT assume parent directory exists when falling back - chain fallbacks (repo root → home)
- DO NOT send warnings to stdout - breaks shell integration scripts that parse command output
- DO NOT modify frozen dataclasses without careful consideration - WorkstackContext is frozen for immutability

#### Raw Discoveries Log

- Discovered: Error occurs at line 316 in `src/workstack/core/context.py`
- Confirmed: `regenerate_context()` just calls `create_context()` so fixing one fixes both
- Learned: `prepare_cwd_recovery_cmd` already has defensive code for missing cwd
- Checked: Multiple CLI commands would benefit from this fix
- Found: Tests use `simulated_workstack_env` which handles cwd properly
- Verified: `discover_repo_or_sentinel()` already defensive at lines 55-56
- Noted: WorkstackContext is a frozen dataclass - adding fields requires care
- Observed: CLI uses Click framework with `click.echo(err=True)` for stderr
- Discovered: Path operations that can fail include `.cwd()`, `.resolve()`, `.is_relative_to()`
- Found: Repository discovery can walk up parent directories to find `.git`
- Confirmed: Home directory via `Path.home()` is universal fallback

#### Planning Artifacts

**Stack trace analyzed:**

```
File "/Users/schrockn/code/workstack/src/workstack/core/context.py", line 316, in create_context
    cwd = Path.cwd()
FileNotFoundError: [Errno 2] No such file or directory
```

**Commands that helped debug:**

- `pwd` → Returns successfully even when cwd deleted
- `echo $PWD` → Shows cached path that no longer exists
- `git worktree list` → Shows all worktrees to find which was deleted

**Code patterns examined:**

- `prepare_cwd_recovery_cmd` - Has proper defensive checking
- `discover_repo_or_sentinel` - Already checks path.exists()
- Test fixtures using `simulated_workstack_env` - Proper isolation

#### Implementation Risks

**Technical Debt:**

- Multiple path operations scattered throughout codebase may have similar issues
- No consistent pattern for defensive path handling

**Uncertainty Areas:**

- How many other path operations might fail on deleted directories
- Whether some commands specifically require real cwd (vs fallback)

**Performance Concerns:**

- Walking up directory tree to find repo root could be slow on deep paths
- None significant - this is error recovery path only

**Security Considerations:**

- Falling back to home directory is safe - no privilege escalation
- Repository root discovery uses existing secure logic

### Implementation Steps

1. **Create safe CWD detection function**: Add `get_safe_cwd()` in `src/workstack/core/context.py`
   [CRITICAL: Must handle both FileNotFoundError and OSError for robustness]
   - Success: Function returns tuple of (Path, RecoveryInfo | None)
   - On failure: Function never raises, always returns valid path

   Related Context:
   - Returns RecoveryInfo when fallback used to pass warning info to CLI layer
   - Tries repository root first (better context), then home directory (universal)
   - See API/Tool Quirks for why both FileNotFoundError and OSError needed

2. **Create RecoveryInfo dataclass**: Add dataclass in `src/workstack/core/context.py`
   - Success: Frozen dataclass with deleted_path and fallback_path fields
   - On failure: Check dataclass syntax and imports

   Related Context:
   - Needs to carry both original (deleted) path and chosen fallback for clear warning
   - Must be frozen for immutability consistency with codebase patterns

3. **Update create_context() to use safe CWD**: Modify line 316 in `src/workstack/core/context.py`
   - Success: Uses get_safe_cwd() and stores recovery_info if present
   - On failure: Check tuple unpacking syntax

   Related Context:
   - Clean separation - no warning emission here, just capture recovery info
   - See Architectural Insights for why this is the single fix point

4. **Add recovery_info to WorkstackContext**: Modify WorkstackContext dataclass in `src/workstack/core/context.py`
   - Success: Optional field added with default None
   - On failure: Ensure frozen=True preserved, check field syntax

   Related Context:
   - Optional field maintains backward compatibility
   - See Known Pitfalls about modifying frozen dataclasses

5. **Emit warning in CLI entry point**: Update cli() in `src/workstack/cli/cli.py` after line 36
   - Success: Warning shown to stderr when recovery occurred
   - On failure: Check click.echo syntax and err=True parameter

   Related Context:
   - Warning at CLI layer maintains separation of concerns (see Architectural Insights)
   - Must use stderr to avoid breaking shell integrations (see Domain Logic)
   - Show both deleted path and fallback for clarity

6. **Audit and fix Path.resolve() usage**: Search for `.resolve()` calls without `.exists()` checks
   [CRITICAL: Each resolve() must be preceded by exists() check per LBYL principle]
   - Success: All unsafe resolve() calls protected
   - On failure: Review LBYL patterns in codebase

   Related Context:
   - Comprehensive audit requested to prevent similar issues
   - See Known Pitfalls about resolve() on missing paths
   - Follows codebase's LBYL principle (never try/except for control flow)

7. **Audit and fix Path.is_relative_to() usage**: Search for `.is_relative_to()` calls on potentially missing paths
   - Success: All unsafe is_relative_to() calls protected
   - On failure: Review path validation patterns

   Related Context:
   - Part of comprehensive path operation audit
   - Can fail similarly to resolve() on missing paths

8. **Add unit tests**: Create tests in `tests/unit/core/test_context.py`
   - Success: Tests pass, coverage for get_safe_cwd() with mocked scenarios
   - On failure: Check mock usage and test fixtures

   Related Context:
   - Mock Path.cwd() to raise FileNotFoundError
   - Test both repo root and home directory fallbacks
   - Verify RecoveryInfo properly populated

9. **Add integration test**: Create `tests/integration/test_deleted_cwd.py`
   - Success: Test simulates real deleted directory scenario
   - On failure: Check test isolation and cleanup

   Related Context:
   - Tests actual command execution with deleted cwd
   - Verifies warning message appears
   - Confirms commands still function with fallback

10. **Run validation**: Execute project CI checks with `make all-ci`
    - Success: All tests pass, pyright succeeds, ruff clean
    - On failure: Fix any issues found by CI

    Related Context:
    - Final validation ensures no regressions
    - Catches any typing or style issues

### Testing

- Unit tests for get_safe_cwd() with mocked failures
- Integration test with actual deleted directory
- Test both fallback scenarios (repo root and home)
- Verify warning message format and stderr routing
- Run full CI validation suite

---

## Progress Tracking

**Current Status:** Plan created, ready for implementation

**Last Updated:** 2024-11-14

### Implementation Progress

- [ ] Step 1: Create safe CWD detection function
- [ ] Step 2: Create RecoveryInfo dataclass
- [ ] Step 3: Update create_context() to use safe CWD
- [ ] Step 4: Add recovery_info to WorkstackContext
- [ ] Step 5: Emit warning in CLI entry point
- [ ] Step 6: Audit and fix Path.resolve() usage
- [ ] Step 7: Audit and fix Path.is_relative_to() usage
- [ ] Step 8: Add unit tests
- [ ] Step 9: Add integration test
- [ ] Step 10: Run validation

### Overall Progress

**Steps Completed:** 0 / 10
