"""Integration tests for HTTP routes."""

from httpx import AsyncClient


class TestCreateSession:
    """Tests for POST /api/sessions."""

    async def test_create_session_success(self, async_client: AsyncClient) -> None:
        """Creating a session should return 200 with session data."""
        response = await async_client.post(
            "/api/sessions",
            json={"working_directory": "/path/to/repo"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "active"

    async def test_create_session_with_external_id(self, async_client: AsyncClient) -> None:
        """Creating a session with external_id should include it in response."""
        response = await async_client.post(
            "/api/sessions",
            json={
                "working_directory": "/path/to/repo",
                "external_id": "slack-thread-123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["external_id"] == "slack-thread-123"


class TestListSessions:
    """Tests for GET /api/sessions."""

    async def test_list_empty(self, async_client: AsyncClient) -> None:
        """Listing when empty should return empty list."""
        response = await async_client.get("/api/sessions")

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_returns_sessions(self, async_client: AsyncClient) -> None:
        """Listing should return all sessions."""
        # Create two sessions
        await async_client.post("/api/sessions", json={"working_directory": "/path1"})
        await async_client.post("/api/sessions", json={"working_directory": "/path2"})

        response = await async_client.get("/api/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestGetSession:
    """Tests for GET /api/sessions/{session_id}."""

    async def test_get_existing_session(self, async_client: AsyncClient) -> None:
        """Getting an existing session should return it."""
        create_response = await async_client.post(
            "/api/sessions", json={"working_directory": "/path"}
        )
        session_id = create_response.json()["session_id"]

        response = await async_client.get(f"/api/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["working_directory"] == "/path"

    async def test_get_nonexistent_returns_404(self, async_client: AsyncClient) -> None:
        """Getting a nonexistent session should return 404."""
        response = await async_client.get("/api/sessions/nonexistent")

        assert response.status_code == 404


class TestDeleteSession:
    """Tests for DELETE /api/sessions/{session_id}."""

    async def test_delete_existing_session(self, async_client: AsyncClient) -> None:
        """Deleting an existing session should return success."""
        create_response = await async_client.post(
            "/api/sessions", json={"working_directory": "/path"}
        )
        session_id = create_response.json()["session_id"]

        response = await async_client.delete(f"/api/sessions/{session_id}")

        assert response.status_code == 200
        assert response.json() == {"deleted": True}

    async def test_delete_nonexistent_returns_404(self, async_client: AsyncClient) -> None:
        """Deleting a nonexistent session should return 404."""
        response = await async_client.delete("/api/sessions/nonexistent")

        assert response.status_code == 404


class TestSendMessage:
    """Tests for POST /api/sessions/{session_id}/messages."""

    async def test_send_message_returns_sse(self, async_client: AsyncClient) -> None:
        """Sending a message should return SSE stream."""
        create_response = await async_client.post(
            "/api/sessions", json={"working_directory": "/path"}
        )
        session_id = create_response.json()["session_id"]

        response = await async_client.post(
            f"/api/sessions/{session_id}/messages",
            json={"message": "Hello, Claude!"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        # SSE events should be in the response
        assert b"event:" in response.content

    async def test_send_message_to_nonexistent_returns_404(self, async_client: AsyncClient) -> None:
        """Sending to nonexistent session should return 404."""
        response = await async_client.post(
            "/api/sessions/nonexistent/messages",
            json={"message": "Hello"},
        )

        assert response.status_code == 404
