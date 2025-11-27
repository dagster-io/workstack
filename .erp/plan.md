# Minimal-Change Fix for /gt:pr-submit Workflow Issues

## Problem Summary

**Issue 1: Workflow doesn't fail when PR submission fails**
- Agent successfully committed/squashed but gt submit failed (missing Graphite auth)
- Workflow reported as informational instead of critical failure
- Job should have failed (non-zero exit) but didn't

**Issue 2: No pre-flight Graphite authentication check**
- gt submit fails when user isn't authenticated to Graphite
- No check before expensive operations (commit, squash, diff analysis)
- User only discovers auth issue after workflow has made changes

## Current Architecture

```
/gt:pr-submit (slash command)
  → gt-branch-submitter (agent via Task tool)
    → Step 1: dot-agent run gt submit-pr pre-analysis (Python kit command)
    → Step 2: Diff analysis (agent)
    → Step 3: dot-agent run gt submit-pr post-analysis (Python kit command)
      → execute_post_analysis() → ops.graphite().submit()
        → RealGraphiteGtKit.submit() → subprocess.run(['gt', 'submit', ...])
```

## Root Cause Analysis

### Issue 1: Error Propagation Gap
The agent prompt has error handling instructions (lines 282-329 in gt-branch-submitter.md) but:
- Instructions tell agent to "stop and display" errors
- No enforcement mechanism - agent can ignore and continue
- Python commands return JSON with success=false, but agent doesn't necessarily fail
- Task tool may not propagate agent's "stop" as a failure to parent

### Issue 2: Missing Pre-flight Check
- gt submit requires authentication to Graphite (via `gt auth --token`)
- No check exists before running expensive operations
- Existing pattern: Ensure.gh_installed() checks GitHub CLI availability
- Need similar check for Graphite authentication

## Minimal Change Solution

### Change 1: Add Graphite Auth Check (Python)

**File**: `/Users/schrockn/code/erk/src/erk/cli/ensure.py`

**Add new method after `gh_installed()` (around line 362)**:

```python
@staticmethod
def gt_authenticated() -> None:
    """Ensure Graphite CLI (gt) is authenticated.
    
    Uses gt user tips to check auth status, which is the LBYL
    approach to validating Graphite authentication before use.
    
    Raises:
        SystemExit: If gt is not authenticated
    
    Example:
        >>> Ensure.gt_authenticated()
        >>> # Now safe to call gt submit commands
    """
    # First check if gt is installed
    if shutil.which("gt") is None:
        user_output(
            click.style("Error: ", fg="red")
            + "Graphite CLI (gt) is not installed\n\n"
            + "Install it from: https://graphite.dev/docs/install\n"
        )
        raise SystemExit(1)
    
    # Check authentication by running a command that requires auth
    # gt user tips is lightweight and requires authentication
    result = subprocess.run(
        ["gt", "user", "tips"],
        capture_output=True,
        text=True,
        check=False,
    )
    
    if result.returncode != 0:
        # Authentication required
        user_output(
            click.style("Error: ", fg="red")
            + "Graphite CLI (gt) is not authenticated\n\n"
            + "Authenticate with: gt auth --token YOUR_TOKEN\n"
            + "Get your token from: https://app.graphite.dev/activate"
        )
        raise SystemExit(1)
```

**Why this location**: Right after `gh_installed()` - follows existing pattern for external tool validation.

**Why this approach**: 
- Reuses existing Ensure pattern
- LBYL (Look Before You Leap) - checks before expensive operations
- Uses gt user tips as a lightweight auth check command
- Provides helpful error message with next steps

### Change 2: Call Auth Check in Pre-Analysis

**File**: `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/submit_branch.py`

**Add import at top (after line 66)**:

```python
from erk.cli.ensure import Ensure
```

**Add check at start of `execute_pre_analysis()` (after line 213)**:

```python
def execute_pre_analysis(ops: GtKit | None = None) -> PreAnalysisResult | PreAnalysisError:
    """Execute the pre-analysis phase. Returns success or error result."""
    if ops is None:
        ops = RealGtKit()
    
    # CRITICAL: Check Graphite authentication BEFORE any operations
    # This prevents wasting work if user isn't authenticated
    Ensure.gt_authenticated()
    
    # Step 0: Check for and commit uncommitted changes
    ...
```

**Why this location**: Before any git operations - fails fast if auth missing.

**Why this approach**:
- Minimal change - single function call
- Reuses existing error handling (Ensure raises SystemExit(1))
- Python command already exits with code 1 on failure
- No changes to agent prompt needed

### Change 3: Strengthen Agent Error Handling

**File**: `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/agents/gt/gt-branch-submitter.md`

**Modify Step 1 instructions (around line 24-55)**:

Current:
```markdown
**Error handling:**
If the command fails (exit code 1), parse the error JSON and report to user. Do not continue.
```

Strengthened:
```markdown
**Error handling:**
If the command fails (exit code 1):
1. Parse the error JSON to understand what failed
2. Display the error message and details to the user
3. **CRITICAL**: Use Bash to exit with non-zero code to propagate failure:
   ```bash
   exit 1
   ```
4. DO NOT continue to next steps

This ensures the workflow fails properly when pre-analysis fails.
```

**Repeat similar change for Step 3 (post-analysis) around line 206-214**:

```markdown
**Error handling:**

If the command fails (exit code 1):
1. Parse the error JSON to understand what failed
2. Examine the error type and command output (stdout/stderr in details)
3. Provide clear, helpful guidance based on the specific situation
4. **CRITICAL**: Use Bash to exit with non-zero code to propagate failure:
   ```bash
   exit 1
   ```
5. DO NOT retry automatically - let the user decide how to proceed
```

**Why this change**: 
- Makes error propagation explicit in agent instructions
- Agent must actively call `exit 1` to fail the workflow
- Minimal change to existing error handling pattern
- Doesn't require architectural changes

### Change 4: Update Agent Self-Verification Checklist

**File**: Same file, at end (around line 524-542)

**Add checklist item**:

```markdown
## Self-Verification

Before completing, verify:

- [ ] Uncommitted changes were checked and committed if needed
- [ ] Pre-analysis completed successfully OR workflow exited with code 1
- [ ] Diff analysis is concise and strategic (3-5 key changes max)
- [ ] Commit message has no Claude footer
- [ ] File paths are relative to repository root
- [ ] Post-analysis completed successfully OR workflow exited with code 1
- [ ] PR link posted to issue (if issue reference exists)
- [ ] Graphite URL retrieved from JSON output
- [ ] Results displayed with "What Was Done" section listing actions
- [ ] Graphite URL placed at end under "View PR" section
- [ ] Any errors handled with helpful guidance AND exit 1 called
```

## Implementation Sequence

1. **Add Ensure.gt_authenticated()** in ensure.py
   - Test manually: `python -c "from erk.cli.ensure import Ensure; Ensure.gt_authenticated()"`
   - Should pass if authenticated, fail with helpful message if not

2. **Add auth check to pre-analysis** in submit_branch.py
   - Test with unit test that mocks Ensure.gt_authenticated() to raise SystemExit
   - Verify command exits with code 1 when auth check fails

3. **Update agent prompt** in gt-branch-submitter.md
   - Add explicit exit 1 instructions to error handling sections
   - Add verification checklist item

4. **Integration test**:
   - Test with unauthenticated Graphite (remove token temporarily)
   - Verify workflow fails fast with helpful error message
   - Verify exit code is 1

5. **Test normal workflow**:
   - Ensure changes don't break authenticated workflow
   - Verify all steps still work as expected

## Testing Strategy

**Unit Tests** (submit_branch.py):
```python
def test_pre_analysis_fails_when_gt_not_authenticated():
    """Verify pre-analysis fails fast when Graphite is not authenticated."""
    with patch('erk.cli.ensure.Ensure.gt_authenticated', side_effect=SystemExit(1)):
        with pytest.raises(SystemExit):
            execute_pre_analysis()
```

**Manual Testing**:
1. Remove Graphite auth token: `gt auth --token ""`
2. Run `/gt:pr-submit "test"`
3. Verify:
   - Workflow fails immediately (before committing/squashing)
   - Error message shows authentication requirement
   - Exit code is 1
   - Agent stops execution (doesn't continue to post-analysis)

**Integration Testing**:
1. Re-authenticate: `gt auth --token YOUR_TOKEN`
2. Run `/gt:pr-submit "test"` on real branch
3. Verify:
   - Pre-flight check passes
   - Workflow completes successfully
   - PR is created

## Why This Is Minimal

1. **Reuses existing patterns**: Ensure class, SystemExit(1), JSON error responses
2. **No architectural changes**: Same agent → Python command → subprocess flow
3. **No new dependencies**: Uses existing subprocess, shutil, click imports
4. **No new error types**: Reuses existing error handling infrastructure
5. **Single new method**: Ensure.gt_authenticated() - 20 lines
6. **Single function call**: One line added to execute_pre_analysis()
7. **Documentation updates**: Clarifies existing error handling instructions

## Trade-offs Accepted

1. **Agent must remember to call exit 1**: Not enforced by code, relies on prompt
   - Alternative would require Task tool changes (out of scope)
   - Mitigated by: explicit instructions, checklist item

2. **Auth check happens in Python, not agent**: Could add to agent prompt
   - But Python is better place for LBYL check
   - Reuses existing Ensure pattern
   - More reliable than agent following instructions

3. **Uses gt user tips for auth check**: Not a dedicated auth status command
   - But it's lightweight and requires auth
   - Alternative: parse config files (more fragile)
   - Trade-off: works, simple, minimal

## Files Changed

1. `/Users/schrockn/code/erk/src/erk/cli/ensure.py` - Add gt_authenticated()
2. `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/submit_branch.py` - Add auth check call
3. `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/agents/gt/gt-branch-submitter.md` - Strengthen error handling instructions

Total: 3 files, ~30 lines added/modified

## Success Criteria

- [ ] Workflow fails fast (exit 1) when Graphite not authenticated
- [ ] Error message is helpful (tells user how to authenticate)
- [ ] Workflow fails fast (exit 1) when post-analysis fails
- [ ] No changes made (commit/squash) before auth check runs
- [ ] Normal authenticated workflow still works
- [ ] Agent properly propagates failures with exit 1