# CLI Module - Pydantic Serialization Patterns

## Quick Reference: When Pydantic Auto-Serializes Types

| Type        | In Model Fields            | In Arbitrary Dicts     | Solution for Dicts      |
| ----------- | -------------------------- | ---------------------- | ----------------------- |
| `Path`      | ✅ Auto → `str`            | ❌ Requires custom     | `str(path)`             |
| `datetime`  | ✅ Auto → ISO format       | ❌ Requires custom     | `dt.isoformat()`        |
| `dataclass` | ✅ Auto → dict (recursive) | ❌ Requires conversion | `asdict()` then recurse |

**Key insight:** Pydantic's automatic serialization only applies to **typed model fields**, not arbitrary Python objects nested in dicts.

---

## Design Decision: json_output.py Architecture

### Dict-Only Approach with Pydantic Validation Where Needed

The `emit_json()` function accepts only dicts:

```python
def emit_json(data: dict[str, Any]) -> None:
    serialized = _serialize_for_json(data)
    json_str = json.dumps(serialized, indent=2)
    machine_output(json_str)
```

**Rationale:**

1. **Single contract** - Clear expectation: "give me a dict"
   - No union types (`BaseModel | dict`)
   - No branching logic based on type
   - Simple, explicit interface

2. **Pydantic models convert first** - Commands using schemas call `.model_dump(mode='json')`
   - Example: `emit_json(status_model.model_dump(mode='json'))`
   - Pydantic handles Path/datetime serialization during conversion
   - Validation happens at model construction, not at emit time

3. **Custom serialization for dict values** - `_serialize_for_json()` handles special types
   - Path → str conversion
   - datetime → ISO format
   - dataclass → dict recursion

**Why not accept Pydantic models directly?**

- Eliminates dual-path complexity
- Makes conversion explicit at call sites
- Pydantic `.model_dump(mode='json')` already does serialization
- No performance benefit to accepting BaseModel (still converts to dict internally)

---

## Why NOT Use RootModel for Dict Serialization?

### The Tempting (But Wrong) Approach

```python
# ❌ This seems like it would work, but doesn't
from pydantic import RootModel

data = {"path": Path("/test"), "timestamp": datetime.now()}
model = RootModel[dict[str, Any]](data)
json_str = model.model_dump_json()  # ← TypeError: Path not JSON serializable
```

**Why it fails:**

- `RootModel[dict[str, Any]]` tells Pydantic "this is a dict"
- Pydantic only serializes Path/datetime when they're **typed fields**
- Generic `Any` type provides no serialization hints
- The Path/datetime are **dict values**, not model fields

### What Actually Works

**Option 1: Typed model fields** (what Pydantic excels at)

```python
# ✅ Pydantic knows path is a Path field
class MyModel(BaseModel):
    path: Path
    timestamp: datetime

model = MyModel(path=Path("/test"), timestamp=datetime.now())
json_str = model.model_dump_json()  # ← Works: {"path": "/test", "timestamp": "..."}
```

**Option 2: Custom serialization function** (for arbitrary dicts)

```python
# ✅ Explicit control over serialization
def _serialize_for_json(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    # ... handle dicts, lists, nested structures

serialized = _serialize_for_json(data)
json_str = json.dumps(serialized, indent=2)
```

---

## Performance Characteristics

### RootModel Construction Overhead

**Creating a Pydantic model has significant overhead:**

```python
# Every emit_json() call would do this:
model = RootModel[dict[str, Any]](data)  # ← Model construction
json_str = model.model_dump_json()        # ← Validation + serialization
```

**Overhead includes:**

- Schema construction/validation
- Field inspection and type checking
- Serialization setup
- Internal model bookkeeping

**From Pydantic documentation:**

> "Schema construction carries significant overhead...it is recommended to create a TypeAdapter for a given type just once and reuse it"

### Custom Function Performance

```python
# Direct Python recursion - minimal overhead
serialized = _serialize_for_json(data)   # ← Pure Python recursion
json_str = json.dumps(serialized)        # ← Standard library
```

**Characteristics:**

- No model construction
- No validation overhead
- Direct type checking with `isinstance()`
- Minimal memory allocation

**Performance comparison:**

- RootModel: ~100-1000x slower (model construction dominates)
- Custom function: Near-zero overhead beyond the serialization itself

---

## Common Mistakes to Avoid

### Mistake 1: Assuming RootModel Auto-Serializes Nested Types

```python
# ❌ WRONG: Assumes RootModel handles Path in dict values
data = {"worktree": {"path": Path("/test")}}
model = RootModel[dict[str, Any]](data)
json_str = model.model_dump_json()  # ← Fails: Path not serializable
```

**Why it fails:** `dict[str, Any]` doesn't tell Pydantic that values contain Path objects.

**Correct approach:**

```python
# ✅ CORRECT: Define schema with typed fields
class WorktreeInfo(BaseModel):
    path: Path

class Output(BaseModel):
    worktree: WorktreeInfo

model = Output(worktree=WorktreeInfo(path=Path("/test")))
json_str = model.model_dump_json()  # ← Works: field typing provides serialization hint
```

### Mistake 2: Using model_dump() Then json.dumps()

```python
# ❌ INEFFICIENT: Two-step serialization
model = MyPydanticModel(...)
dict_data = model.model_dump(mode='json')  # ← Pydantic converts to dict
json_str = json.dumps(dict_data, indent=2)  # ← json.dumps formats it
```

**Why inefficient:** Pydantic already has formatted JSON serialization.

**Correct approach:**

```python
# ✅ CORRECT: One-step serialization
model = MyPydanticModel(...)
json_str = model.model_dump_json(indent=2)  # ← Single call, already formatted
```

### Mistake 3: Not Converting Pydantic Model to Dict

```python
# ❌ WRONG: emit_json() only accepts dicts
def my_command():
    model = MyResponseModel(name="test", path=Path("/foo"))
    emit_json(model)  # ← Type error: Expected dict, got BaseModel
```

**Why wrong:** `emit_json()` signature is `dict[str, Any]`, not `BaseModel | dict`.

**Correct approach:**

```python
# ✅ CORRECT: Convert Pydantic model to dict first
def my_command():
    model = MyResponseModel(name="test", path=Path("/foo"))
    emit_json(model.model_dump(mode="json"))  # ← Explicit conversion
```

---

## Design Rationale Summary

### Why json_output.py Uses This Approach

1. **Dict-only interface** - Single, simple contract
   - All callers pass dicts to `emit_json()`
   - No union types or branching logic
   - Explicit conversions at call sites

2. **Pydantic models call .model_dump(mode='json')** - Explicit conversion
   - Validation happens at model construction
   - Serialization happens during .model_dump()
   - emit_json() receives pre-serialized dict

3. **Custom serialization for dict values** - Handles special types
   - Path → str, datetime → ISO format
   - Explicit, performant, testable
   - Follows LBYL (Look Before You Leap) principles

4. **ErrorResponse still uses Pydantic** - Provides validation value
   - Validates exit_code range (0-255)
   - Converts to dict before emit: `emit_json(error.model_dump(mode='json'))`

5. **No RootModel** - Avoids anti-pattern
   - Doesn't solve the serialization problem
   - Adds performance overhead
   - More complex without benefit

### When to Use Pydantic Models

**Use Pydantic models before calling emit_json() when:**

- ✅ Output has a well-defined schema
- ✅ Want runtime validation (e.g., field constraints)
- ✅ Multiple commands share the same structure
- ✅ Need to document JSON schema

**Pattern:**

```python
model = MyResponseModel(...)  # ← Validation happens here
emit_json(model.model_dump(mode='json'))  # ← Serialization happens here
```

**Use plain dicts when:**

- ✅ Output structure is dynamic or simple
- ✅ Don't need validation
- ✅ One-off command output

---

## Code Examples

### Example 1: Pydantic Model with Explicit Conversion

```python
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel
from erk.cli.json_output import emit_json

class WorktreeResponse(BaseModel):
    name: str
    path: Path          # ← Typed field: auto-converts to str
    created: datetime   # ← Typed field: auto-converts to ISO format

# Usage
response = WorktreeResponse(
    name="feature",
    path=Path("/repo/worktrees/feature"),
    created=datetime.now(),
)

# Convert to dict then emit
emit_json(response.model_dump(mode="json"))
# Output: {
#   "name": "feature",
#   "path": "/repo/worktrees/feature",
#   "created": "2025-11-17T10:30:45.123456Z"
# }
```

### Example 2: Dict with Custom Serialization

```python
from pathlib import Path
from datetime import datetime

def _serialize_for_json(obj: Any) -> Any:
    """Recursively serialize special types."""
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_for_json(item) for item in obj]
    return obj

# Usage
data = {
    "name": "feature",
    "path": Path("/repo/worktrees/feature"),
    "created": datetime.now(),
}

serialized = _serialize_for_json(data)
json_str = json.dumps(serialized, indent=2)
# Output: {
#   "name": "feature",
#   "path": "/repo/worktrees/feature",
#   "created": "2025-11-17T10:30:45.123456"
# }
```

### Example 3: ErrorResponse with Validation

```python
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    error: str
    error_type: str
    exit_code: int = Field(default=1, ge=0, le=255)  # ← Validates range

# Valid
error = ErrorResponse(error="File not found", error_type="FileNotFoundError", exit_code=1)

# Invalid - raises ValidationError
error = ErrorResponse(error="Bad", error_type="Error", exit_code=999)  # ← Fails: > 255
```

---

## Related Files

**Implementation:**

- `src/erk/cli/json_output.py` - Core JSON output utilities
- `src/erk/cli/json_schemas.py` - Pydantic schemas for command responses
- `src/erk/cli/rendering.py` - Output rendering framework

**Tests:**

- `tests/cli/test_json_output.py` - Tests for emit_json() and serialization
- `tests/cli/test_rendering.py` - Tests for renderer framework

---

## Further Reading

**Pydantic documentation:**

- [Serialization](https://docs.pydantic.dev/latest/concepts/serialization/) - Model dump, JSON mode
- [Custom Serializers](https://docs.pydantic.dev/latest/concepts/serialization/#custom-serializers) - Field and model serializers
- [JSON Schema](https://docs.pydantic.dev/latest/concepts/json_schema/) - Generating schemas

**Erk coding standards:**

- `AGENTS.md` - Top 6 critical rules
- `dignified-python` skill - Complete Python standards
