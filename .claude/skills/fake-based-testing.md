---
name: fake-based-testing
version: 1.0.0
min_tokens: 50
max_tokens: 1500
optimized_for: agents
auto_trigger_patterns:
  - "test_*.py"
  - "*_test.py"
  - "tests/**/*.py"
---

# Fake-Based Testing Skill

Ultra-concise guide for writing tests using fake-based testing patterns with operations layer isolation.

## ⚡ Testing Checklist

WHEN: Adding new external dependency
DO:

1. Create Ops interface (ABC)
2. Add to RealOps → mock test
3. Add to FakeOps → fake test
4. Use FakeOps in business logic tests

WHEN: Testing business logic
DO: Use FakeOps, assert on mutations

WHEN: Function calls external API
DO: Create Ops interface, implement Fake with mutations

WHEN: Testing subprocess commands
DO: Mock subprocess.run, verify args with mock.assert_called

WHEN: Testing error conditions
DO: Configure FakeOps to raise, verify handling

WHEN: Testing stateful operations
DO: Use Fake's mutation tracking for assertions

WHEN: Need test isolation
DO: Fresh Fake instance per test

WHEN: Complex test setup
DO: Use fixtures for Fake configuration

WHEN: Testing async operations
DO: Create AsyncOps interface, use async fakes

WHEN: Verifying side effects
DO: Check Fake's mutation tracking properties

NOTE: For CLI testing patterns, see fake-based-testing-cli skill

## Quick Patterns

### Operations Layer Pattern

WHEN: External dependency needs testing
DO: Create Ops ABC, Real implementation, Fake implementation
VERIFY: Real with mocks, Fake with direct tests, business logic with Fake

<details><summary>Implementation Pattern</summary>

```python
from abc import ABC, abstractmethod

class EmailOps(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> str: ...

    @abstractmethod
    def fetch_inbox(self, limit: int) -> list[dict]: ...

class RealEmailOps(EmailOps):
    def __init__(self, smtp_client, imap_client):
        self._smtp = smtp_client
        self._imap = imap_client

    def send(self, to: str, subject: str, body: str) -> str:
        msg_id = self._smtp.send_message(to, subject, body)
        return msg_id

    def fetch_inbox(self, limit: int) -> list[dict]:
        return self._imap.fetch_recent(limit)

class FakeEmailOps(EmailOps):
    def __init__(self):
        self._sent_emails: list[dict] = []
        self._inbox: list[dict] = []

    def send(self, to: str, subject: str, body: str) -> str:
        msg_id = f"msg-{len(self._sent_emails) + 1}"
        self._sent_emails.append({
            "id": msg_id,
            "to": to,
            "subject": subject,
            "body": body
        })
        return msg_id

    def fetch_inbox(self, limit: int) -> list[dict]:
        return self._inbox[:limit]

    @property
    def sent_emails(self) -> list[dict]:
        return self._sent_emails.copy()
```

</details>

### Testing External Services

WHEN: Function calls external API
DO: Create Ops interface, implement Fake with mutations
VERIFY: Check fake's mutation tracking

<details><summary>Implementation Pattern</summary>

```python
class APIClientOps(ABC):
    @abstractmethod
    def fetch(self, url: str) -> dict: ...

class FakeAPIClientOps(APIClientOps):
    def __init__(self, responses: dict[str, dict] | None = None):
        self._responses = responses or {}
        self._fetched_urls: list[str] = []

    def fetch(self, url: str) -> dict:
        self._fetched_urls.append(url)
        if url not in self._responses:
            raise ValueError(f"No response configured for {url}")
        return self._responses[url]

    @property
    def fetched_urls(self) -> list[str]:
        return self._fetched_urls.copy()
```

</details>

<details><summary>Usage Example</summary>

```python
def test_fetch_user_data():
    api_ops = FakeAPIClientOps({
        "/api/user/123": {"id": 123, "name": "Alice"}
    })
    service = UserService(api_ops)

    user = service.get_user(123)

    assert user.name == "Alice"
    assert api_ops.fetched_urls == ["/api/user/123"]
```

</details>

### Mock Testing for Real Implementations

WHEN: Testing RealOps implementations
DO: Mock external calls, verify correct usage
VERIFY: Mock called with expected arguments

<details><summary>Implementation Pattern</summary>

```python
from unittest.mock import patch, MagicMock

def test_real_api_ops():
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response

        ops = RealAPIClientOps()
        result = ops.fetch("https://api.example.com/data")

        assert result == {"status": "ok"}
        mock_get.assert_called_once_with("https://api.example.com/data")
```

</details>

## Operations Layer Quick Reference

Components:

- Interface: `XxxOps(ABC)` - defines contract
- Real: `RealXxxOps(XxxOps)` - production I/O
- Fake: `FakeXxxOps(XxxOps)` - test double
- Mock test: Verify Real's I/O commands
- Fake test: Verify Fake's behavior

<details><summary>Full Pattern Example</summary>

```python
# 1. Define interface
from abc import ABC, abstractmethod

class DatabaseOps(ABC):
    @abstractmethod
    def execute(self, query: str) -> list[dict]: ...

    @abstractmethod
    def insert(self, table: str, data: dict) -> int: ...

# 2. Real implementation
class RealDatabaseOps(DatabaseOps):
    def __init__(self, connection):
        self._conn = connection

    def execute(self, query: str) -> list[dict]:
        cursor = self._conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    def insert(self, table: str, data: dict) -> int:
        # Real database insertion logic
        pass

# 3. Fake implementation
class FakeDatabaseOps(DatabaseOps):
    def __init__(self):
        self._data: dict[str, list[dict]] = {}
        self._queries: list[str] = []
        self._next_id = 1

    def execute(self, query: str) -> list[dict]:
        self._queries.append(query)
        # Parse query and return fake data
        return []

    def insert(self, table: str, data: dict) -> int:
        if table not in self._data:
            self._data[table] = []

        record = {**data, "id": self._next_id}
        self._data[table].append(record)
        self._next_id += 1
        return record["id"]

    @property
    def executed_queries(self) -> list[str]:
        return self._queries.copy()

# 4. Test Real with mocks
def test_real_database_ops():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [{"id": 1}]

    ops = RealDatabaseOps(mock_conn)
    result = ops.execute("SELECT * FROM users")

    assert result == [{"id": 1}]
    mock_cursor.execute.assert_called_once_with("SELECT * FROM users")

# 5. Test business logic with Fake
def test_user_service():
    db_ops = FakeDatabaseOps()
    service = UserService(db_ops)

    user_id = service.create_user("Alice", "alice@example.com")

    assert user_id == 1
    assert db_ops._data["users"] == [
        {"id": 1, "name": "Alice", "email": "alice@example.com"}
    ]
```

</details>

## Fake vs Mock Decision Matrix

| Situation                | Use Fake | Use Mock |
| ------------------------ | -------- | -------- |
| Business logic test      | ✓        |          |
| Verify subprocess args   |          | ✓        |
| Verify API call format   |          | ✓        |
| Test state changes       | ✓        |          |
| Test error handling      | ✓        |          |
| Integration test         | ✓        |          |
| Unit test                | ✓        |          |
| Test Real implementation |          | ✓        |
| Test async behavior      | ✓        |          |
| Test complex workflows   | ✓        |          |
| Verify exact call count  |          | ✓        |

<details><summary>Detailed Guidance</summary>

**Use Fakes when:**

- Testing business logic that depends on external services
- You need to track state changes over multiple operations
- Testing error handling and edge cases
- Building integration tests that need consistent behavior
- You want fast, deterministic tests

**Use Mocks when:**

- Testing that Real implementations call the right external APIs
- Verifying exact arguments passed to system calls
- Testing interaction patterns (call order, frequency)
- You need to simulate specific failure modes
- Testing timeout and retry logic

**Key principle:** Fakes for behavior testing, Mocks for interaction testing

</details>

## ❌ Anti-Patterns

AVOID: mock.patch for fakes
DO: Constructor injection

AVOID: Hardcoded test data scattered in tests
DO: Use fixtures to configure fake responses

AVOID: Shared fake instances
DO: Fresh instance per test

AVOID: Fakes with real I/O
DO: Pure in-memory operations

AVOID: Complex mock setups
DO: Simple fake with state

AVOID: Testing implementation details
DO: Test observable behavior

AVOID: Mocking everything
DO: Fake only I/O boundaries

AVOID: Stateful test dependencies
DO: Independent test cases

<details><summary>Why These Matter</summary>

**mock.patch problems:**

- Creates tight coupling to implementation
- Makes refactoring difficult
- Can mask real issues

**Hardcoded test data problems:**

- Duplicated setup across tests
- Difficult to maintain
- Obscures test intent

**Shared instance problems:**

- Test pollution between cases
- Hidden dependencies
- Non-deterministic failures

**Real I/O in fakes problems:**

- Slow tests
- Flaky tests
- Environment dependencies

</details>

## Examples

<details><summary>Simple Fake Test</summary>

```python
def test_create_user_via_api():
    api_ops = FakeAPIClientOps({})
    service = UserService(api_ops)

    user_id = service.create_user("alice", "alice@example.com")

    assert user_id is not None
    assert len(api_ops.post_requests) == 1
    assert api_ops.post_requests[0]["url"] == "/api/users"
    assert api_ops.post_requests[0]["data"]["name"] == "alice"
```

</details>

<details><summary>Mock Subprocess Test</summary>

```python
from unittest.mock import patch, MagicMock

def test_git_operations():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="main\n",
            stderr=""
        )

        git_ops = RealGitOps()
        branch = git_ops.current_branch()

        assert branch == "main"
        mock_run.assert_called_once_with(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=True
        )
```

</details>

<details><summary>Error Handling Test</summary>

```python
def test_handles_api_error():
    api_ops = FakeAPIClientOps()
    # Don't configure response to trigger error

    service = DataService(api_ops)

    result = service.fetch_data("unknown_endpoint")

    assert result is None  # Service handles error gracefully
    assert api_ops.fetched_urls == ["unknown_endpoint"]
```

</details>

<details><summary>Stateful Operations Test</summary>

```python
def test_cache_behavior():
    cache_ops = FakeCacheOps()
    service = CachedService(cache_ops)

    # First call - cache miss
    result1 = service.get_data("key1")
    assert cache_ops.cache_hits == 0
    assert cache_ops.cache_misses == 1

    # Second call - cache hit
    result2 = service.get_data("key1")
    assert cache_ops.cache_hits == 1
    assert cache_ops.cache_misses == 1
    assert result1 == result2
```

</details>

<details><summary>Fixture-based Test Setup</summary>

```python
import pytest

@pytest.fixture
def fake_api():
    return FakeAPIClientOps({
        "/users": [{"id": 1, "name": "Alice"}],
        "/posts": [{"id": 1, "title": "Hello"}]
    })

@pytest.fixture
def fake_db():
    db = FakeDatabaseOps()
    db._data["users"] = [
        {"id": 1, "name": "Alice", "active": True}
    ]
    return db

def test_sync_users(fake_api, fake_db):
    service = SyncService(fake_api, fake_db)

    service.sync_users()

    assert fake_api.fetched_urls == ["/users"]
    assert len(fake_db._data["users"]) == 1
    assert fake_db.executed_queries == ["SELECT * FROM users"]
```

</details>

## 🤖 Agent Optimization Tips

- Start with checklist, expand only if needed
- Use pattern matching on WHEN/DO markers
- Skip collapsed sections unless specific pattern needed
- Cache fake instances in test context
- Mutation tracking > mock.assert_called
- Use fixtures for complex setups
- Keep fakes simple - just track mutations
- Test one behavior per test case

<details><summary>Token Usage Guide</summary>

- Checklist only: ~50 tokens
- - Quick patterns: ~200 tokens
- - One detailed pattern: ~300 tokens
- Full expansion: ~1500 tokens

**Optimization strategies:**

1. Read checklist first
2. Pattern match on WHEN conditions
3. Expand only matching patterns
4. Skip examples unless debugging
5. Cache expanded patterns in context

</details>

## Pattern Recognition Markers

**Consistent markers used throughout:**

- `WHEN:` - Situation or condition
- `DO:` - Action to take
- `VERIFY:` - What to assert/check
- `NOTE:` - Important caveat or detail
- `AVOID:` - Anti-pattern to avoid
- `PREFER:` - Better alternative

**Use these for quick pattern matching without full parsing.**
