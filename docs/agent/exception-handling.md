# Exception Handling Guide

**📍 You are here**: [CLAUDE.md](../../CLAUDE.md) → docs/agent/exception-handling.md

**Purpose**: Complete guide to exception handling in workstack. This codebase has strict rules about exception usage.

**Related docs**:

- [CLAUDE.md](../../CLAUDE.md) - Core coding rules
- [patterns.md](patterns.md) - Code examples and patterns
- [guide.md](guide.md) - Documentation index

---

## Table of Contents

- [General Principles](#general-principles)
- [LBYL vs EAFP](#lbyl-vs-eafp)
- [Critical Enforcement](#critical-enforcement)
- [Acceptable Uses](#acceptable-uses)
- [Implementation Patterns](#implementation-patterns)
  - [Encapsulation Pattern](#encapsulation-pattern)
  - [Proactive Checking](#proactive-checking)
  - [Context Manager Pattern for Error Boundaries](#context-manager-pattern-for-error-boundaries)
- [Dictionary Access](#dictionary-access)
- [Validation and Input Checking](#validation-and-input-checking)
- [File Processing](#file-processing)
- [Path Resolution and Comparison](#path-resolution-and-comparison)
- [Exception Swallowing](#exception-swallowing)
- [Summary Checklist](#summary-checklist)

---

## General Principles

This codebase follows specific norms for exception handling to maintain clean, predictable code:

- **By default, exceptions should NOT be used as control flow**
- **Do NOT implement alternative paths in catch blocks** - exceptions should bubble up the stack to be handled at appropriate boundaries
- **Avoid catching broad `Exception` types** unless you have a specific reason
- **Prefer "Look Before You Leap" (LBYL) over "Easier to Ask for Forgiveness than Permission" (EAFP)** - Check conditions before performing operations rather than catching exceptions

---

## LBYL vs EAFP

### Look Before You Leap (LBYL) Pattern

**ALWAYS prefer checking conditions proactively** rather than using try/except blocks:

```python
# ✅ PREFERRED: LBYL - Check before acting
if has_capability(obj):
    result = use_capability(obj)
else:
    result = use_alternative(obj)

# ❌ AVOID: EAFP - Try and catch exceptions
try:
    result = use_capability(obj)
except CapabilityError:
    result = use_alternative(obj)
```

### Benefits of LBYL

- **More explicit about intent** - Reader immediately understands this is a conditional path
- **Easier to understand control flow** - No hidden exception paths
- **Better performance** - No exception overhead for normal flow
- **Clearer distinction between errors and normal flow** - Exceptions indicate real problems
- **Easier to debug** - Exceptions in stack traces indicate genuine issues

### When EAFP is Acceptable

Exception handling is acceptable in these rare cases:

- **No practical way to check the condition beforehand** - The check would duplicate internal logic
- **Checking would require duplicating the operation's logic** - Testing would be as expensive as doing
- **Third-party APIs that use exceptions for control flow** - External library design forces it
- **Race conditions where state could change between check and use** - File system operations where file could be deleted between check and use

---

## Critical Enforcement

⚠️ **Claude Code: You MUST NOT violate these exception handling rules. Specifically:**

1. **NEVER write try/except blocks for alternate execution paths** - Let exceptions bubble up instead of catching them to try alternative approaches
2. **NEVER swallow exceptions silently** - Don't use empty `except:` blocks or `except Exception: pass` patterns
3. **NEVER catch exceptions just to continue with different logic** - This masks real problems and makes debugging impossible
4. **ALWAYS let exceptions propagate to appropriate error boundaries** - Only handle exceptions at CLI level, column analysis boundaries, or when dealing with third-party API quirks

**If you find yourself writing try/except, STOP and ask: "Should this exception bubble up instead?"**

The default answer should be: **YES, let it bubble up.**

---

## Acceptable Uses

### 1. Error Boundaries

Meaningful divisions in software that have sensible default error behavior:

- **CLI commands** - Top-level exception handlers for user-friendly error messages
- **Column analysis operations** - Individual column failures shouldn't fail entire table analysis

Example:

```python
@click.command("create")
@click.pass_obj
def create(ctx: WorkstackContext, name: str) -> None:
    """Create a worktree."""
    try:
        # Command implementation
        create_worktree(ctx, name)
    except subprocess.CalledProcessError as e:
        # Error boundary: convert technical error to user-friendly message
        click.echo(f"Error: Git command failed: {e.stderr}", err=True)
        raise SystemExit(1)
```

### 2. API Compatibility

Compensating for APIs that use exceptions for control flow:

- When third-party APIs use exceptions to indicate missing keys/values
- When database dialects have different capabilities that can't be detected a priori

Example (acceptable because BigQuery API design forces it):

```python
def _get_bigquery_sample(sql_client, table_name):
    """
    Try BigQuery TABLESAMPLE, use alternate approach for views.

    BigQuery's TABLESAMPLE doesn't work on views, so we use exception handling
    to detect this case. This is acceptable because there's no reliable way
    to determine a priori whether a table supports TABLESAMPLE.
    """
    try:
        return sql_client.run_query(f"SELECT * FROM {table_name} TABLESAMPLE...")
    except Exception:
        return sql_client.run_query(f"SELECT * FROM {table_name} ORDER BY RAND()...")
```

### 3. Embellishing Exceptions

Adding context to in-flight exceptions before re-raising:

```python
try:
    process_file(config_file)
except yaml.YAMLError as e:
    # Add context about which file failed
    raise ValueError(f"Failed to parse config file {config_file}: {e}") from e
```

---

## Implementation Patterns

### Encapsulation Pattern

When violating exception norms is necessary, **encapsulate the violation within a function**:

```python
# ✅ GOOD: Exception handling encapsulated in helper function
def _get_bigquery_sample_with_alternate(sql_client, table_name, percentage, limit):
    """
    Try BigQuery TABLESAMPLE, use alternate approach for views.

    BigQuery's TABLESAMPLE doesn't work on views, so we use exception handling
    to detect this case. This is acceptable because there's no reliable way
    to determine a priori whether a table supports TABLESAMPLE.
    """
    try:
        return sql_client.run_query(f"SELECT * FROM {table_name} TABLESAMPLE...")
    except Exception:
        return sql_client.run_query(f"SELECT * FROM {table_name} ORDER BY RAND()...")

# Usage - caller doesn't see the exception handling
def analyze_table(table_name):
    sample = _get_bigquery_sample_with_alternate(sql_client, table_name, 10, 1000)
    return analyze_sample(sample)
```

```python
# ❌ BAD: Exception control flow exposed in main logic
def analyze_table(table_name):
    try:
        sample = sql_client.run_query(f"SELECT * FROM {table_name} TABLESAMPLE...")
    except Exception:
        sample = sql_client.run_query(f"SELECT * FROM {table_name} ORDER BY RAND()...")
    return analyze_sample(sample)
```

### Proactive Checking

When possible, check conditions that cause errors before making calls:

```python
# ✅ PREFERRED: Check condition beforehand
if is_view(table_name):
    return get_view_sample(table_name)
else:
    return get_table_sample(table_name)

# ❌ AVOID: Using exceptions to discover the condition
try:
    return get_table_sample(table_name)  # Will fail on views
except Exception:
    return get_view_sample(table_name)
```

### Context Manager Pattern for Error Boundaries

When you need exception handling for resource management or cleanup at error boundaries, **encapsulate it in a context manager**. This keeps business logic clean while properly handling necessary exceptions:

```python
# ✅ GOOD: Exception handling encapsulated in context manager (example pattern)
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def worktree_analysis_boundary(worktree_path: Path):
    """Error boundary for individual worktree analysis.

    Allows batch analysis to continue even if one worktree fails.
    Acceptable because: individual worktree failures shouldn't crash
    entire multi-worktree operation.
    """
    try:
        yield
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # Error boundary: provide default behavior for failures
        click.echo(f"Warning: Skipping {worktree_path.name}: {e}", err=True)
        # Operation continues with other worktrees

# ✅ Business logic remains clean and exception-free
def analyze_all_worktrees() -> dict[Path, str]:
    """Analyze all worktrees, skipping any that fail."""
    results = {}
    for wt_path in get_worktree_paths():
        with worktree_analysis_boundary(wt_path):
            # This might fail, but won't crash entire operation
            branch = get_current_branch(wt_path)
            results[wt_path] = branch
    return results
```

**Benefits:**

- **Business logic stays clean** - No try/except blocks cluttering the main code
- **Exception handling is encapsulated and reusable** - Write once, use everywhere
- **Clear separation of concerns** - Error handling logic separated from business logic
- **Follows LBYL principle in business logic** - Only use exceptions at proper boundaries
- **Easy to test** - Both the context manager and business logic can be tested independently

**When to use this pattern:**

- Resource cleanup (files, connections, locks)
- Atomic operations that need rollback on error
- Any error boundary that requires exception handling

---

## Dictionary Access

### Using `in` for Membership Testing

**ALWAYS use membership testing (`in`) before accessing dictionary keys** instead of catching `KeyError`:

```python
# ✅ PREFERRED: Proactive key existence checking
if key in mapping:
    value = mapping[key]
    # process value
    process(value)
else:
    # handle missing key case
    handle_missing_key()

# ❌ AVOID: Using KeyError as control flow
try:
    value = mapping[key]
    # process value
    process(value)
except KeyError:
    handle_missing_key()
```

**Rationale**: Membership testing is more explicit about intent, performs better, and avoids using exceptions for control flow. The `in` operator clearly indicates that you're checking for key existence before access.

### Alternative: Use `.get()` with Default

For simple cases where you just need a default value:

```python
# ✅ GOOD: Using .get() with default
value = mapping.get(key, default_value)
process(value)

# ✅ ALSO GOOD: Check membership first for complex logic
if key in mapping:
    value = mapping[key]
    # Complex processing
    complex_process(value)
else:
    # Complex fallback logic
    complex_fallback()
```

---

## Validation and Input Checking

### Exception Transformation

**DO NOT catch exceptions just to re-raise them with different messages** unless you're adding meaningful context:

```python
# ❌ BAD: Unnecessary exception transformation
try:
    croniter(cron_string, now).get_next(datetime)
except Exception as e:
    raise ValueError(f"Invalid cron string: {e}")

# ✅ GOOD: Let the original exception bubble up with its specific error details
croniter(cron_string, now).get_next(datetime)

# ✅ ACCEPTABLE: Adding meaningful context before re-raising
try:
    croniter(cron_string, now).get_next(datetime)
except Exception as e:
    raise ValueError(
        f"Cron job '{job_name}' has invalid schedule '{cron_string}': {e}"
    ) from e
```

**Rationale**: The original exception from third-party libraries (like `croniter`) often contains more precise error information than generic wrapper messages. Only transform exceptions when you're adding valuable context that helps with debugging or user experience.

### When to Add Context

Add context when the exception crosses an abstraction boundary:

```python
# ✅ GOOD: Adding context at abstraction boundary
def load_user_config(username: str) -> Config:
    """Load configuration for a user."""
    config_path = Path(f"/configs/{username}.toml")
    try:
        return parse_toml(config_path)
    except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
        # Add username context - caller doesn't know which file failed
        raise ConfigError(f"Failed to load config for user {username}: {e}") from e
```

---

## File Processing

### Fail Fast on Data Corruption

**DO NOT catch exceptions during file processing operations** unless at appropriate error boundaries:

```python
# ❌ BAD: Silently skipping malformed files
for context_file in files:
    try:
        context_data = yaml.safe_load(read_file(context_file))
        process_context(context_data)
    except (yaml.YAMLError, ValidationError) as e:
        print(f"Warning: Skipping malformed file {context_file}: {e}")
        continue  # This hides real problems

# ✅ GOOD: Let exceptions bubble up to reveal systemic issues
for context_file in files:
    context_data = yaml.safe_load(read_file(context_file))  # Will fail fast on corruption
    process_context(context_data)
```

**Rationale**: If files are malformed, it indicates:

- **CI/tooling has failed** - Your validation pipeline is broken
- **Data corruption has occurred** - Disk/network issues
- **System is in an untrustworthy state** - Unknown extent of damage

The problem should be fixed at its source (CI, validation, tooling) rather than masked with exception handling. Silently skipping corrupted files can lead to:

- Incomplete analysis with no indication of the gap
- Silent data loss that compounds over time
- False sense of security that "everything is working"

### When File Exceptions Are Acceptable

At appropriate error boundaries (e.g., CLI level):

```python
# ✅ ACCEPTABLE: Error boundary at CLI level
@click.command("process")
@click.argument("config_file")
def process_cmd(config_file: str) -> None:
    """Process data according to config file."""
    try:
        config = load_config(config_file)
        process_data(config)
    except FileNotFoundError:
        click.echo(f"Error: Config file not found: {config_file}", err=True)
        raise SystemExit(1)
    except yaml.YAMLError as e:
        click.echo(f"Error: Invalid YAML in {config_file}: {e}", err=True)
        raise SystemExit(1)
```

---

## Path Resolution and Comparison

**Common Anti-Pattern**: Using try/except with `.resolve()` or `.is_relative_to()`.

### The Wrong Pattern

```python
# ❌ BAD: Using exceptions for path validation
for wt_path in worktree_paths:
    try:
        wt_path_resolved = wt_path.resolve()
        if current_dir.is_relative_to(wt_path_resolved):
            current_worktree = wt_path_resolved
            break
    except (OSError, ValueError):
        continue
```

### The Correct Pattern

```python
# ✅ GOOD: Check exists before resolution (LBYL)
for wt_path in worktree_paths:
    if wt_path.exists():
        wt_path_resolved = wt_path.resolve()
        if current_dir.is_relative_to(wt_path_resolved):
            current_worktree = wt_path_resolved
            break
```

### Why This Matters

1. **`.resolve()` can raise `OSError`** for invalid paths, permission issues, symlink loops
2. **`.is_relative_to()` can raise `ValueError`** in edge cases
3. **Using exceptions for flow control violates LBYL principle**
4. **`.exists()` makes intent explicit** - you're checking for valid paths
5. **Avoids exception overhead** for normal operation

**Rule**: Always check `.exists()` before calling `.resolve()` or path comparison methods.

---

## Exception Swallowing

### Never Swallow Silently

**NEVER swallow exceptions silently** - always let them bubble up to appropriate error boundaries:

```python
# ❌ BAD: Silently swallowing exceptions
try:
    if not self.is_dir(path):
        return
    for name in self.listdir(path):
        if fnmatch.fnmatch(name, pattern):
            yield f"{path}/{name}" if path else name
except (FileNotFoundError, NotADirectoryError):
    return  # Silently fails, hiding real problems

# ✅ GOOD: Let exceptions bubble up
if not self.is_dir(path):
    return
for name in self.listdir(path):
    if fnmatch.fnmatch(name, pattern):
        yield f"{path}/{name}" if path else name
```

**Why this is bad**:

- **Hides genuine errors** - `FileNotFoundError` mid-iteration indicates file system issues
- **Makes debugging impossible** - No indication that something went wrong
- **Masks race conditions** - Directory deleted between check and iteration
- **False success** - Caller thinks operation succeeded when it partially failed

### Never Use Exceptions for Alternate Logic

**NEVER implement alternate execution paths in exception handlers** unless you're at an appropriate error boundary:

```python
# ❌ BAD: Using exceptions for alternate logic
try:
    return PurePosixPath(path).match(pattern)
except ValueError:
    # Alternate path using fnmatch if PurePath.match fails
    return fnmatch.fnmatch(path, pattern)

# ✅ GOOD: Let the original exception bubble up
return PurePosixPath(path).match(pattern)

# ✅ ALSO GOOD: Check condition first if truly needed
if is_valid_posix_path(path):
    return PurePosixPath(path).match(pattern)
else:
    return fnmatch.fnmatch(path, pattern)
```

**Rationale**: Exception swallowing masks real problems and makes debugging extremely difficult. If an exception occurs, it usually indicates a genuine issue that needs to be addressed, not hidden.

### Empty Except Blocks

```python
# ❌ NEVER do this
try:
    risky_operation()
except:
    pass

# ❌ NEVER do this either
try:
    risky_operation()
except Exception:
    pass

# ✅ If you must catch, at least log it
import logging
logger = logging.getLogger(__name__)

try:
    risky_operation()
except Exception as e:
    logger.exception(f"Unexpected error in risky_operation: {e}")
    raise  # Re-raise after logging
```

---

## Summary Checklist

Before writing `try/except`, ask yourself:

- [ ] **Is this at an error boundary?** (CLI level, API boundary, module boundary)
- [ ] **Can I check the condition proactively instead?** (LBYL approach)
- [ ] **Am I adding meaningful context, or just hiding the error?**
- [ ] **Is the third-party API forcing me to use exceptions?** (Document why)
- [ ] **Have I encapsulated the violation in a helper function?** (Keep exception handling localized)
- [ ] **Am I catching specific exceptions, not broad `Exception`?** (Be precise)
- [ ] **Will this exception handler be maintained?** (Don't create technical debt)

**Default answer should be: Let the exception bubble up.**

---

## Common Patterns Summary

| Scenario              | Preferred Approach                        | Avoid                                       |
| --------------------- | ----------------------------------------- | ------------------------------------------- |
| **Dictionary access** | `if key in dict:` or `.get(key, default)` | `try: dict[key] except KeyError:`           |
| **File existence**    | `if path.exists():`                       | `try: open(path) except FileNotFoundError:` |
| **Type checking**     | `if isinstance(obj, Type):`               | `try: obj.method() except AttributeError:`  |
| **Value validation**  | `if is_valid(value):`                     | `try: process(value) except ValueError:`    |
| **Optional feature**  | `if has_feature(obj):`                    | `try: use_feature(obj) except:`             |

---

## Related Documentation

- [CLAUDE.md](../../CLAUDE.md) - Core coding standards
- [patterns.md](patterns.md) - Code examples and patterns
- [guide.md](guide.md) - Documentation index
- [../../tests/CLAUDE.md](../../tests/CLAUDE.md) - Testing patterns

---

## Questions?

If you're unsure whether exception handling is appropriate:

1. Check if you can use LBYL pattern instead
2. Ask: "Is this an error boundary?" (Usually: CLI commands only)
3. Document why the exception is necessary in a comment
4. Encapsulate the exception handling in a helper function
5. When in doubt, let it bubble up
