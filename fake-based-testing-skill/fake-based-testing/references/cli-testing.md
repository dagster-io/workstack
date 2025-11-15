# CLI Testing with Click and Fakes

## Overview

Testing Click CLI commands with fake operations enables fast, deterministic testing of command-line interfaces without real I/O operations.

## Basic CLI Testing Setup

### Simple Command Test

```python
from click.testing import CliRunner
import click

def test_simple_command():
    runner = CliRunner()

    @click.command()
    @click.option("--name", default="World")
    def hello(name):
        click.echo(f"Hello, {name}!")

    result = runner.invoke(hello, ["--name", "Alice"])

    assert result.exit_code == 0
    assert "Hello, Alice!" in result.output
```

## Dependency Injection via Context

### Setting Up Context Objects

```python
@click.command()
@click.option("--endpoint", required=True)
@click.pass_context
def fetch_data(ctx, endpoint):
    """Command that uses injected operations."""
    api_ops = ctx.obj["api_ops"]

    try:
        data = api_ops.get(endpoint)
        click.echo(f"Data: {data}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        ctx.exit(1)

def test_fetch_data_command():
    runner = CliRunner()
    fake_api = FakeAPIClientOps(
        _get_responses={
            "/api/users": [{"id": 1, "name": "Alice"}]
        }
    )

    result = runner.invoke(
        fetch_data,
        ["--endpoint", "/api/users"],
        obj={"api_ops": fake_api}
    )

    assert result.exit_code == 0
    assert "Alice" in result.output
    assert fake_api.get_calls == ["/api/users"]
```

### Multiple Dependencies

```python
@click.command()
@click.pass_context
def sync_command(ctx):
    """Command with multiple injected dependencies."""
    api_ops = ctx.obj["api_ops"]
    db_ops = ctx.obj["db_ops"]
    cache_ops = ctx.obj["cache_ops"]

    # Fetch from API
    users = api_ops.get("/api/users")

    # Store in database
    for user in users:
        db_ops.insert("users", user)

    # Update cache
    cache_ops.set("users_synced", True, ttl=3600)

    click.echo(f"Synced {len(users)} users")

def test_sync_command():
    runner = CliRunner()

    # Setup all fakes
    fake_api = FakeAPIClientOps(
        _get_responses={
            "/api/users": [
                {"name": "Alice"},
                {"name": "Bob"}
            ]
        }
    )
    fake_db = FakeDatabaseOps()
    fake_cache = FakeCacheOps()

    result = runner.invoke(
        sync_command,
        obj={
            "api_ops": fake_api,
            "db_ops": fake_db,
            "cache_ops": fake_cache
        }
    )

    assert result.exit_code == 0
    assert "Synced 2 users" in result.output
    assert len(fake_db._tables.get("users", [])) == 2
    assert fake_cache.get("users_synced") is True
```

## Testing Command Groups

### Group with Shared Context

```python
@click.group()
@click.pass_context
def cli(ctx):
    """Main command group."""
    ctx.ensure_object(dict)

@cli.command()
@click.pass_context
def status(ctx):
    api_ops = ctx.obj["api_ops"]
    status = api_ops.get("/api/status")
    click.echo(f"Status: {status['state']}")

@cli.command()
@click.option("--message", required=True)
@click.pass_context
def notify(ctx, message):
    email_ops = ctx.obj["email_ops"]
    email_ops.send("admin@example.com", "Notification", message)
    click.echo("Notification sent")

def test_command_group():
    runner = CliRunner()

    fake_api = FakeAPIClientOps(
        _get_responses={"/api/status": {"state": "healthy"}}
    )
    fake_email = FakeEmailOps()

    # Test status command
    result = runner.invoke(
        cli,
        ["status"],
        obj={"api_ops": fake_api}
    )
    assert "Status: healthy" in result.output

    # Test notify command
    result = runner.invoke(
        cli,
        ["notify", "--message", "Test alert"],
        obj={"email_ops": fake_email}
    )
    assert "Notification sent" in result.output
    assert len(fake_email.sent_emails) == 1
```

## Error Handling Tests

### Testing Error Conditions

```python
def test_command_handles_api_error():
    runner = CliRunner()

    # Configure fake to raise error
    fake_api = FakeAPIClientOps(_raise_on={"/api/data"})

    result = runner.invoke(
        fetch_data,
        ["--endpoint", "/api/data"],
        obj={"api_ops": fake_api}
    )

    assert result.exit_code == 1
    assert "Error" in result.output
```

### Testing Validation Errors

```python
@click.command()
@click.option("--email", required=True)
@click.pass_context
def send_email(ctx, email):
    if "@" not in email:
        click.echo("Invalid email format", err=True)
        ctx.exit(2)

    email_ops = ctx.obj["email_ops"]
    email_ops.send(email, "Test", "Body")
    click.echo(f"Email sent to {email}")

def test_email_validation():
    runner = CliRunner()
    fake_email = FakeEmailOps()

    # Test invalid email
    result = runner.invoke(
        send_email,
        ["--email", "invalid"],
        obj={"email_ops": fake_email}
    )
    assert result.exit_code == 2
    assert "Invalid email format" in result.output
    assert len(fake_email.sent_emails) == 0

    # Test valid email
    result = runner.invoke(
        send_email,
        ["--email", "valid@example.com"],
        obj={"email_ops": fake_email}
    )
    assert result.exit_code == 0
    assert len(fake_email.sent_emails) == 1
```

## Interactive Commands

### Testing Prompts

```python
@click.command()
@click.pass_context
def interactive_setup(ctx):
    name = click.prompt("Enter your name")
    email = click.prompt("Enter your email")
    confirm = click.confirm("Save this information?")

    if confirm:
        db_ops = ctx.obj["db_ops"]
        user_id = db_ops.insert("users", {"name": name, "email": email})
        click.echo(f"User created with ID: {user_id}")
    else:
        click.echo("Cancelled")

def test_interactive_command():
    runner = CliRunner()
    fake_db = FakeDatabaseOps()

    # Simulate user input
    result = runner.invoke(
        interactive_setup,
        input="Alice\nalice@example.com\ny\n",
        obj={"db_ops": fake_db}
    )

    assert result.exit_code == 0
    assert "User created with ID: 1" in result.output
    assert len(fake_db._tables.get("users", [])) == 1
```

### Testing Choice Prompts

```python
@click.command()
@click.pass_context
def select_action(ctx):
    action = click.prompt(
        "Select action",
        type=click.Choice(["fetch", "sync", "delete"]),
        default="fetch"
    )

    api_ops = ctx.obj["api_ops"]

    if action == "fetch":
        data = api_ops.get("/api/data")
        click.echo(f"Fetched: {data}")
    elif action == "sync":
        click.echo("Syncing...")
    elif action == "delete":
        api_ops.delete("/api/data")
        click.echo("Deleted")

def test_choice_prompt():
    runner = CliRunner()
    fake_api = FakeAPIClientOps(
        _get_responses={"/api/data": {"value": 42}}
    )

    # Test fetch action
    result = runner.invoke(
        select_action,
        input="fetch\n",
        obj={"api_ops": fake_api}
    )
    assert "Fetched: {'value': 42}" in result.output

    # Test delete action
    result = runner.invoke(
        select_action,
        input="delete\n",
        obj={"api_ops": fake_api}
    )
    assert "Deleted" in result.output
    assert fake_api._delete_calls == ["/api/data"]
```

## Testing Output Formats

### JSON Output

```python
@click.command()
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
def list_users(ctx, format):
    api_ops = ctx.obj["api_ops"]
    users = api_ops.get("/api/users")

    if format == "json":
        click.echo(json.dumps(users))
    else:
        for user in users:
            click.echo(f"- {user['name']} ({user['email']})")

def test_json_output():
    runner = CliRunner()
    fake_api = FakeAPIClientOps(
        _get_responses={
            "/api/users": [
                {"name": "Alice", "email": "alice@example.com"},
                {"name": "Bob", "email": "bob@example.com"}
            ]
        }
    )

    # Test JSON format
    result = runner.invoke(
        list_users,
        ["--format", "json"],
        obj={"api_ops": fake_api}
    )

    output_data = json.loads(result.output)
    assert len(output_data) == 2
    assert output_data[0]["name"] == "Alice"
```

## Testing File Operations

### Using Isolated Filesystem

```python
@click.command()
@click.argument("filename")
@click.pass_context
def process_file(ctx, filename):
    api_ops = ctx.obj["api_ops"]

    # Read file
    with open(filename, "r") as f:
        content = f.read()

    # Process via API
    result = api_ops.post("/api/process", {"content": content})

    # Write result
    output_file = f"{filename}.processed"
    with open(output_file, "w") as f:
        f.write(result["processed"])

    click.echo(f"Processed file saved to {output_file}")

def test_file_processing():
    runner = CliRunner()
    fake_api = FakeAPIClientOps(
        _post_responses={
            "/api/process": {"processed": "PROCESSED CONTENT"}
        }
    )

    with runner.isolated_filesystem():
        # Create test file
        with open("test.txt", "w") as f:
            f.write("original content")

        result = runner.invoke(
            process_file,
            ["test.txt"],
            obj={"api_ops": fake_api}
        )

        assert result.exit_code == 0
        assert "Processed file saved" in result.output

        # Verify output file
        with open("test.txt.processed", "r") as f:
            assert f.read() == "PROCESSED CONTENT"

        # Verify API was called
        assert len(fake_api.post_calls) == 1
        assert fake_api.post_calls[0][1]["content"] == "original content"
```

## Testing Progress and Callbacks

### Progress Bar Testing

```python
@click.command()
@click.pass_context
def batch_process(ctx):
    api_ops = ctx.obj["api_ops"]
    items = api_ops.get("/api/items")

    with click.progressbar(items, label="Processing") as bar:
        for item in bar:
            api_ops.post(f"/api/process/{item['id']}", item)

    click.echo(f"Processed {len(items)} items")

def test_progress_bar():
    runner = CliRunner()
    fake_api = FakeAPIClientOps(
        _get_responses={
            "/api/items": [
                {"id": 1, "data": "a"},
                {"id": 2, "data": "b"},
                {"id": 3, "data": "c"}
            ]
        }
    )

    result = runner.invoke(
        batch_process,
        obj={"api_ops": fake_api}
    )

    assert result.exit_code == 0
    assert "Processed 3 items" in result.output
    assert len(fake_api.post_calls) == 3
```

## Fixtures for CLI Testing

### Reusable Test Fixtures

```python
import pytest

@pytest.fixture
def cli_runner():
    """Provide CliRunner instance."""
    return CliRunner()

@pytest.fixture
def fake_api():
    """Provide configured fake API client."""
    return FakeAPIClientOps(
        _get_responses={
            "/api/status": {"status": "ok"},
            "/api/users": [{"id": 1, "name": "Test"}]
        }
    )

@pytest.fixture
def fake_db():
    """Provide fake database with test data."""
    fake = FakeDatabaseOps()
    fake.seed_table("users", [
        {"id": 1, "name": "Alice", "active": True},
        {"id": 2, "name": "Bob", "active": False}
    ])
    return fake

def test_with_fixtures(cli_runner, fake_api, fake_db):
    result = cli_runner.invoke(
        my_command,
        ["--sync"],
        obj={
            "api_ops": fake_api,
            "db_ops": fake_db
        }
    )

    assert result.exit_code == 0
```

## Common Assertions

### Result Properties

```python
# Exit code
assert result.exit_code == 0  # Success
assert result.exit_code != 0  # Any error
assert result.exit_code == 1  # Specific error

# Output
assert "text" in result.output  # Contains text
assert result.output.strip() == "exact"  # Exact match
assert not result.output  # No output

# Exception
assert result.exception is None  # No exception
assert isinstance(result.exception, ValueError)  # Specific exception

# Output streams
assert "error" in result.stderr  # Error output (Click 8.0+)
```

### Fake State Assertions

```python
# API calls
assert fake_api.get_calls == ["/api/endpoint"]
assert len(fake_api.post_calls) == 2
assert fake_api.post_calls[0][1]["key"] == "value"

# Database state
assert len(fake_db._tables["users"]) == 3
assert fake_db.queries[0][0] == "SELECT * FROM users"

# Email tracking
assert len(fake_email.sent_emails) == 1
assert fake_email.sent_emails[0]["to"] == "user@example.com"
```

## Best Practices

1. **Use CliRunner** - Never test CLI commands with subprocess
2. **Inject via obj** - Pass fakes through context object
3. **Test both success and failure** - Cover error paths
4. **Use isolated_filesystem** - For file operations
5. **Assert on fakes** - Verify operations were performed
6. **Keep tests focused** - One behavior per test