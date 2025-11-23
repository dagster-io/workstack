# Refactor Time Injection via ErkContext

## Problem

Currently using awkward `__wrapped__` pattern in tests because Time is passed as decorator parameter instead of through ErkContext dependency injection.

## Solution

Move Time to ErkContext following the established architecture pattern (ABC → Real → Fake).

## Implementation Steps

### 1. Move Time ABC to Core Location

**Create:** `src/erk/core/time/abc.py`

- Move `Time` ABC from `src/erk/cli/commands/land_stack/time_provider.py`
- Standard ABC interface with `sleep(seconds: float) -> None` method

### 2. Create Real Implementation

**Create:** `src/erk/core/time/real.py`

- Move `RealTime` class (currently in `time_provider.py`)
- Implements `time.sleep()` wrapper

### 3. Move Fake to Standard Location

**Update:** `tests/fakes/time.py` (rename from `time_provider.py`)

- Move `FakeTime` to match naming pattern (e.g., `git.py`, `github.py`)
- Keep mutation tracking via `sleep_calls` property

### 4. Add Time to ErkContext

**Update:** `src/erk/core/context.py`

- Add `time: Time` field to dataclass (~line 60)
- Add to `for_test()` with default `FakeTime()` (~line 150)
- Add to `minimal()` with default `FakeTime()` (~line 80)
- Add to `create_context()` with `RealTime()` (~line 400)

### 5. Update Retry Decorator

**Update:** `src/erk/cli/commands/land_stack/retry.py`

- Remove `time_provider` parameter from `retry_with_backoff()`
- Change decorator to accept function that takes `ctx` as first parameter
- Extract `ctx.time` inside wrapper and use that
- **Alternative**: Keep decorator simple, move retry logic to function that accepts ctx

### 6. Update Retry Call Sites

**Update:** `src/erk/cli/commands/land_stack/execution.py`

- Remove `time_provider` argument from decorator
- Function already has `ctx` parameter, decorator will extract `ctx.time`

### 7. Simplify Tests

**Update:** `tests/commands/land_stack/test_execution.py`

- **Remove** the awkward `check_pr_mergeable` fixture with `__wrapped__`
- Simply inject `FakeTime` via `ErkContext.for_test(time=FakeTime())`
- Call `_check_pr_mergeable_with_retry` directly (no fixture needed)
- Tests become much simpler and clearer

### 8. Delete Old Files

- Delete `src/erk/cli/commands/land_stack/time_provider.py`
- Delete `tests/fakes/time_provider.py` (after moving to `time.py`)

## Result

- Consistent with all other ErkContext dependencies (Git, GitHub, Shell, etc.)
- No more `__wrapped__` hacks in tests
- Tests inject FakeTime via standard `ErkContext.for_test()` pattern
- Future-ready for potential DryRunTime wrapper if needed
- Cleaner, more maintainable code following established patterns

## Technical Details

### Current Architecture

ErkContext uses frozen dataclass with injected dependencies:

```python
@dataclass(frozen=True)
class ErkContext:
    git: Git
    github: GitHub
    # ... other dependencies
```

All dependencies follow ABC → Real → Fake pattern:

- **ABC**: `src/erk/core/{module}/abc.py`
- **Real**: `src/erk/core/{module}/real.py`
- **Fake**: `tests/fakes/{module}.py`

### Current Time Usage

Time is currently passed as optional parameter to `retry_with_backoff()` decorator:

```python
@retry_with_backoff(max_attempts=5, base_delay=2.0, backoff_factor=2.0, time_provider=FakeTime())
```

This requires awkward test patterns with `__wrapped__` to re-apply decorator.

### Proposed Time Usage

Time will be injected via ErkContext like other dependencies:

```python
# In production
ctx = ErkContext(..., time=RealTime())

# In tests
ctx = ErkContext.for_test(time=FakeTime())

# Decorator extracts from ctx
@retry_with_backoff(max_attempts=5, base_delay=2.0, backoff_factor=2.0)
def _check_pr_mergeable_with_retry(ctx: ErkContext, ...):
    # Decorator uses ctx.time internally
    ...
```

### Benefits

1. **Consistency**: Matches Git, GitHub, Shell, etc.
2. **Testability**: No `__wrapped__` hacks needed
3. **Simplicity**: Tests use standard `for_test()` pattern
4. **Extensibility**: Can add DryRunTime wrapper later
5. **Maintainability**: Clear dependency injection throughout
