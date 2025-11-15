# Operations Layer Pattern

## Overview

The operations layer pattern isolates external dependencies behind interfaces, enabling easy testing with fake implementations while maintaining production code integrity.

## Complete Implementation Example

### 1. Define the Interface (ABC)

```python
from abc import ABC, abstractmethod
from typing import Any

class EmailOps(ABC):
    """Abstract interface for email operations."""

    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> str:
        """Send an email and return message ID."""
        ...

    @abstractmethod
    def fetch_inbox(self, user: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent emails for a user."""
        ...

    @abstractmethod
    def mark_read(self, message_id: str) -> None:
        """Mark an email as read."""
        ...
```

### 2. Implement Real Operations

```python
import smtplib
import imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class RealEmailOps(EmailOps):
    """Production implementation using actual email services."""

    def __init__(self, smtp_config: dict, imap_config: dict):
        self._smtp_config = smtp_config
        self._imap_config = imap_config

    def send(self, to: str, subject: str, body: str) -> str:
        msg = MIMEMultipart()
        msg['From'] = self._smtp_config['from']
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(self._smtp_config['host'], self._smtp_config['port']) as server:
            server.starttls()
            server.login(self._smtp_config['user'], self._smtp_config['password'])
            result = server.send_message(msg)
            return msg['Message-ID']

    def fetch_inbox(self, user: str, limit: int = 10) -> list[dict[str, Any]]:
        with imaplib.IMAP4_SSL(self._imap_config['host']) as mail:
            mail.login(self._imap_config['user'], self._imap_config['password'])
            mail.select('inbox')
            # Implementation details...
            return []

    def mark_read(self, message_id: str) -> None:
        # Implementation details...
        pass
```

### 3. Implement Fake Operations

```python
from dataclasses import dataclass, field
from typing import Any
import uuid

@dataclass
class FakeEmailOps(EmailOps):
    """In-memory fake for testing."""

    # Configuration
    _inbox: list[dict[str, Any]] = field(default_factory=list)
    _should_fail_on: set[str] = field(default_factory=set)

    # Mutation tracking
    _sent_emails: list[dict[str, Any]] = field(default_factory=list, init=False)
    _read_messages: list[str] = field(default_factory=list, init=False)
    _fetch_calls: list[tuple[str, int]] = field(default_factory=list, init=False)

    def send(self, to: str, subject: str, body: str) -> str:
        if to in self._should_fail_on:
            raise ValueError(f"Simulated failure for {to}")

        message_id = f"msg-{uuid.uuid4().hex[:8]}"
        self._sent_emails.append({
            "id": message_id,
            "to": to,
            "subject": subject,
            "body": body
        })
        return message_id

    def fetch_inbox(self, user: str, limit: int = 10) -> list[dict[str, Any]]:
        self._fetch_calls.append((user, limit))
        return self._inbox[:limit]

    def mark_read(self, message_id: str) -> None:
        self._read_messages.append(message_id)

    # Properties for test assertions
    @property
    def sent_emails(self) -> list[dict[str, Any]]:
        return self._sent_emails.copy()

    @property
    def read_messages(self) -> list[str]:
        return self._read_messages.copy()
```

## Testing Strategy

### Test Business Logic with Fakes

```python
def test_notification_service_sends_welcome_email():
    # Arrange
    email_ops = FakeEmailOps()
    service = NotificationService(email_ops)

    # Act
    service.send_welcome("user@example.com")

    # Assert
    assert len(email_ops.sent_emails) == 1
    email = email_ops.sent_emails[0]
    assert email["to"] == "user@example.com"
    assert "Welcome" in email["subject"]
```

### Test Real Implementation with Mocks

```python
from unittest.mock import patch, MagicMock

def test_real_email_ops_smtp_integration():
    with patch("smtplib.SMTP") as mock_smtp:
        # Setup mock
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Execute
        ops = RealEmailOps(smtp_config, imap_config)
        message_id = ops.send("test@example.com", "Test", "Body")

        # Verify
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.send_message.assert_called_once()
```

### Test Error Handling

```python
def test_service_handles_email_failure():
    # Configure fake to fail
    email_ops = FakeEmailOps(_should_fail_on={"bad@example.com"})
    service = NotificationService(email_ops)

    # Should handle gracefully
    result = service.send_notification("bad@example.com", "Test")

    assert result is False  # Service returns False on failure
    assert len(email_ops.sent_emails) == 0  # No email sent
```

## Best Practices

1. **Keep interfaces minimal** - Only include methods actually used
2. **Make fakes configurable** - Allow tests to control behavior
3. **Track all mutations** - Record every operation for verification
4. **Use dataclasses** - Clean initialization and automatic `__repr__`
5. **Copy return values** - Prevent test pollution through shared state
6. **Test both paths** - Verify Real with mocks, business logic with fakes

## Common Patterns

### Async Operations

```python
class AsyncEmailOps(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> str: ...

class FakeAsyncEmailOps(AsyncEmailOps):
    def __init__(self):
        self._sent_emails: list[dict] = []

    async def send(self, to: str, subject: str, body: str) -> str:
        self._sent_emails.append({"to": to, "subject": subject, "body": body})
        return f"msg-{len(self._sent_emails)}"
```

### Pagination Support

```python
@dataclass
class FakeAPIClientOps:
    _responses: dict[str, list[dict]] = field(default_factory=dict)

    def fetch_page(self, endpoint: str, page: int, size: int) -> dict:
        data = self._responses.get(endpoint, [])
        start = page * size
        end = start + size
        return {
            "items": data[start:end],
            "page": page,
            "total": len(data),
            "has_next": end < len(data)
        }
```

### Stateful Operations

```python
@dataclass
class FakeCacheOps:
    _cache: dict[str, Any] = field(default_factory=dict)
    _hits: int = field(default=0, init=False)
    _misses: int = field(default=0, init=False)

    def get(self, key: str) -> Any | None:
        if key in self._cache:
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value
```
