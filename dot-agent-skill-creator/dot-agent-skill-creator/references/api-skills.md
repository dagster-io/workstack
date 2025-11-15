# API Integration Skills Pattern

## Overview

Skills that integrate with external APIs require authentication handling, error management, and often CLI commands for common operations.

## Implementation Pattern

### 1. Define API Operations Interface

```python
# src/my_kit/api_client.py
from abc import ABC, abstractmethod
from typing import Any

class APIClientOps(ABC):
    @abstractmethod
    def get(self, endpoint: str) -> dict[str, Any]: ...

    @abstractmethod
    def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def delete(self, endpoint: str) -> None: ...

class RealAPIClient(APIClientOps):
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session = self._create_session()

    def _create_session(self):
        import requests
        session = requests.Session()
        session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        })
        return session

    def get(self, endpoint: str) -> dict[str, Any]:
        response = self.session.get(f"{self.base_url}/{endpoint}")
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(f"{self.base_url}/{endpoint}", json=data)
        response.raise_for_status()
        return response.json()
```

### 2. Create CLI Commands

```python
# src/my_kit/commands.py
import click
import json
import os
from pathlib import Path

@click.group()
def api():
    """API interaction commands."""
    pass

@api.command()
@click.option('--api-key', envvar='API_KEY', required=True)
@click.option('--endpoint', required=True)
@click.option('--output', '-o', type=click.Path())
def fetch(api_key: str, endpoint: str, output: str | None):
    """Fetch data from API endpoint."""
    from my_kit.api_client import RealAPIClient

    client = RealAPIClient(api_key, get_base_url())

    try:
        data = client.get(endpoint)

        if output:
            Path(output).write_text(json.dumps(data, indent=2))
            click.echo(f"✅ Saved to {output}")
        else:
            click.echo(json.dumps(data, indent=2))

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

@api.command()
@click.option('--api-key', envvar='API_KEY', required=True)
@click.option('--endpoint', required=True)
@click.argument('data_file', type=click.File('r'))
def send(api_key: str, endpoint: str, data_file):
    """Send data to API endpoint."""
    from my_kit.api_client import RealAPIClient

    client = RealAPIClient(api_key, get_base_url())
    data = json.load(data_file)

    try:
        response = client.post(endpoint, data)
        click.echo(json.dumps(response, indent=2))
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

def get_base_url() -> str:
    """Get API base URL from environment or config."""
    return os.environ.get('API_BASE_URL', 'https://api.example.com')
```

### 3. Authentication Management

```python
# src/my_kit/auth.py
import click
import keyring
import json
from pathlib import Path

@click.group()
def auth():
    """API authentication management."""
    pass

@auth.command()
@click.option('--api-key', prompt=True, hide_input=True)
@click.option('--base-url', prompt=True)
def configure(api_key: str, base_url: str):
    """Configure API credentials."""
    # Store securely using keyring
    keyring.set_password('my-api', 'api_key', api_key)

    # Store non-sensitive config
    config_path = Path.home() / '.my-api' / 'config.json'
    config_path.parent.mkdir(exist_ok=True)

    config = {'base_url': base_url}
    config_path.write_text(json.dumps(config, indent=2))

    click.echo("✅ API configured successfully")

@auth.command()
def test():
    """Test API connection."""
    api_key = keyring.get_password('my-api', 'api_key')
    if not api_key:
        click.echo("❌ No API key configured. Run: dot-agent run my-kit auth configure")
        sys.exit(1)

    from my_kit.api_client import RealAPIClient
    client = RealAPIClient(api_key, get_base_url())

    try:
        # Test with a simple endpoint
        client.get('status')
        click.echo("✅ API connection successful")
    except Exception as e:
        click.echo(f"❌ Connection failed: {e}", err=True)
        sys.exit(1)
```

### 4. Error Handling

```python
# src/my_kit/errors.py
class APIError(Exception):
    """Base API error."""
    pass

class AuthenticationError(APIError):
    """Authentication failed."""
    pass

class RateLimitError(APIError):
    """Rate limit exceeded."""
    pass

class NotFoundError(APIError):
    """Resource not found."""
    pass

def handle_api_error(response):
    """Convert HTTP errors to specific exceptions."""
    if response.status_code == 401:
        raise AuthenticationError("Invalid API key")
    elif response.status_code == 429:
        raise RateLimitError("Rate limit exceeded")
    elif response.status_code == 404:
        raise NotFoundError("Resource not found")
    else:
        response.raise_for_status()
```

## Skill Documentation

### SKILL.md Structure

````markdown
---
name: api-integration
description: This skill should be used when working with the Example API. It provides authentication management, common operations via CLI commands, and patterns for API integration. Essential for fetching data, sending updates, and managing API workflows.
---

# API Integration

Work with the Example API efficiently.

## Quick Start

### Setup

1. Configure authentication:

```bash
dot-agent run my-kit auth configure
```
````

2. Test connection:

```bash
dot-agent run my-kit auth test
```

### Basic Operations

```bash
# Fetch data
dot-agent run my-kit api fetch --endpoint users

# Send data
dot-agent run my-kit api send --endpoint users/create data.json

# With output file
dot-agent run my-kit api fetch --endpoint users/123 -o user.json
```

## Authentication

The API key can be provided in three ways:

1. Environment variable: `export API_KEY=xxx`
2. Command option: `--api-key xxx`
3. Secure storage via `auth configure`

## CLI Commands

Available via `dot-agent run my-kit`:

### Authentication

- **auth configure** - Store API credentials securely
- **auth test** - Verify API connection

### API Operations

- **api fetch** - GET data from endpoint
- **api send** - POST data to endpoint
- **api delete** - DELETE resource
- **api update** - PUT/PATCH resource

### Data Processing

- **transform** - Transform API responses
- **validate** - Validate data against schema

## Error Handling

Common errors and solutions:

| Error            | Solution                        |
| ---------------- | ------------------------------- |
| 401 Unauthorized | Check API key with `auth test`  |
| 429 Rate Limited | Wait and retry with backoff     |
| 404 Not Found    | Verify endpoint and resource ID |
| Network Error    | Check connection and base URL   |

## Advanced Usage

See references for:

- `references/batch-operations.md` - Bulk API operations
- `references/pagination.md` - Handling paginated responses
- `references/webhooks.md` - Setting up webhooks

````

## Common API Patterns

### Pagination Handling

```python
@click.command()
@click.option('--api-key', envvar='API_KEY', required=True)
@click.option('--endpoint', required=True)
@click.option('--limit', default=100)
def fetch_all(api_key: str, endpoint: str, limit: int):
    """Fetch all pages of paginated endpoint."""
    client = RealAPIClient(api_key, get_base_url())

    all_items = []
    page = 1
    total_pages = None

    with click.progressbar(length=100, label='Fetching pages') as bar:
        while True:
            response = client.get(f"{endpoint}?page={page}&limit={limit}")

            all_items.extend(response['items'])

            if total_pages is None:
                total_pages = response['total_pages']
                bar.length = total_pages

            bar.update(1)

            if page >= total_pages:
                break
            page += 1

    click.echo(f"✅ Fetched {len(all_items)} items")
    click.echo(json.dumps(all_items, indent=2))
````

### Rate Limiting

```python
import time
from functools import wraps

def rate_limited(max_calls_per_second=10):
    """Decorator to rate limit API calls."""
    min_interval = 1.0 / max_calls_per_second
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

class RateLimitedAPIClient(RealAPIClient):
    @rate_limited(max_calls_per_second=5)
    def get(self, endpoint: str) -> dict:
        return super().get(endpoint)
```

### Retry Logic

```python
import backoff

class RetryingAPIClient(RealAPIClient):
    @backoff.on_exception(
        backoff.expo,
        (ConnectionError, TimeoutError),
        max_tries=3,
        max_time=30
    )
    def get(self, endpoint: str) -> dict:
        return super().get(endpoint)
```

### Webhook Registration

```python
@click.command()
@click.option('--api-key', envvar='API_KEY', required=True)
@click.argument('webhook_url')
@click.option('--events', multiple=True, required=True)
def register_webhook(api_key: str, webhook_url: str, events: tuple[str]):
    """Register webhook for events."""
    client = RealAPIClient(api_key, get_base_url())

    webhook_data = {
        'url': webhook_url,
        'events': list(events),
        'secret': generate_webhook_secret()
    }

    try:
        response = client.post('webhooks', webhook_data)
        click.echo(f"✅ Webhook registered: {response['id']}")
        click.echo(f"Secret: {webhook_data['secret']} (save this!)")
    except Exception as e:
        click.echo(f"❌ Failed: {e}", err=True)

def generate_webhook_secret() -> str:
    """Generate secure webhook secret."""
    import secrets
    return secrets.token_urlsafe(32)
```

## Testing API Skills

### Unit Tests with Fakes

```python
# tests/test_api_commands.py
from click.testing import CliRunner
from my_kit.commands import fetch
from my_kit.api_client import APIClientOps

class FakeAPIClient(APIClientOps):
    def __init__(self, responses: dict):
        self.responses = responses
        self.requests = []

    def get(self, endpoint: str) -> dict:
        self.requests.append(('GET', endpoint))
        return self.responses.get(endpoint, {})

def test_fetch_command():
    runner = CliRunner()
    fake_client = FakeAPIClient({
        'users': [{'id': 1, 'name': 'Alice'}]
    })

    # Patch the client creation
    with patch('my_kit.commands.RealAPIClient', return_value=fake_client):
        result = runner.invoke(fetch, ['--api-key', 'test', '--endpoint', 'users'])

    assert result.exit_code == 0
    assert 'Alice' in result.output
    assert fake_client.requests == [('GET', 'users')]
```

### Integration Tests

```python
def test_real_api_integration():
    """Test against real API (requires API_KEY env var)."""
    api_key = os.environ.get('TEST_API_KEY')
    if not api_key:
        pytest.skip("No TEST_API_KEY provided")

    runner = CliRunner()
    result = runner.invoke(
        fetch,
        ['--endpoint', 'status'],
        env={'API_KEY': api_key}
    )

    assert result.exit_code == 0
    assert 'status' in result.output.lower()
```

## Best Practices

1. **Secure Credentials** - Never hardcode API keys
2. **Rate Limiting** - Respect API limits
3. **Error Recovery** - Implement retry with backoff
4. **Caching** - Cache responses when appropriate
5. **Validation** - Validate responses against schema
6. **Logging** - Log API calls for debugging
7. **Testing** - Use fakes for unit tests
8. **Documentation** - Document all endpoints used
