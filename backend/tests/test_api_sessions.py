"""
Integration tests for sessions API endpoints.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client: AsyncClient):
        """Test root endpoint returns API info."""
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Agentic Chatbot API"
        assert data["version"] == "1.0.0"
        assert "docs" in data

    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        """Test health check endpoint."""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestSessionsEndpoints:
    """Test sessions API endpoints."""

    @pytest.mark.asyncio
    async def test_create_session(self, async_client: AsyncClient):
        """Test creating a new session."""
        response = await async_client.post("/api/v1/sessions", json={})
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["title"] == "New Chat"
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_session_with_title(self, async_client: AsyncClient):
        """Test creating a session with custom title."""
        response = await async_client.post(
            "/api/v1/sessions", json={"title": "My Custom Session"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "My Custom Session"

    @pytest.mark.asyncio
    async def test_list_sessions(self, async_client: AsyncClient):
        """Test listing sessions."""
        response = await async_client.get("/api/v1/sessions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_session(self, async_client: AsyncClient):
        """Test getting a specific session."""
        create_response = await async_client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["id"]

        response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, async_client: AsyncClient):
        """Test getting a session that doesn't exist."""
        response = await async_client.get("/api/v1/sessions/nonexistent-id")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_session_title(self, async_client: AsyncClient):
        """Test updating session title."""
        create_response = await async_client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["id"]

        response = await async_client.patch(
            f"/api/v1/sessions/{session_id}", json={"title": "Updated Title"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_archive_session(self, async_client: AsyncClient):
        """Test archiving a session."""
        create_response = await async_client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["id"]

        response = await async_client.patch(
            f"/api/v1/sessions/{session_id}", json={"archived": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["archived"] is True

    @pytest.mark.asyncio
    async def test_delete_session(self, async_client: AsyncClient):
        """Test deleting a session."""
        create_response = await async_client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["id"]

        response = await async_client.delete(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 200

        get_response = await async_client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 404


class TestMessagesEndpoints:
    """Test messages API endpoints."""

    @pytest.mark.asyncio
    async def test_get_messages(self, async_client: AsyncClient):
        """Test getting messages for a session."""
        create_response = await async_client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["id"]

        response = await async_client.get(f"/api/v1/sessions/{session_id}/messages")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_create_message(self, async_client: AsyncClient):
        """Test creating a message in a session."""
        create_response = await async_client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["id"]

        response = await async_client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"role": "user", "content": "Hello, chatbot!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "user"
        assert data["content"] == "Hello, chatbot!"
        assert data["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_create_message_with_agent_type(self, async_client: AsyncClient):
        """Test creating a message with agent type."""
        create_response = await async_client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["id"]

        response = await async_client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={
                "role": "assistant",
                "content": "I am the master agent.",
                "agent_type": "master",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["agent_type"] == "master"

    @pytest.mark.asyncio
    async def test_create_message_with_parent(self, async_client: AsyncClient):
        """Test creating a message with parent for forking."""
        create_response = await async_client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["id"]

        msg1_response = await async_client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"role": "user", "content": "First message"},
        )
        msg1_id = msg1_response.json()["id"]

        msg2_response = await async_client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={
                "role": "assistant",
                "content": "Response to first",
                "parent_message_id": msg1_id,
            },
        )
        assert msg2_response.status_code == 200
        data = msg2_response.json()
        assert data["parent_message_id"] == msg1_id


class TestWorkingMemoryEndpoints:
    """Test working memory API endpoints."""

    @pytest.mark.asyncio
    async def test_get_working_memory(self, async_client: AsyncClient):
        """Test getting working memory for a session."""
        create_response = await async_client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["id"]

        response = await async_client.get(
            f"/api/v1/sessions/{session_id}/working-memory"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "memory_tree" in data
        assert "timeline" in data
        assert "index_map" in data

    @pytest.mark.asyncio
    async def test_update_working_memory(self, async_client: AsyncClient):
        """Test updating working memory for a session."""
        create_response = await async_client.post("/api/v1/sessions", json={})
        session_id = create_response.json()["id"]

        memory_update = {
            "memory_tree": {"root": {"agent": "master", "children": []}},
            "timeline": [{"id": "step-1", "agent": "planner"}],
            "index_map": {"step-1": {"status": "completed"}},
        }

        response = await async_client.put(
            f"/api/v1/sessions/{session_id}/working-memory", json=memory_update
        )
        assert response.status_code == 200
        data = response.json()
        assert data["memory_tree"]["root"]["agent"] == "master"
        assert len(data["timeline"]) == 1
