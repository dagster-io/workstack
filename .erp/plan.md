# Refactor Manual Error Checking to Use Ensure Abstraction

## Example: GitHub Authentication Check in submit.py

### Current Code (Lines 100-114)

**File:** `src/erk/cli/commands/submit.py`

```python
# Get GitHub username from gh CLI (requires authentication)
try:
    result = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True,
        text=True,
        check=True,
    )
    submitted_by = result.stdout.strip()
except subprocess.CalledProcessError:
    # Fall back to "unknown" if gh API fails
    submitted_by = "unknown"

if not submitted_by:
    submitted_by = "unknown"
```

### Problem

1. **Not LBYL compliant** - Uses try/catch instead of checking authentication upfront
2. **Silent failure** - Falls back to "unknown" instead of informing user of auth issue
3. **Deferred failure** - Later call to `ctx.github.trigger_workflow()` (line 118) will fail with unclear error if gh is not authenticated
4. **Inconsistent with codebase patterns** - Other commands use `Ensure.gh_authenticated(ctx)` (e.g., `pr/checkout_cmd.py:41`)

### Refactoring Plan

#### Step 1: Add Ensure import

Add to imports section (line 11):

```python
from erk.cli.ensure import Ensure
```

#### Step 2: Add authentication check at function start

Add after line 63 (after `discover_repo_context`):

```python
# Validate GitHub CLI authentication upfront (LBYL)
Ensure.gh_authenticated(ctx)
```

#### Step 3: Simplify username fetching

Replace lines 100-114 with:

```python
# Get GitHub username from gh CLI (authentication already validated)
is_authenticated, username, _ = ctx.github.check_auth_status()
submitted_by = username or "unknown"
```

**Rationale:** Since we've already validated authentication, `ctx.github.check_auth_status()` will return the username. This:

- Removes subprocess call duplication (Ensure already checked via ctx.github)
- Uses existing context integration methods
- Maintains fallback to "unknown" if username unavailable
- Follows LBYL pattern

### Benefits

1. ✅ **Explicit early validation** - User gets clear error message if gh not authenticated
2. ✅ **LBYL compliance** - Checks conditions before operations
3. ✅ **Consistent error styling** - Red "Error:" prefix handled by Ensure
4. ✅ **Better UX** - Clear actionable error instead of silent fallback
5. ✅ **Code reduction** - Removes 14 lines of try/catch boilerplate

### Files to Modify

- `src/erk/cli/commands/submit.py`

### Testing Considerations

- Verify behavior when gh not installed
- Verify behavior when gh not authenticated
- Verify normal flow still retrieves username correctly
- Check that workflow trigger (line 118) still works
