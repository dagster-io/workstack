# Dagster Code Smells - Production-Tested Python Standards

> **Context**: These code smells come from real production issues at Dagster Labs. Each represents actual bugs that occurred in a large Python codebase with strong typing culture. They complement the dignified-python skill's foundational principles.

## Quick Reference Guide

| If you're about to write...                   | Check this section                                                   |
| --------------------------------------------- | -------------------------------------------------------------------- |
| `@property` with I/O or expensive computation | [Performance Expectations](#3-performance-expectations-property-len) |
| Function with many optional parameters        | [Parameter Design](#5-parameter-design-keyword-arguments)            |
| `repr()` for sorting or hashing               | [String Representation Abuse](#1-string-representation-abuse-repr)   |
| Try/except without explicit error             | [Error Boundaries](#4-error-boundaries-early-validation)             |
| Context object passed everywhere              | [Context Coupling](#8-context-coupling)                              |
| Function with 10+ local variables             | [Complexity Management](#10-complexity-management-local-variables)   |
| Class with 50+ methods                        | [God Classes](#9-god-classes)                                        |
| Context manager assigned to variable          | [Context Manager Patterns](#11-context-manager-patterns)             |

## Table of Contents

### Function & API Design

1. [String Representation Abuse (`repr`)](#1-string-representation-abuse-repr)
2. [Default Parameter Values](#2-default-parameter-values)
3. [Performance Expectations (`@property`, `__len__`)](#3-performance-expectations-property-len)
4. [Error Boundaries (Early Validation)](#4-error-boundaries-early-validation)

### Parameter Design

5. [Keyword Arguments](#5-parameter-design-keyword-arguments)
6. [Invalid Parameter Combinations](#6-invalid-parameter-combinations)
7. [Parameter Anxiety](#7-parameter-anxiety)

### Code Organization

8. [Context Coupling](#8-context-coupling)
9. [God Classes](#9-god-classes)
10. [Complexity Management (Local Variables)](#10-complexity-management-local-variables)

### Python-Specific

11. [Context Manager Patterns](#11-context-manager-patterns)

### Meta-Principles

12. [Understanding Code Smells](#12-understanding-code-smells)

---

## Function & API Design

### 1. String Representation Abuse (`repr`)

**DON'T** use `repr()` for programmatic operations:

```python
# ❌ WRONG - Using repr for sorting
items.sort(key=lambda x: repr(x))

# ❌ WRONG - Using repr as dictionary key
cache[repr(obj)] = computed_value

# ❌ WRONG - Using repr for comparison
if repr(obj1) == repr(obj2):
    do_something()
```

**DO** use proper protocols:

```python
# ✅ CORRECT - Implement __hash__ and __eq__
class MyClass:
    def __hash__(self) -> int:
        return hash((self.field1, self.field2))

    def __eq__(self, other) -> bool:
        if not isinstance(other, MyClass):
            return False
        return self.field1 == other.field1 and self.field2 == other.field2

# ✅ CORRECT - Use dedicated comparison
def compare_objects(obj1, obj2) -> bool:
    return obj1.key == obj2.key
```

**Rationale**: `repr()` is for debugging/logging only. Engineers may change `__repr__` without realizing it's used programmatically, causing subtle bugs.

**Real Bug**: Dagster PR #21497 - Using `repr()` for sorting created hard-to-diagnose failures.

---

### 2. Default Parameter Values

**DON'T** provide defaults for "schlepping" functions (that organize and pass parameters):

```python
# ❌ WRONG - Dangerous default
def execute_job(
    job: JobDefinition,
    instance: DagsterInstance,
    asset_selection: Optional[Sequence[AssetKey]] = None,  # BAD!
) -> JobExecutionResult:
    # If caller forgets asset_selection, executes EVERYTHING
    return job.execute(instance, asset_selection or job.all_assets)
```

**DO** require explicit parameters:

```python
# ✅ CORRECT - Force caller to be explicit
def execute_job(
    job: JobDefinition,
    instance: DagsterInstance,
    asset_selection: Sequence[AssetKey],  # Required, no default
) -> JobExecutionResult:
    return job.execute(instance, asset_selection)

# Caller must consciously decide
execute_job(job, instance, asset_selection=specific_assets)
# Or explicitly pass all
execute_job(job, instance, asset_selection=job.all_assets)
```

**Rationale**: Default `None` often means "do everything", which is dangerous. Engineers forget to thread selections through, causing unintended executions.

**Real Bug**: UI selection was forgotten, executing entire job instead of selection.

---

### 3. Performance Expectations (`@property`, `__len__`)

**DON'T** hide expensive operations behind cheap-looking interfaces:

```python
# ❌ WRONG - Property doing I/O
class DataSet:
    @property
    def size(self) -> int:
        # Fetches from database!
        return self._fetch_count_from_db()

# ❌ WRONG - __len__ doing expensive computation
class PartitionSubset:
    def __len__(self) -> int:
        # Materializes ALL partition keys!
        return len(list(self._generate_all_partitions()))
```

**DO** make cost explicit or cache results:

```python
# ✅ CORRECT - Method name indicates cost
class DataSet:
    def fetch_size_from_db(self) -> int:
        return self._fetch_count_from_db()

# ✅ CORRECT - Cached for immutable objects
from functools import cached_property

@frozen
class PartitionSubset:
    @cached_property
    def size(self) -> int:
        # Computed once, cached forever (immutable)
        return len(list(self._generate_all_partitions()))

# ✅ CORRECT - Precomputed
class EfficientSubset:
    def __init__(self, partitions: Sequence[str]):
        self._partitions = partitions
        self._count = len(partitions)  # Precompute

    def __len__(self) -> int:
        return self._count  # O(1)
```

**Rationale**: Engineers assume `@property` and `__len__` are cheap. They'll use them in loops without thinking.

**Real Bug**: Customer on Discord - `AssetSubset.size` property triggered 10,000+ partition key materializations via expensive cron parsing.

---

### 4. Error Boundaries (Early Validation)

**DON'T** let invalid values propagate:

```python
# ❌ WRONG - Error surfaces deep in stack
def process_value(value):
    # No validation
    wrapped = Wrapper(value)
    return wrapped.compute()  # TypeError here if value wrong type

process_value("123")  # Mistake here, error elsewhere
```

**DO** validate at entry points:

```python
# ✅ CORRECT - Validate immediately
from dagster import _check as check

def process_value(value):
    check.int_param(value, "value")  # Error surfaces HERE
    wrapped = Wrapper(value)
    return wrapped.compute()

# ✅ CORRECT - Full validation in constructors
class AssetSpec:
    def __new__(cls, key, *, description=None, metadata=None):
        return super().__new__(
            cls,
            key=AssetKey.from_coercible(key),
            description=check.opt_str_param(description, "description"),
            metadata=check.opt_mapping_param(metadata, "metadata"),
        )
```

**Rationale**: Errors far from their source are expensive to debug. They're non-deterministic and context-dependent.

**Pattern**: Use Dagster's `check` module or similar validation at every public API boundary.

---

## Parameter Design

### 5. Parameter Design (Keyword Arguments)

**DON'T** use positional arguments for non-obvious parameters:

```python
# ❌ WRONG - Meaning unclear
result = process(None, False, True, 5)

# ❌ WRONG - Even with comments at callsite
result = process(
    None,  # optional_list
    False,  # sort
    True,  # validate
    5,  # retries
)
```

**DO** use keyword arguments:

```python
# ✅ CORRECT - Self-documenting
result = process(
    optional_list=None,
    sort=False,
    validate=True,
    retries=5
)

# ✅ CORRECT - Enforce keyword-only with *
def process(*, optional_list=None, sort=False, validate=True, retries=3):
    pass
```

**Exception**: Obvious positional arguments are fine:

```python
# ✅ OK - Meaning is obvious
sum = add(x, y)
point = Point(x, y)
range(10, 20)
```

**Rationale**: Keyword-only arguments can be reordered later (two-way door). Positional → keyword-only is a breaking change.

---

### 6. Invalid Parameter Combinations

**DON'T** create functions with invalid parameter states:

```python
# ❌ WRONG - Invalid combinations possible
def configure(
    use_cache: Optional[bool] = None,
    cache_size: Optional[int] = None,
    cache_ttl: Optional[int] = None
):
    if use_cache is False and (cache_size or cache_ttl):
        raise ValueError("Cannot specify cache settings when cache disabled")
    if use_cache and not cache_size:
        raise ValueError("Must specify cache_size when cache enabled")
```

**DO** use type system to prevent invalid states:

```python
# ✅ CORRECT - Union type
CacheConfig = Union[
    Literal["disabled"],
    CacheSettings
]

@dataclass
class CacheSettings:
    size: int
    ttl: int

def configure(cache: CacheConfig):
    if cache == "disabled":
        # No cache
    else:
        # Use cache.size and cache.ttl

# ✅ CORRECT - Separate functions
def configure_with_cache(size: int, ttl: int):
    pass

def configure_without_cache():
    pass
```

**Rationale**: Type system should make invalid states unrepresentable. Runtime validation indicates design flaw.

**Real Case**: `ReconstructableJob.get_subset` had mutually exclusive parameters that could be set simultaneously.

---

### 7. Parameter Anxiety

**DON'T** add too many behavioral parameters:

```python
# ❌ WRONG - 2^4 = 16 possible code paths!
def process_data(
    data: str,
    validate: bool = True,
    normalize: bool = True,
    cache: bool = False,
    async_mode: bool = False
):
    if validate:
        # branch 1
    if normalize:
        # branch 2
    if cache:
        # branch 3
    if async_mode:
        # branch 4
```

**DO** decompose or compose explicitly:

```python
# ✅ CORRECT - Separate concerns
def validate_data(data: str) -> str:
    # validation only
    return validated

def normalize_data(data: str) -> str:
    # normalization only
    return normalized

# Caller composes explicitly
data = validate_data(raw_data)
data = normalize_data(data)

# ✅ CORRECT - Configuration object for related options
@dataclass
class ProcessingConfig:
    validation_rules: ValidationRules
    normalization: NormalizationType

def process_data(data: str, config: ProcessingConfig):
    # Single configuration parameter
    pass
```

**Behavioral vs. Data Parameters**:

- **Behavioral**: Affect control flow (if/else branches)
- **Data**: Just passed through (no branches)

**Formula**: N boolean parameters = 2^N possible paths

**Rationale**: Exponential complexity overwhelms cognitive capacity. "Parameter anxiety" is valid intuition.

---

## Code Organization

### 8. Context Coupling

**DON'T** pass context objects to generic code:

```python
# ❌ WRONG - Unnecessarily couples to context
def calculate_total(context: AppContext) -> int:
    # Why does addition need the whole context?
    return context.value1 + context.value2

def format_output(context: AppContext, total: int) -> str:
    # Generic formatting shouldn't know about app context
    return f"{context.prefix}: {total}"
```

**DO** extract needed values at boundaries:

```python
# ✅ CORRECT - Extract at entry point
def handle_request(context: AppContext):
    # Context used only at boundary
    total = calculate_total(context.value1, context.value2)
    output = format_output(context.prefix, total)
    return output

def calculate_total(value1: int, value2: int) -> int:
    # Generic, reusable
    return value1 + value2

def format_output(prefix: str, total: int) -> str:
    # Generic, testable
    return f"{prefix}: {total}"
```

**Rationale**: Context objects couple code to specific execution environment. Generic code with specific values is reusable.

**Real Case**: PR #21897 required major refactoring to extract scheduling logic from daemon-specific context.

---

### 9. God Classes

**DON'T** let classes accumulate unbounded responsibilities:

```python
# ❌ WRONG - God class doing everything
class ApplicationManager:
    # Database operations
    def save_user(self, user): ...
    def load_user(self, id): ...

    # Authentication
    def authenticate(self, credentials): ...
    def check_permissions(self, user, resource): ...

    # Email sending
    def send_email(self, to, subject, body): ...

    # Report generation
    def generate_report(self, type, params): ...

    # ... 200+ more methods
```

**DO** decompose into focused components:

```python
# ✅ CORRECT - Single responsibility
class UserRepository:
    def save(self, user): ...
    def load(self, id): ...

class AuthService:
    def authenticate(self, credentials): ...
    def check_permissions(self, user, resource): ...

class EmailService:
    def send(self, to, subject, body): ...

class ReportGenerator:
    def generate(self, type, params): ...
```

**Decomposition Tactics**:

1. **Implementation First** (Two-way door):

```python
# Step 1: Break up implementation
class GodClass:
    def method1(self):
        return self._component1.method1()

    def method2(self):
        return self._component2.method2()
```

2. **Wrapper/Namespace** (When too intertwined):

```python
# Step 2: Introduce wrappers
class UserAPI:
    def __init__(self, god_instance):
        self._instance = god_instance

    def save_user(self, user):
        return self._instance.save_user(user)
```

**Real Case**: `DagsterInstance` - 3200+ lines, 180+ methods, unknowable complexity.

---

### 10. Complexity Management (Local Variables)

**DON'T** let functions accumulate many local variables:

```python
# ❌ WRONG - Too many locals
def process_complex_data():
    raw_data = fetch_data()
    validated = validate(raw_data)
    normalized = normalize(validated)

    config = load_config()
    rules = parse_rules(config)

    interim_result1 = apply_rules(normalized, rules)
    interim_result2 = transform(interim_result1)
    interim_result3 = filter_data(interim_result2)

    metadata = extract_metadata(interim_result3)
    summary = generate_summary(metadata)

    cache_key = compute_cache_key(summary)
    cached = check_cache(cache_key)

    # ... 20+ more variables
```

**DO** use immutable value objects:

```python
# ✅ CORRECT - Formalize dependencies
@dataclass(frozen=True)
class ProcessingState:
    @cached_property
    def raw_data(self):
        return fetch_data()

    @cached_property
    def validated(self):
        return validate(self.raw_data)

    @cached_property
    def normalized(self):
        return normalize(self.validated)

    @cached_property
    def final_result(self):
        return transform(
            filter_data(
                apply_rules(self.normalized, self.rules)
            )
        )

    @cached_property
    def rules(self):
        return parse_rules(load_config())

def process_complex_data():
    state = ProcessingState()
    return state.final_result
```

**Python Scope Issues**:

- Variables can be referenced before assignment
- Inner functions can mutate outer scope
- No variable declarations
- Shadow variables cause confusion

**Rationale**: Too many locals indicates function doing too much. Cached properties formalize dependency DAG.

**Real Case**: `multi_asset` decorator - 200+ lines, 37 locals. Refactored in PR #22230.

---

## Python-Specific

### 11. Context Manager Patterns

**DON'T** assign context managers to variables:

```python
# ❌ WRONG - Context manager in variable
if condition:
    cm = open("file1.txt")
else:
    cm = open("file2.txt")

# Used later... maybe
with cm as f:
    content = f.read()

# ❌ WRONG - Using nullcontext
from contextlib import nullcontext

if needs_lock:
    lock_cm = threading.Lock()
else:
    lock_cm = nullcontext()  # Dummy context manager

with lock_cm:
    do_work()
```

**DO** create dedicated context managers:

```python
# ✅ CORRECT - Dedicated context manager
@contextmanager
def open_appropriate_file(condition):
    if condition:
        with open("file1.txt") as f:
            yield f
    else:
        with open("file2.txt") as f:
            yield f

with open_appropriate_file(condition) as f:
    content = f.read()

# ✅ CORRECT - Handle logic inside context manager
@contextmanager
def maybe_lock(needs_lock):
    if needs_lock:
        lock = threading.Lock()
        with lock:
            yield
    else:
        yield  # No lock needed

with maybe_lock(needs_lock):
    do_work()
```

**Rationale**: Assigning context managers creates distance between creation and use. Non-idiomatic and error-prone.

**Real Case**: `dg` tool validation logic - complex conditional context managers made code hard to follow.

---

## 12. Understanding Code Smells

### What Are Code Smells?

Code smells are patterns that indicate potential problems in code design. They're not bugs, but they make bugs more likely and code harder to maintain.

### Why These Matter

1. **Battle-Tested**: Each smell represents real production bugs at Dagster Labs
2. **Python-Specific**: Addresses Python's unique challenges (scoping, typing, conventions)
3. **Scale-Sensitive**: Problems that emerge in large codebases
4. **Team Dynamics**: Helps develop "collective taste" in engineering teams

### Key Principles

1. **Explicitness > Implicitness**: Make intent clear at call sites
2. **Type System as Guard Rail**: Use types to prevent invalid states
3. **Early Error Detection**: Surface problems at point of mistake
4. **Composition > Parameters**: Decompose complex functions
5. **Reusability Through Generics**: Don't couple to context unnecessarily
6. **Manageable Complexity**: Keep cyclomatic complexity reasonable
7. **Idiomatic Python**: Follow Python conventions and expectations
8. **Immutability for Clarity**: Use frozen dataclasses and cached properties
9. **Clear Contracts**: Make function behavior obvious from signature
10. **Testability**: Design for easy testing and isolation

### Trade-offs

These aren't absolute rules. Sometimes you need to:

- Accept complexity for performance
- Use defaults for developer ergonomics
- Create large classes for backwards compatibility

The key is being conscious about trade-offs and documenting them.

---

## Related Skills

- **dignified-python**: Core Python standards (LBYL, type annotations, imports)
- **workstack**: Project-specific standards and workflows

## References

- Original Dagster discussions: `docs/reference/dagster-discussions/`
- Real PRs showing fixes: Referenced in each smell section
- Dagster codebase: Where these patterns were discovered and fixed
