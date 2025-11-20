# Dependency Injection - ABC Over Protocol

## Core Rule

**Use ABC for interfaces, NEVER Protocol**

## ABC Interface Pattern

```python
# ✅ CORRECT: Use ABC for interfaces
from abc import ABC, abstractmethod

class Repository(ABC):
    @abstractmethod
    def save(self, entity: Entity) -> None:
        """Save entity to storage."""
        ...

    @abstractmethod
    def load(self, id: str) -> Entity:
        """Load entity by ID."""
        ...

class PostgresRepository(Repository):
    def save(self, entity: Entity) -> None:
        # Implementation
        pass

    def load(self, id: str) -> Entity:
        # Implementation
        pass

# ❌ WRONG: Using Protocol
from typing import Protocol

class Repository(Protocol):
    def save(self, entity: Entity) -> None: ...
    def load(self, id: str) -> Entity: ...
```

## Benefits of ABC

1. **Explicit inheritance** - Clear class hierarchy
2. **Runtime validation** - Errors if abstract methods not implemented
3. **Better IDE support** - Autocomplete and refactoring work better
4. **Documentation** - Clear contract definition

## Complete DI Example

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Define the interface
class DataStore(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None:
        """Retrieve value by key."""
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Store value with key."""
        ...

# Implementation
class RedisStore(DataStore):
    def get(self, key: str) -> str | None:
        return self.client.get(key)

    def set(self, key: str, value: str) -> None:
        self.client.set(key, value)

# Business logic accepts interface
@dataclass
class Service:
    store: DataStore  # Depends on abstraction

    def process(self, item: str) -> None:
        cached = self.store.get(item)
        if cached is None:
            result = expensive_computation(item)
            self.store.set(item, result)
```

## Testing with Fakes

```python
class FakeStore(DataStore):
    """In-memory fake for testing."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value

# Test uses fake
def test_service() -> None:
    fake_store = FakeStore()
    service = Service(store=fake_store)
    service.process("test")
    assert "test" in fake_store.data
```

## Key Takeaways

1. **Always ABC**: Use `abc.ABC` for all interfaces
2. **Never Protocol**: Avoid `typing.Protocol` entirely
3. **Abstract methods**: Mark interface methods with `@abstractmethod`
4. **Runtime safety**: ABC validates implementations at instantiation
5. **Test with fakes**: Create fake implementations for testing
