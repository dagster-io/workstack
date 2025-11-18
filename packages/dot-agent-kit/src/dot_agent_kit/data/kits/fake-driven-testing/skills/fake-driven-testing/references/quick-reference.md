# Quick Reference

**Read this when**: You need a quick lookup for file locations, fixtures, or example tests.

## Decision Tree: Where Should I Add My Test?

```
┌─ I need to test...
│
├─ A NEW FEATURE or BUG FIX
│  └─> tests/unit/ or tests/services/ (over fakes) ← START HERE
│     Example: tests/services/test_user_service.py
│
├─ A FAKE IMPLEMENTATION (test infrastructure)
│  └─> tests/unit/fakes/test_fake_*.py
│     Example: tests/unit/fakes/test_fake_database.py
│
├─ A REAL IMPLEMENTATION (code coverage with mocks)
│  └─> tests/integration/test_real_*.py
│     Example: tests/integration/test_real_database.py
│
└─ CRITICAL USER WORKFLOW (smoke test)
   └─> tests/e2e/ (end-to-end, sparingly)
      Example: tests/e2e/test_user_journey.py
```

**Default**: When in doubt, write tests over fakes (Layer 3).

## File Location Map

### Generic Python Project Structure

```
src/
├── myapp/
│   ├── integration classes/              ← External system wrappers
│   │   ├── __init__.py
│   │   ├── database.py        ← Database integration class (ABC + Real)
│   │   ├── api_client.py      ← API client integration class
│   │   ├── filesystem.py      ← File system integration class
│   │   └── message_queue.py   ← Message queue integration class
│   ├── services/              ← Business logic
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── order_service.py
│   │   └── payment_service.py
│   ├── models/                ← Domain models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── order.py
│   └── cli/                   ← CLI commands (if applicable)
│       ├── __init__.py
│       └── commands.py
```

### Test Code Structure

```
tests/
├── conftest.py                ← Shared pytest fixtures
├── fakes/                     ← Fake implementations (in-memory)
│   ├── __init__.py
│   ├── database.py            ← FakeDatabaseAdapter
│   ├── api_client.py          ← FakeApiClient
│   ├── filesystem.py          ← FakeFileSystem
│   └── message_queue.py       ← FakeMessageQueue
├── unit/
│   ├── fakes/                 ← Tests OF fakes (Layer 1)
│   │   ├── test_fake_database.py
│   │   ├── test_fake_api_client.py
│   │   └── test_fake_filesystem.py
│   ├── services/              ← Business logic tests (Layer 3)
│   │   ├── test_user_service.py
│   │   ├── test_order_service.py
│   │   └── test_payment_service.py
│   └── models/                ← Model tests
│       ├── test_user.py
│       └── test_order.py
├── integration/               ← Tests WITH real integration classes (Layer 2)
│   ├── test_real_database.py ← Layer 2: mocked connections
│   ├── test_real_api_client.py
│   └── test_api_endpoints.py ← API integration tests
├── e2e/                       ← End-to-end tests (Layer 4)
│   ├── test_user_journey.py
│   └── test_order_flow.py
└── helpers/                   ← Test utilities
    ├── __init__.py
    ├── builders.py            ← Test data builders
    └── fixtures.py            ← Additional fixtures
```

## Common Fixtures

### pytest Built-in Fixtures

| Fixture       | Purpose                           | Usage                            |
| ------------- | --------------------------------- | -------------------------------- |
| `tmp_path`    | Temporary directory (Path object) | `def test_foo(tmp_path: Path):`  |
| `monkeypatch` | Mock/patch objects                | `def test_foo(monkeypatch):`     |
| `capsys`      | Capture stdout/stderr             | `out, err = capsys.readouterr()` |
| `caplog`      | Capture log messages              | `assert "ERROR" in caplog.text`  |

### Project-Specific Patterns

| Pattern                    | Purpose                    | Usage                                                 |
| -------------------------- | -------------------------- | ----------------------------------------------------- |
| Dependency injection       | Inject fakes into services | `service = UserService(db=fake_db, api=fake_api)`     |
| Builder pattern            | Build complex test data    | `user = UserBuilder().with_name("Alice").build()`     |
| Fixture composition        | Combine fixtures           | `def service(fake_db, fake_api): return Service(...)` |
| CliRunner (for Click apps) | Test CLI commands          | `runner = CliRunner(); result = runner.invoke(cmd)`   |

### Fake Implementation Examples

| Fake Class            | Purpose                       | Common Methods                              |
| --------------------- | ----------------------------- | ------------------------------------------- |
| `FakeDatabaseAdapter` | In-memory database operations | `query()`, `execute()`, `transaction()`     |
| `FakeApiClient`       | In-memory API responses       | `get()`, `post()`, `put()`, `delete()`      |
| `FakeFileSystem`      | In-memory file operations     | `read()`, `write()`, `exists()`, `delete()` |
| `FakeMessageQueue`    | In-memory message queue       | `publish()`, `subscribe()`, `acknowledge()` |
| `FakeCache`           | In-memory cache               | `get()`, `set()`, `delete()`, `clear()`     |

## Common Test Patterns

### Basic Unit Test Over Fakes

```python
import pytest
from pathlib import Path

def test_user_service_create_user() -> None:
    # Arrange
    fake_db = FakeDatabaseAdapter()
    fake_api = FakeApiClient()
    service = UserService(database=fake_db, api_client=fake_api)

    # Act
    user = service.create_user("Alice", "alice@example.com")

    # Assert
    assert user.id is not None
    assert user.name == "Alice"
    assert user.email == "alice@example.com"

    # Verify operations were called
    assert len(fake_db.executed_queries) == 1
    assert "INSERT INTO users" in fake_db.executed_queries[0]
```

### CLI Test with Click

```python
from click.testing import CliRunner

def test_cli_command(tmp_path: Path) -> None:
    """Test CLI command with CliRunner."""
    # Arrange
    runner = CliRunner()

    # Act
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(init_command, ["my_project"])

    # Assert
    assert result.exit_code == 0
    assert "Project created" in result.output
```

### Test with Builder Pattern

```python
def test_order_processing() -> None:
    """Test with builder pattern for complex data."""
    # Arrange
    user = UserBuilder().with_name("Alice").with_credit(100).build()
    order = OrderBuilder().for_user(user).with_items(3).with_total(50).build()

    service = OrderService(database=FakeDatabaseAdapter())

    # Act
    result = service.process_order(order)

    # Assert
    assert result.status == "completed"
    assert result.user.credit == 50
```

### Test Fake Implementation

```python
def test_fake_database_tracks_queries() -> None:
    """Test that fake tracks operations correctly."""
    # Arrange
    fake_db = FakeDatabaseAdapter()

    # Act
    fake_db.execute("INSERT INTO users VALUES (1, 'Alice')")
    fake_db.query("SELECT * FROM users")

    # Assert
    assert len(fake_db.executed_queries) == 2
    assert fake_db.executed_queries[0].startswith("INSERT")
    assert fake_db.executed_queries[1].startswith("SELECT")
```

### Test Real Implementation with Mocking

```python
def test_real_database_with_mocking(monkeypatch) -> None:
    """Test real integration class with mocked connections."""
    # Arrange: Mock the database connection
    mock_connection = Mock()
    mock_cursor = Mock()
    mock_connection.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [{"id": 1, "name": "Alice"}]

    monkeypatch.setattr("psycopg2.connect", lambda **kwargs: mock_connection)

    # Act
    db = RealDatabaseAdapter(connection_string="...")
    result = db.query("SELECT * FROM users")

    # Assert
    assert len(result) == 1
    assert result[0]["name"] == "Alice"
    mock_cursor.execute.assert_called_once_with("SELECT * FROM users")
```

## Example Tests to Reference

### Layer 1: Fake Infrastructure Tests

**Purpose**: Verify fakes work correctly

| File                                       | What It Tests                              |
| ------------------------------------------ | ------------------------------------------ |
| `tests/unit/fakes/test_fake_database.py`   | FakeDatabase tracks queries correctly      |
| `tests/unit/fakes/test_fake_api_client.py` | FakeApiClient returns configured responses |
| `tests/unit/fakes/test_fake_filesystem.py` | FakeFileSystem simulates file operations   |

### Layer 2: Real Integration classes with Mocking

**Purpose**: Get code coverage of real implementations

| File                                        | What It Tests                          |
| ------------------------------------------- | -------------------------------------- |
| `tests/integration/test_real_database.py`   | RealDatabase executes correct SQL      |
| `tests/integration/test_real_api_client.py` | RealApiClient makes correct HTTP calls |

### Layer 3: Business Logic Over Fakes (MAJORITY)

**Purpose**: Test features and bug fixes

| File                                          | What It Tests                     |
| --------------------------------------------- | --------------------------------- |
| `tests/unit/services/test_user_service.py`    | User creation, updates, deletion  |
| `tests/unit/services/test_order_service.py`   | Order processing logic            |
| `tests/unit/services/test_payment_service.py` | Payment validation and processing |

### Layer 4: End-to-End Integration

**Purpose**: Smoke tests over real system

| File                             | What It Tests             |
| -------------------------------- | ------------------------- |
| `tests/e2e/test_user_journey.py` | Complete user signup flow |
| `tests/e2e/test_order_flow.py`   | Full order processing     |

## Common Imports

```python
# Testing framework
import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from pathlib import Path

# Type hints
from typing import Any
from collections.abc import Generator

# Your fakes
from tests.fakes.database import FakeDatabaseAdapter
from tests.fakes.api_client import FakeApiClient
from tests.fakes.filesystem import FakeFileSystem

# Your services and models
from myapp.services.user_service import UserService
from myapp.services.order_service import OrderService
from myapp.models.user import User
from myapp.models.order import Order

# Test helpers
from tests.helpers.builders import UserBuilder, OrderBuilder
```

## Useful Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/services/test_user_service.py

# Run specific test
pytest tests/unit/services/test_user_service.py::test_create_user

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src/myapp

# Coverage with missing lines
pytest --cov=src/myapp --cov-report=term-missing

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Type check (if using mypy or pyright)
mypy src/
pyright

# Format code
black src/ tests/
# or
ruff format src/ tests/

# Lint code
ruff check src/ tests/
# or
pylint src/

# Run tests in parallel
pytest -n auto
```

## Test Distribution Guidelines

For a typical feature (e.g., "add user authentication"):

| Layer                    | Count       | Example                                                   |
| ------------------------ | ----------- | --------------------------------------------------------- |
| Layer 1: Fake tests      | 1-2 tests   | Verify `FakeAuthService.authenticate()` tracks correctly  |
| Layer 2: Real with mocks | 1-2 tests   | Verify `RealAuthService.authenticate()` calls correct API |
| Layer 3: Business logic  | 10-15 tests | Test auth flow over fakes (success, failures, edge cases) |
| Layer 4: E2E             | 1 test      | Smoke test complete login flow                            |

**Total**: ~20 tests, with 80% over fakes.

## Quick Checklist: Adding a New Integration class Method

When adding a method to an integration class interface:

- [ ] Add `@abstractmethod` to ABC (e.g., `DatabaseAdapter`)
- [ ] Implement in real class (e.g., `RealDatabaseAdapter`)
- [ ] Implement in fake class (e.g., `FakeDatabaseAdapter`)
- [ ] Add operation tracking to fake (if write operation)
- [ ] Add handler in dry-run wrapper if applicable
- [ ] Test fake (`tests/unit/fakes/test_fake_database.py`)
- [ ] Test real with mocking (`tests/integration/test_real_database.py`)
- [ ] Test business logic over fake (`tests/unit/services/test_*.py`)

## Testing Patterns Quick Reference

### AAA Pattern

```python
def test_example() -> None:
    # Arrange
    service = UserService(fake_db)

    # Act
    result = service.get_user(1)

    # Assert
    assert result.name == "Alice"
```

### Given-When-Then

```python
def test_example() -> None:
    # Given
    service = UserService(fake_db)

    # When
    result = service.get_user(1)

    # Then
    assert result.name == "Alice"
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    (1, "Alice"),
    (2, "Bob"),
    (3, None),
])
def test_get_user(input: int, expected: str | None) -> None:
    service = UserService(fake_db)
    result = service.get_user(input)
    assert result.name == expected if result else result is None
```

## Related Documentation

- `python-specific.md` - pytest fixtures, mocking, frameworks
- `testing-strategy.md` - Which layer to test at (detailed guide)
- `workflows.md` - Step-by-step guides for common tasks
- `patterns.md` - Common testing patterns explained
- `anti-patterns.md` - What to avoid
- `integration-architecture.md` - Understanding the integration layer
