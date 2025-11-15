# Fake Implementation Patterns

## API Clients

### REST API Client

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

class APIClientOps(ABC):
    @abstractmethod
    def get(self, endpoint: str) -> dict[str, Any]: ...

    @abstractmethod
    def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def delete(self, endpoint: str) -> None: ...

@dataclass
class FakeAPIClientOps(APIClientOps):
    """Configurable fake API client for testing."""

    # Configuration
    _get_responses: dict[str, dict] = field(default_factory=dict)
    _post_responses: dict[str, dict] = field(default_factory=dict)
    _raise_on: set[str] = field(default_factory=set)

    # Mutation tracking
    _get_calls: list[str] = field(default_factory=list, init=False)
    _post_calls: list[tuple[str, dict]] = field(default_factory=list, init=False)
    _delete_calls: list[str] = field(default_factory=list, init=False)

    def get(self, endpoint: str) -> dict[str, Any]:
        self._get_calls.append(endpoint)

        if endpoint in self._raise_on:
            raise ConnectionError(f"Simulated failure for {endpoint}")

        if endpoint not in self._get_responses:
            raise ValueError(f"No response configured for GET {endpoint}")

        return self._get_responses[endpoint].copy()

    def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        self._post_calls.append((endpoint, data.copy()))

        if endpoint in self._raise_on:
            raise ConnectionError(f"Simulated failure for {endpoint}")

        if endpoint in self._post_responses:
            return self._post_responses[endpoint].copy()

        # Default: echo back data with ID
        return {"id": len(self._post_calls), **data}

    def delete(self, endpoint: str) -> None:
        self._delete_calls.append(endpoint)

        if endpoint in self._raise_on:
            raise ConnectionError(f"Simulated failure for {endpoint}")

    # Test assertions
    @property
    def get_calls(self) -> list[str]:
        return self._get_calls.copy()

    @property
    def post_calls(self) -> list[tuple[str, dict]]:
        return self._post_calls.copy()
```

### GraphQL Client

```python
@dataclass
class FakeGraphQLOps:
    _responses: dict[str, Any] = field(default_factory=dict)
    _queries: list[tuple[str, dict]] = field(default_factory=list, init=False)

    def query(self, query: str, variables: dict | None = None) -> dict:
        self._queries.append((query, variables or {}))

        # Simple query key extraction (real implementation would parse)
        query_key = query.split("{")[1].split("(")[0].strip()

        if query_key in self._responses:
            return {"data": self._responses[query_key]}

        return {"data": None, "errors": [{"message": "Not found"}]}
```

## Database Operations

### SQL Database

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

class DatabaseOps(ABC):
    @abstractmethod
    def execute(self, query: str, params: tuple = ()) -> list[dict]: ...

    @abstractmethod
    def insert(self, table: str, data: dict) -> int: ...

    @abstractmethod
    def update(self, table: str, id: int, data: dict) -> None: ...

@dataclass
class FakeDatabaseOps(DatabaseOps):
    """In-memory database simulation."""

    # Data storage
    _tables: dict[str, list[dict]] = field(default_factory=dict)
    _next_id: int = field(default=1, init=False)

    # Mutation tracking
    _queries: list[tuple[str, tuple]] = field(default_factory=list, init=False)

    def execute(self, query: str, params: tuple = ()) -> list[dict]:
        self._queries.append((query, params))

        # Simple SELECT simulation
        if query.upper().startswith("SELECT"):
            table = self._extract_table(query)
            if table in self._tables:
                return self._tables[table].copy()

        return []

    def insert(self, table: str, data: dict) -> int:
        if table not in self._tables:
            self._tables[table] = []

        record = {"id": self._next_id, **data}
        self._tables[table].append(record)
        self._next_id += 1
        return record["id"]

    def update(self, table: str, id: int, data: dict) -> None:
        if table not in self._tables:
            return

        for record in self._tables[table]:
            if record.get("id") == id:
                record.update(data)
                break

    def _extract_table(self, query: str) -> str:
        """Simple table extraction from SQL."""
        parts = query.upper().split("FROM")
        if len(parts) > 1:
            return parts[1].strip().split()[0].lower()
        return ""

    # Test helpers
    def seed_table(self, table: str, records: list[dict]) -> None:
        """Pre-populate table for testing."""
        self._tables[table] = records.copy()

    @property
    def queries(self) -> list[tuple[str, tuple]]:
        return self._queries.copy()
```

### NoSQL Database

```python
@dataclass
class FakeMongoOps:
    _collections: dict[str, list[dict]] = field(default_factory=dict)
    _next_id: int = field(default=1, init=False)

    def find(self, collection: str, filter: dict) -> list[dict]:
        if collection not in self._collections:
            return []

        # Simple filter matching
        results = []
        for doc in self._collections[collection]:
            if self._matches(doc, filter):
                results.append(doc.copy())
        return results

    def insert_one(self, collection: str, document: dict) -> str:
        if collection not in self._collections:
            self._collections[collection] = []

        doc = {"_id": f"id-{self._next_id}", **document}
        self._collections[collection].append(doc)
        self._next_id += 1
        return doc["_id"]

    def _matches(self, doc: dict, filter: dict) -> bool:
        """Simple filter matching."""
        for key, value in filter.items():
            if doc.get(key) != value:
                return False
        return True
```

## Async Operations

### Async API Client

```python
import asyncio
from typing import Any

class AsyncAPIClientOps(ABC):
    @abstractmethod
    async def fetch(self, url: str) -> dict: ...

    @abstractmethod
    async def batch_fetch(self, urls: list[str]) -> list[dict]: ...

@dataclass
class FakeAsyncAPIClientOps(AsyncAPIClientOps):
    _responses: dict[str, dict] = field(default_factory=dict)
    _delays: dict[str, float] = field(default_factory=dict)
    _fetch_calls: list[str] = field(default_factory=list, init=False)

    async def fetch(self, url: str) -> dict:
        self._fetch_calls.append(url)

        # Simulate network delay
        if url in self._delays:
            await asyncio.sleep(self._delays[url])

        if url not in self._responses:
            raise ValueError(f"No response for {url}")

        return self._responses[url].copy()

    async def batch_fetch(self, urls: list[str]) -> list[dict]:
        tasks = [self.fetch(url) for url in urls]
        return await asyncio.gather(*tasks)

    # Test configuration
    def set_delay(self, url: str, delay: float) -> None:
        """Configure simulated network delay."""
        self._delays[url] = delay
```

## Message Queue Operations

### Pub/Sub Pattern

```python
from collections import defaultdict

@dataclass
class FakeMessageQueueOps:
    _messages: dict[str, list[dict]] = field(default_factory=lambda: defaultdict(list))
    _subscribers: dict[str, list] = field(default_factory=lambda: defaultdict(list))
    _published: list[tuple[str, dict]] = field(default_factory=list, init=False)

    def publish(self, topic: str, message: dict) -> None:
        self._published.append((topic, message.copy()))
        self._messages[topic].append(message)

        # Simulate subscriber callbacks
        for callback in self._subscribers[topic]:
            callback(message)

    def subscribe(self, topic: str, callback) -> None:
        self._subscribers[topic].append(callback)

    def get_messages(self, topic: str, limit: int = 10) -> list[dict]:
        return self._messages[topic][-limit:]

    @property
    def all_published(self) -> list[tuple[str, dict]]:
        return self._published.copy()
```

## Cache Operations

### Redis-like Cache

```python
from datetime import datetime, timedelta

@dataclass
class FakeCacheOps:
    _data: dict[str, Any] = field(default_factory=dict)
    _expiry: dict[str, datetime] = field(default_factory=dict)
    _hits: int = field(default=0, init=False)
    _misses: int = field(default=0, init=False)

    def get(self, key: str) -> Any | None:
        # Check expiry
        if key in self._expiry:
            if datetime.now() > self._expiry[key]:
                del self._data[key]
                del self._expiry[key]

        if key in self._data:
            self._hits += 1
            return self._data[key]

        self._misses += 1
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        self._data[key] = value
        if ttl:
            self._expiry[key] = datetime.now() + timedelta(seconds=ttl)

    def delete(self, key: str) -> bool:
        if key in self._data:
            del self._data[key]
            self._expiry.pop(key, None)
            return True
        return False

    @property
    def stats(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0
        }
```

## Testing Patterns

### Configure for Success

```python
def test_user_service_creates_user():
    # Arrange - configure fake for success
    api_ops = FakeAPIClientOps(
        _post_responses={
            "/api/users": {"id": 123, "status": "created"}
        }
    )
    service = UserService(api_ops)

    # Act
    user_id = service.create_user("Alice", "alice@example.com")

    # Assert
    assert user_id == 123
    assert api_ops.post_calls == [
        ("/api/users", {"name": "Alice", "email": "alice@example.com"})
    ]
```

### Configure for Failure

```python
def test_service_handles_api_failure():
    # Arrange - configure fake to fail
    api_ops = FakeAPIClientOps(_raise_on={"/api/users"})
    service = UserService(api_ops)

    # Act
    result = service.create_user("Alice", "alice@example.com")

    # Assert - service handles error gracefully
    assert result is None
    assert len(api_ops.post_calls) == 1  # Still tracked the attempt
```

### Test Retry Logic

```python
def test_service_retries_on_failure():
    # Arrange - fail first, succeed second
    api_ops = FakeAPIClientOps()
    api_ops._post_responses["/api/users"] = {"id": 456}

    # Monkey-patch to fail once then succeed
    call_count = 0
    original_post = api_ops.post

    def post_with_retry(endpoint, data):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Network error")
        return original_post(endpoint, data)

    api_ops.post = post_with_retry

    service = UserService(api_ops, retry_count=2)

    # Act
    user_id = service.create_user("Bob", "bob@example.com")

    # Assert
    assert user_id == 456
    assert call_count == 2  # Failed once, succeeded on retry
```