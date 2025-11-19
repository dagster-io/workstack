# Exception Handling - LBYL Over EAFP

## Core Principle

**ALWAYS use LBYL (Look Before You Leap), NEVER EAFP for control flow**

LBYL means checking conditions before acting. EAFP (Easier to Ask for Forgiveness than Permission) means trying operations and catching exceptions. In dignified Python, we strongly prefer LBYL.

## Dictionary Access Patterns

```python
# ✅ CORRECT: Membership testing
if key in mapping:
    value = mapping[key]
    process(value)
else:
    handle_missing()

# ✅ ALSO CORRECT: .get() with default
value = mapping.get(key, default_value)
process(value)

# ✅ CORRECT: Check before nested access
if "config" in data and "timeout" in data["config"]:
    timeout = data["config"]["timeout"]

# ❌ WRONG: KeyError as control flow
try:
    value = mapping[key]
except KeyError:
    handle_missing()

# ❌ WRONG: Nested try/except
try:
    timeout = data["config"]["timeout"]
except KeyError:
    timeout = default_timeout
```

## When Exceptions ARE Acceptable

### 1. Error Boundaries

```python
# ✅ ACCEPTABLE: CLI command error boundary
@click.command("create")
@click.pass_obj
def create(ctx: ErkContext, name: str) -> None:
    """Create a worktree."""
    try:
        create_worktree(ctx, name)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Git command failed: {e.stderr}", err=True)
        raise SystemExit(1)
```

### 2. Third-Party API Compatibility

```python
# ✅ ACCEPTABLE: Third-party API forces exception handling
def _get_bigquery_sample(sql_client, table_name):
    """
    BigQuery's TABLESAMPLE doesn't work on views.
    There's no reliable way to determine a priori whether
    a table supports TABLESAMPLE.
    """
    try:
        return sql_client.run_query(f"SELECT * FROM {table_name} TABLESAMPLE...")
    except Exception:
        return sql_client.run_query(f"SELECT * FROM {table_name} ORDER BY RAND()...")
```

### 3. Adding Context Before Re-raising

```python
# ✅ ACCEPTABLE: Adding context before re-raising
try:
    process_file(config_file)
except yaml.YAMLError as e:
    raise ValueError(f"Failed to parse config file {config_file}: {e}") from e
```

## Encapsulation Pattern

When you must violate exception norms, encapsulate the violation:

```python
def _get_sample_with_fallback(client, table):
    """Encapsulated exception handling with clear documentation."""
    try:
        return client.sample_method(table)
    except SpecificAPIError:
        # Documented reason for exception handling
        return client.fallback_method(table)

# Caller doesn't see the exception handling
def analyze(table):
    sample = _get_sample_with_fallback(client, table)
    return process(sample)
```

## Key Takeaways

1. **Default position**: Let exceptions bubble to error boundaries
2. **Check first**: Use `if` statements to validate conditions
3. **Avoid**: Using exceptions for control flow or expected cases
4. **Encapsulate**: When exceptions are necessary, hide them in helper functions
5. **Document**: Always explain why exception handling is necessary when used
