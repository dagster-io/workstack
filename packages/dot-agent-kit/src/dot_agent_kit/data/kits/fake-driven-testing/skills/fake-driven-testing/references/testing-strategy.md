# Testing Strategy by Layer

**Read this when**: You need to decide where to add a test, or understand the four-layer testing approach.

## Overview

This skill uses a **defense-in-depth testing strategy** with four layers for Python applications:

```
┌─────────────────────────────────────────┐
│  Layer 4: E2E Integration Tests (5%)   │  ← Smoke tests over real system
├─────────────────────────────────────────┤
│  Layer 3: Business Logic Tests (80%)   │  ← Tests over fakes (fast!)
├─────────────────────────────────────────┤
│  Layer 2: Integration class Implementation Tests (15%)│  ← Tests WITH mocking
├─────────────────────────────────────────┤
│  Layer 1: Fake Infrastructure Tests    │  ← Verify test doubles work
└─────────────────────────────────────────┘
```

**Philosophy**: Test business logic extensively over fast in-memory fakes. Use real implementations sparingly for integration validation.

**Test distribution guidance**: Aim for 80% Layer 3, 15% Layer 2, 5% Layer 4. Layer 1 tests grow as needed when adding/changing fakes.

## Layer 1: Unit Tests of Fakes

**Purpose**: Verify test infrastructure is reliable.

**Location**: `tests/unit/fakes/test_fake_*.py`

**When to write**: When adding or changing fake implementations.

**Why**: If fakes are broken, all higher-layer tests become unreliable. These tests validate that your test doubles behave correctly.

### Pattern: Test the Fake Itself

```python
def test_fake_database_tracks_queries(tmp_path: Path) -> None:
    """Verify FakeDatabaseAdapter tracks database operations."""
    # Arrange
    fake_db = FakeDatabaseAdapter()

    # Act
    fake_db.execute("INSERT INTO users (name) VALUES ('Alice')")
    result = fake_db.query("SELECT * FROM users WHERE name = 'Alice'")

    # Assert fake tracked the operations
    assert len(fake_db.executed_queries) == 2
    assert fake_db.executed_queries[0].startswith("INSERT")
    assert fake_db.executed_queries[1].startswith("SELECT")

    # Assert fake returns expected data
    assert len(result) == 1
    assert result[0]["name"] == "Alice"
```

### What to Test

- **State mutations**: Verify operations update internal state correctly
- **Mutation tracking**: Verify read-only properties track operations
- **Error simulation**: Verify fakes can inject errors when configured
- **State queries**: Verify read operations return expected data

### Example Tests

- `tests/unit/fakes/test_fake_database.py` - Tests of FakeDatabaseAdapter
- `tests/unit/fakes/test_fake_api_client.py` - Tests of FakeApiClient
- `tests/unit/fakes/test_fake_cache.py` - Tests of FakeCache
- `tests/unit/fakes/test_fake_message_queue.py` - Tests of FakeMessageQueue

## Layer 2: Integration Tests of Real Integration classes (with Mocking)

**Purpose**: Get code coverage of real implementations without slow I/O.

**Location**: `tests/integration/test_real_*.py`

**When to write**: When adding or changing real implementations.

**Why**: Ensures code coverage even when underlying systems (database, network, filesystem) are mocked.

### Pattern: Mock External Systems, Verify Calls

```python
def test_real_database_executes_correct_query(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify RealDatabaseAdapter calls correct SQL."""
    # Mock the database connection
    mock_connection = Mock()
    mock_cursor = Mock()
    mock_connection.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [{"id": 1, "name": "Alice"}]

    def mock_connect(**kwargs):
        return mock_connection

    monkeypatch.setattr("psycopg2.connect", mock_connect)

    # Act
    db = RealDatabaseAdapter(connection_string="postgresql://...")
    result = db.query("SELECT * FROM users")

    # Assert correct command was constructed
    mock_cursor.execute.assert_called_once_with("SELECT * FROM users")
    assert result == [{"id": 1, "name": "Alice"}]
```

### What to Test

- **Command construction**: Verify correct SQL/API calls are built
- **Error handling**: Verify exceptions from external systems are handled correctly
- **Parsing logic**: Verify response parsing works correctly (can use mock responses)
- **Edge cases**: Verify handling of unusual inputs or error conditions

### Tools

- `monkeypatch` fixture for mocking database connections, HTTP clients, etc.
- Mock return values to simulate various responses
- Test error paths by raising exceptions from mocks

### Example Tests

- `tests/integration/test_real_database.py` - Tests of RealDatabaseAdapter with mocking
- `tests/integration/test_real_api_client.py` - Tests of RealApiClient with mocked HTTP

## Layer 3: Business Logic Tests over Fakes (MAJORITY)

**Purpose**: Test application logic extensively with fast in-memory fakes.

**Location**: `tests/unit/services/`, `tests/unit/`, `tests/commands/`

**When to write**: For EVERY feature and bug fix. This is the default testing layer.

**Why**: Fast, reliable, easy to debug. Tests run in milliseconds, not seconds. This is where most testing happens.

### Pattern: Configure Fakes, Execute Logic, Assert Behavior

```python
def test_user_service_creates_user() -> None:
    """Verify user service creates users correctly."""
    # Arrange: Configure fake with desired state
    fake_db = FakeDatabaseAdapter()
    fake_email = FakeEmailClient(
        should_fail_for=["invalid@example.com"]
    )

    service = UserService(database=fake_db, email_client=fake_email)

    # Act: Execute business logic
    user = service.create_user(
        name="Alice",
        email="alice@example.com"
    )

    # Assert: Check behavior
    assert user.id == 1
    assert user.name == "Alice"
    assert user.email == "alice@example.com"

    # Assert: Check side effects via fake's tracking
    assert len(fake_db.executed_queries) == 1
    assert "INSERT INTO users" in fake_db.executed_queries[0]
    assert len(fake_email.sent_emails) == 1
    assert fake_email.sent_emails[0]["to"] == "alice@example.com"
```

### Key Tools

- **Fake implementations**: `FakeDatabaseAdapter`, `FakeApiClient`, `FakeCache`, etc.
- **Builder patterns**: Create complex test data easily
- **pytest fixtures**: Share common test setup
- **`tmp_path`**: pytest fixture for real directories when needed
- **CliRunner**: For testing Click CLI commands

### What to Test

- **Feature behavior**: Does the feature work as expected?
- **Error handling**: How does code handle error conditions?
- **Edge cases**: Unusual inputs, empty states, boundary conditions
- **Business rules**: Validation, calculations, state transitions
- **Side effects**: Did operations modify state correctly? (Check fake's tracking properties)

### Performance

Tests over fakes run in **milliseconds**. A typical test suite of 100+ tests runs in seconds, enabling rapid iteration.

### Example Tests

- `tests/unit/services/test_user_service.py` - Service layer tests
- `tests/unit/services/test_order_service.py` - Business logic tests
- `tests/unit/models/test_pricing.py` - Domain model tests
- `tests/commands/test_cli.py` - CLI command tests with CliRunner

## Layer 4: End-to-End Integration Tests

**Purpose**: Smoke tests over real system to catch integration issues.

**Location**: `tests/e2e/`

**When to write**: Sparingly, for critical user-facing workflows.

**Why**: Catches issues that mocks miss (actual database behavior, filesystem edge cases, network issues), but slow and potentially brittle.

### Pattern: Real Systems, Actual External Calls

```python
def test_user_registration_e2e(test_database_url: str) -> None:
    """End-to-end test: user registration with real database."""
    # Setup: Use real database (possibly dockerized for tests)
    db = RealDatabaseAdapter(connection_string=test_database_url)

    # Clean slate
    db.execute("DELETE FROM users")

    service = UserService(
        database=db,
        email_client=RealEmailClient(api_key="test_key")
    )

    # Act: Execute real operation
    user = service.register_user(
        name="Alice",
        email="alice@example.com",
        password="secure123"
    )

    # Assert: Verify in real database
    users = db.query("SELECT * FROM users WHERE email = 'alice@example.com'")
    assert len(users) == 1
    assert users[0]["name"] == "Alice"

    # Verify email was actually sent (might check test email service)
    # This depends on your test infrastructure
```

### What to Test

- **Critical workflows**: Core user-facing features (signup, checkout, payment)
- **Integration points**: Where multiple systems interact
- **Real system quirks**: Behavior that's hard to mock accurately
- **Data persistence**: Verify data is actually saved and retrievable

### Characteristics

- **Slow**: Tests take seconds, not milliseconds
- **Brittle**: Can fail due to environment issues (database down, network problems)
- **High value**: Catches real integration bugs that unit tests miss

### When NOT to Use E2E

- ❌ Testing business logic (use Layer 3 instead)
- ❌ Testing error handling (use Layer 3 with fakes configured for errors)
- ❌ Testing calculations or validation (use Layer 3)
- ❌ Rapid iteration during development (use Layer 3)

Use E2E tests as **final validation**, not primary testing strategy.

## Decision Tree: Where Should My Test Go?

```
┌─ I need to test...
│
├─ A NEW FEATURE or BUG FIX
│  └─> Layer 3: tests/unit/services/ or tests/unit/ (over fakes) ← START HERE
│
├─ A FAKE IMPLEMENTATION (test infrastructure)
│  └─> Layer 1: tests/unit/fakes/test_fake_*.py
│
├─ A REAL ADAPTER IMPLEMENTATION (code coverage with mocks)
│  └─> Layer 2: tests/integration/test_real_*.py
│
└─ CRITICAL USER WORKFLOW (smoke test)
   └─> Layer 4: tests/e2e/ (end-to-end, sparingly)
```

**Default**: When in doubt, write tests over fakes (Layer 3).

## Test Distribution Example

For a typical feature (e.g., "add payment processing"):

- **1-2 fake tests** (Layer 1): Verify `FakePaymentGateway.charge()` works
- **1-2 real tests** (Layer 2): Verify `RealPaymentGateway.charge()` calls correct API
- **10-15 business logic tests** (Layer 3): Test payment flow over fakes
  - Successful payment
  - Insufficient funds
  - Invalid card
  - Network timeout
  - Duplicate transaction
  - Refund processing
  - Currency conversion
  - Tax calculation
  - Receipt generation
- **1 E2E test** (Layer 4): Smoke test entire payment flow with test payment gateway

**Total**: ~20 tests, with 80% over fakes.

## Related Documentation

- `integration-architecture.md` - Understanding the integration layer being tested
- `workflows.md` - Step-by-step guides for adding tests
- `patterns.md` - Common testing patterns (CliRunner, builders, etc.)
- `anti-patterns.md` - What to avoid when writing tests
- `python-specific.md` - pytest fixtures, mocking, and Python tools
