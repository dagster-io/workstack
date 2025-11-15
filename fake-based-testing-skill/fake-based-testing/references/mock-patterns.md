# Mock Testing Patterns for Real Implementations

## Overview

Mock testing verifies that Real implementations correctly call external services. Use mocks to test interaction patterns, not business logic.

## Basic Mock Pattern

### Testing HTTP Client Calls

```python
from unittest.mock import patch, MagicMock

def test_real_api_client_get():
    with patch("requests.get") as mock_get:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Execute
        client = RealAPIClient(base_url="https://api.example.com")
        result = client.get("/users/123")

        # Verify
        assert result == {"status": "ok"}
        mock_get.assert_called_once_with(
            "https://api.example.com/users/123",
            headers={"Accept": "application/json"},
            timeout=30
        )
```

### Testing POST Requests

```python
def test_real_api_client_post():
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 1, "created": True}
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        client = RealAPIClient(base_url="https://api.example.com")
        data = {"name": "Alice", "email": "alice@example.com"}
        result = client.post("/users", data)

        assert result == {"id": 1, "created": True}
        mock_post.assert_called_once_with(
            "https://api.example.com/users",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
```

## Database Mock Patterns

### SQL Database Operations

```python
def test_real_database_ops_execute():
    with patch("psycopg2.connect") as mock_connect:
        # Setup mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ]

        # Execute
        db_ops = RealDatabaseOps(connection_string="postgresql://...")
        results = db_ops.execute("SELECT * FROM users WHERE active = %s", (True,))

        # Verify
        assert len(results) == 2
        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM users WHERE active = %s",
            (True,)
        )
        mock_cursor.close.assert_called_once()
```

### MongoDB Operations

```python
def test_real_mongo_ops():
    with patch("pymongo.MongoClient") as mock_client:
        # Setup mock database and collection
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_collection.find.return_value = [
            {"_id": "1", "name": "Alice"}
        ]

        # Execute
        mongo_ops = RealMongoOps("mongodb://localhost:27017/")
        results = mongo_ops.find("users", {"active": True})

        # Verify
        assert len(results) == 1
        mock_collection.find.assert_called_once_with({"active": True})
```

## External Service Mocks

### Email Service

```python
def test_real_email_ops_send():
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        email_ops = RealEmailOps(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="user",
            password="pass"
        )

        message_id = email_ops.send(
            to="alice@example.com",
            subject="Test",
            body="Hello"
        )

        # Verify connection setup
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")

        # Verify message sending
        calls = mock_server.send_message.call_args_list
        assert len(calls) == 1
        sent_msg = calls[0][0][0]
        assert sent_msg['To'] == "alice@example.com"
        assert sent_msg['Subject'] == "Test"
```

### AWS S3 Operations

```python
def test_real_s3_ops_upload():
    with patch("boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3

        s3_ops = RealS3Ops(bucket="my-bucket")
        s3_ops.upload("path/to/file.txt", b"content")

        mock_boto.assert_called_once_with("s3")
        mock_s3.put_object.assert_called_once_with(
            Bucket="my-bucket",
            Key="path/to/file.txt",
            Body=b"content"
        )
```

## Subprocess Mock Patterns

### Git Operations

```python
def test_real_git_ops_current_branch():
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

### Docker Operations

```python
def test_real_docker_ops_run_container():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="container-id-123"
        )

        docker_ops = RealDockerOps()
        container_id = docker_ops.run("nginx:latest", ports={"80": "8080"})

        assert container_id == "container-id-123"
        mock_run.assert_called_once_with(
            ["docker", "run", "-d", "-p", "8080:80", "nginx:latest"],
            capture_output=True,
            text=True,
            check=True
        )
```

## Advanced Mock Patterns

### Side Effects for Sequential Calls

```python
def test_retry_on_connection_error():
    with patch("requests.get") as mock_get:
        # First call fails, second succeeds
        mock_get.side_effect = [
            ConnectionError("Network error"),
            MagicMock(json=lambda: {"data": "success"}, status_code=200)
        ]

        client = RealAPIClient(base_url="https://api.example.com", retry=True)
        result = client.get("/data")

        assert result == {"data": "success"}
        assert mock_get.call_count == 2
```

### Partial Mocking

```python
def test_partial_mock():
    api_client = RealAPIClient(base_url="https://api.example.com")

    # Mock only the requests library, not the entire client
    with patch("requests.Session.get") as mock_get:
        mock_get.return_value.json.return_value = {"mocked": True}

        result = api_client.get_with_session("/endpoint")

        assert result == {"mocked": True}
```

### Context Manager Mocking

```python
def test_file_operations():
    with patch("builtins.open", create=True) as mock_open:
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        mock_file.read.return_value = "file content"

        file_ops = RealFileOps()
        content = file_ops.read("/path/to/file.txt")

        assert content == "file content"
        mock_open.assert_called_once_with("/path/to/file.txt", "r", encoding="utf-8")
```

## Mock Assertion Patterns

### Verify Call Order

```python
def test_transaction_operations():
    with patch("psycopg2.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn

        db_ops = RealDatabaseOps()
        db_ops.execute_transaction([
            "INSERT INTO users ...",
            "UPDATE accounts ..."
        ])

        # Verify methods called in order
        expected_calls = [
            mock_conn.cursor().__enter__().execute("INSERT INTO users ..."),
            mock_conn.cursor().__enter__().execute("UPDATE accounts ..."),
            mock_conn.commit()
        ]
        mock_conn.assert_has_calls(expected_calls, any_order=False)
```

### Verify Partial Arguments

```python
from unittest.mock import ANY

def test_api_call_with_auth():
    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"success": True}

        client = RealAPIClient(api_key="secret")
        client.post("/endpoint", {"data": "value"})

        # Don't care about exact timestamp, just verify auth header exists
        mock_post.assert_called_once_with(
            ANY,  # URL
            json={"data": "value"},
            headers={
                "Authorization": "Bearer secret",
                "X-Request-ID": ANY  # Don't care about exact ID
            }
        )
```

### Verify No Calls

```python
def test_caching_prevents_duplicate_calls():
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"cached": "data"}

        client = CachedAPIClient()
        result1 = client.get("/data")
        result2 = client.get("/data")  # Should use cache

        # Verify only called once despite two get calls
        mock_get.assert_called_once()
        assert result1 == result2
```

## Best Practices

1. **Mock at boundaries** - Mock external libraries, not your own code
2. **Verify behavior, not implementation** - Focus on inputs/outputs, not internals
3. **Use real objects when possible** - Only mock what you must
4. **Keep mocks simple** - Complex mock setup indicates design issues
5. **Test one thing** - Each test should verify a single interaction
6. **Clean up patches** - Use context managers or decorators to ensure cleanup
