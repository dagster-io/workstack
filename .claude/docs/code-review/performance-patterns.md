# Performance Expectations - Properties and Magic Methods

## Core Principle

Python's `@property` decorator and dunder methods like `__len__` create strong expectations about performance. Engineers reasonably assume these are cheap operations (modest assembly instructions, maybe a cached value lookup). Using them for expensive operations violates this expectation and causes performance issues.

## Property Access

### DON'T Hide Expensive Operations

```python
# ❌ WRONG - Property doing I/O
class DataSet:
    @property
    def size(self) -> int:
        # Fetches from database!
        return self._fetch_count_from_db()

# ❌ WRONG - Property doing expensive computation
class PartitionSubset:
    @property
    def size(self) -> int:
        # Materializes ALL partition keys!
        return len(list(self._generate_all_partitions()))
```

### DO Make Cost Explicit or Cache Results

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
```

## Magic Methods (`__len__`, `__bool__`, etc.)

### DON'T Make Magic Methods Expensive

```python
# ❌ WRONG - __len__ doing expensive computation
class PartitionSubset:
    def __len__(self) -> int:
        # Materializes ALL partition keys!
        return len(list(self._generate_all_partitions()))

# ❌ WRONG - __bool__ doing I/O
class RemoteResource:
    def __bool__(self) -> bool:
        # Network call!
        return self._check_exists_on_server()
```

### DO Precompute or Use Explicit Methods

```python
# ✅ CORRECT - Precomputed
class EfficientSubset:
    def __init__(self, partitions: Sequence[str]):
        self._partitions = partitions
        self._count = len(partitions)  # Precompute

    def __len__(self) -> int:
        return self._count  # O(1)

# ✅ CORRECT - Explicit method for expensive operation
class RemoteResource:
    def exists_on_server(self) -> bool:
        """Check if resource exists (network call)."""
        return self._check_exists_on_server()
```

## Guidelines

1. **Properties should be O(1)** - Simple attribute access or cached value
2. **Use `@cached_property` for moderately expensive operations** - Only on immutable classes
3. **Use explicit methods for expensive operations** - Name should indicate cost
4. **Document performance characteristics** - If not obvious
5. **Never do I/O in properties or magic methods** - No file reads, network calls, or database queries

## Real Production Bug

**Customer on Discord**: `AssetSubset.size` property triggered 10,000+ partition key materializations via expensive cron parsing. What looked like a simple property access was actually:

- Parsing cron strings
- Generating all time-based partitions
- Materializing thousands of partition keys
- All from what appeared to be a cheap property access

**Rationale**: Engineers won't think twice about accessing properties in loops or using them multiple times. They assume it's cheap because the syntax makes it look cheap.

## Key Takeaways

1. **Properties = O(1)**: If it's not constant time, it's not a property
2. **Magic methods = O(1)**: Same rule applies to `__len__`, `__bool__`, etc.
3. **Make cost visible**: Expensive operations should have explicit method names
4. **Cache when appropriate**: Use `@cached_property` for immutable objects
5. **Document exceptions**: If a property must be expensive, document it prominently
