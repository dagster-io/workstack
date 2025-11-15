---
name: fake-based-testing-cli
version: 1.0.0
min_tokens: 30
max_tokens: 500
optimized_for: agents
auto_trigger_patterns:
  - "tests/**/test_*_cli.py"
  - "tests/**/cli/**/*.py"
---

# CLI Testing with Fake-Based Patterns

Specialized patterns for testing Click CLI commands using fake operations.

## ⚡ CLI Testing Checklist

WHEN: Testing Click CLI command
DO:

1. Use CliRunner for test execution
2. Inject FakeOps via Click context (`obj` parameter)
3. Assert on exit code, output, and fake mutations

WHEN: CLI command calls external APIs
DO: Pass FakeAPIClientOps in context object

WHEN: CLI needs complex setup
DO: Use pytest fixtures to configure fakes

## CLI Testing Pattern

WHEN: Testing CLI commands
DO: Use CliRunner with FakeOps injection
VERIFY: Check exit code, output text, and Fake mutations

<details><summary>Basic Pattern</summary>

```python
from click.testing import CliRunner

def test_api_command():
    runner = CliRunner()
    fake_api = FakeAPIClientOps({
        "/api/status": {"status": "healthy", "version": "1.0"}
    })

    result = runner.invoke(
        check_api_status,
        ["--endpoint", "/api/status"],
        obj={"api_ops": fake_api}
    )

    assert result.exit_code == 0
    assert "healthy" in result.output
    assert fake_api.fetched_urls == ["/api/status"]
```

</details>

<details><summary>With Fixture Setup</summary>

```python
import pytest
from click.testing import CliRunner

@pytest.fixture
def cli_runner():
    return CliRunner()

@pytest.fixture
def fake_api():
    return FakeAPIClientOps({
        "/api/users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ]
    })

def test_sync_users_command(cli_runner, fake_api):
    result = cli_runner.invoke(
        sync_users,
        ["--source", "/api/users"],
        obj={"api_ops": fake_api}
    )

    assert result.exit_code == 0
    assert "Synced 2 users" in result.output
    assert fake_api.fetched_urls == ["/api/users"]
```

</details>

## Click Context Injection

WHEN: CLI command needs dependencies
DO: Pass via Click context `obj` parameter
NOTE: Context is a dict available in command via `@click.pass_context`

<details><summary>Implementation Pattern</summary>

```python
import click

@click.command()
@click.option("--endpoint")
@click.pass_context
def api_command(ctx, endpoint):
    """Command that uses injected ops."""
    api_ops = ctx.obj["api_ops"]
    result = api_ops.fetch(endpoint)
    click.echo(f"Result: {result}")

# In test
def test_api_command():
    runner = CliRunner()
    fake_api = FakeAPIClientOps({"/data": {"value": 42}})

    result = runner.invoke(
        api_command,
        ["--endpoint", "/data"],
        obj={"api_ops": fake_api}
    )

    assert result.exit_code == 0
    assert "value: 42" in result.output
```

</details>

## Testing Error Cases

WHEN: CLI should handle API errors gracefully
DO: Configure fake to raise exceptions
VERIFY: Exit code and error message in output

<details><summary>Error Handling Pattern</summary>

```python
def test_api_error_handling():
    runner = CliRunner()
    fake_api = FakeAPIClientOps()  # No responses configured

    result = runner.invoke(
        fetch_data,
        ["--url", "/api/missing"],
        obj={"api_ops": fake_api}
    )

    assert result.exit_code != 0
    assert "Error" in result.output
    assert fake_api.fetched_urls == ["/api/missing"]
```

</details>

## Testing Interactive Commands

WHEN: CLI uses click.prompt or click.confirm
DO: Pass input via CliRunner
VERIFY: Prompts appear and input handled correctly

<details><summary>Interactive Pattern</summary>

```python
def test_interactive_command():
    runner = CliRunner()
    fake_api = FakeAPIClientOps({})

    # Simulate user typing "yes" then "alice@example.com"
    result = runner.invoke(
        create_user,
        input="yes\nalice@example.com\n",
        obj={"api_ops": fake_api}
    )

    assert result.exit_code == 0
    assert "Created user" in result.output
    assert len(fake_api.post_requests) == 1
```

</details>

## Common CLI Assertions

**Exit codes:**

- `assert result.exit_code == 0` - Success
- `assert result.exit_code != 0` - Any error
- `assert result.exit_code == 1` - Specific error code

**Output:**

- `assert "text" in result.output` - Check message
- `assert result.output.strip() == "exact"` - Exact match
- `assert not result.output` - No output

**Exceptions:**

- `assert result.exception is None` - No exception
- `assert isinstance(result.exception, ValueError)` - Specific exception

## 🤖 Agent Tips

- Use CliRunner for all Click command tests
- Inject fakes via `obj={"key": fake}`
- Access in command via `ctx.obj["key"]`
- Assert on exit_code, output, and fake state
- Use `input=` for interactive commands

<details><summary>Token Usage</summary>

- Checklist only: ~30 tokens
- - Basic pattern: ~100 tokens
- Full expansion: ~500 tokens

</details>
