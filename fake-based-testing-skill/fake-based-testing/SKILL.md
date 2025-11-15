---
name: fake-based-testing
description: This skill should be used when writing tests for Python code that depends on external services (APIs, databases, email, etc.). It provides patterns for creating fake implementations that enable fast, deterministic testing without real I/O operations. Essential when tests need to verify business logic with external dependencies, handle error conditions, or test CLI commands.
---

# Fake-Based Testing

## Overview

This skill provides patterns and tools for writing tests using fake implementations of external dependencies. Fakes are in-memory test doubles that track mutations and enable deterministic, fast testing without real I/O operations.

## Quick Start Decision Tree

To determine the testing approach:

1. **Testing business logic that calls external services?** → Create Fake implementation
2. **Testing CLI commands?** → Use CliRunner with Fake injection
3. **Verifying exact API calls?** → Use Mock for Real implementation
4. **Testing error handling?** → Configure Fake to raise exceptions
5. **Need test isolation?** → Create fresh Fake instance per test

## Core Testing Workflow

### Step 1: Identify External Dependencies

Scan the code for external I/O operations:

- HTTP/REST API calls
- Database queries
- Email/SMS sending
- File system operations (when dependency injection is appropriate)
- Subprocess commands
- Message queues

### Step 2: Create Operations Interface

For each external dependency, create an ABC interface:

```python
from abc import ABC, abstractmethod

class EmailOps(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> str: ...
```

### Step 3: Implement Real and Fake Versions

Create both Real (production) and Fake (testing) implementations:

- **RealOps**: Performs actual I/O operations
- **FakeOps**: In-memory simulation with mutation tracking

See `references/operations-pattern.md` for complete implementation patterns.

### Step 4: Write Tests Using Fakes

Inject Fake implementations in tests to verify business logic:

```python
def test_notification_service():
    email_ops = FakeEmailOps()
    service = NotificationService(email_ops)

    service.notify_user("user@example.com", "Alert")

    assert len(email_ops.sent_emails) == 1
    assert email_ops.sent_emails[0]["to"] == "user@example.com"
```

### Step 5: Test Real Implementations with Mocks

Verify Real implementations make correct external calls:

```python
def test_real_email_ops():
    with patch("smtplib.SMTP") as mock_smtp:
        ops = RealEmailOps(smtp_config)
        ops.send("user@example.com", "Test", "Body")

        mock_smtp.assert_called_once()
```

## When to Use Fakes vs Mocks

| Use Fakes for             | Use Mocks for                       |
| ------------------------- | ----------------------------------- |
| Business logic testing    | Verifying Real implementation calls |
| State change verification | Exact argument verification         |
| Error condition testing   | Call count/order verification       |
| Integration testing       | Testing interaction patterns        |
| Fast, deterministic tests | Simulating specific failures        |

## Testing Patterns

### API Client Testing

For external API interactions, see `references/fake-patterns.md#api-clients`

### Database Operations

For database testing patterns, see `references/fake-patterns.md#database-operations`

### CLI Command Testing

For Click CLI testing with fakes, see `references/cli-testing.md`

### Error Handling

Configure fakes to simulate errors:

```python
api_ops = FakeAPIClientOps(raise_on="/api/error")
# Calling api_ops.fetch("/api/error") will raise an exception
```

### Async Operations

For async testing patterns, see `references/fake-patterns.md#async-operations`

## Resources

### references/

- `operations-pattern.md` - Complete operations layer implementation guide with full examples
- `fake-patterns.md` - Detailed fake implementation patterns for various services (API clients, databases, cache, message queues)
- `mock-patterns.md` - Mock testing patterns for Real implementations
- `cli-testing.md` - CLI testing with Click and fake injection

## Key Principles

1. **Fake for behavior, Mock for interaction** - Use fakes to test what the code does, mocks to test how it calls dependencies
2. **Fresh instances per test** - Create new fake instances to ensure test isolation
3. **Track mutations** - Fakes should record all operations for verification
4. **No real I/O in fakes** - Keep fakes pure in-memory for speed and determinism
5. **Constructor injection** - Pass dependencies through constructors, not patches
