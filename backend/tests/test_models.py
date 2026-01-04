"""
Unit tests for database models.
"""

import pytest
from datetime import datetime
from app.db.models import (
    Base,
    ChatSession,
    Message,
    WorkingMemory,
    AgentStep,
    CustomTool,
    Configuration,
    generate_uuid,
)


class TestGenerateUUID:
    """Test the generate_uuid function."""

    def test_generate_uuid_format(self):
        """Test that generated UUID has correct format."""
        uuid = generate_uuid()
        assert isinstance(uuid, str)
        assert len(uuid) == 36
        assert uuid.count("-") == 4

    def test_generate_uuid_uniqueness(self):
        """Test that generated UUIDs are unique."""
        uuids = [generate_uuid() for _ in range(100)]
        assert len(set(uuids)) == 100


class TestChatSession:
    """Test the ChatSession model."""

    def test_create_session(self):
        """Test creating a chat session."""
        session = ChatSession(id="test-id", title="Test Session")
        assert session.id == "test-id"
        assert session.title == "Test Session"
        assert session.archived is False
        assert session.extra_data is None

    def test_session_repr(self):
        """Test session string representation."""
        session = ChatSession(id="test-id", title="Test Session")
        repr_str = repr(session)
        assert "ChatSession" in repr_str
        assert "test-id" in repr_str


class TestMessage:
    """Test the Message model."""

    def test_create_message(self):
        """Test creating a message."""
        message = Message(
            id="msg-id",
            session_id="session-id",
            role="user",
            content="Hello, world!",
        )
        assert message.id == "msg-id"
        assert message.session_id == "session-id"
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.agent_type is None
        assert message.parent_message_id is None

    def test_assistant_message(self):
        """Test creating an assistant message."""
        message = Message(
            id="msg-id",
            session_id="session-id",
            role="assistant",
            content="I am a bot.",
            agent_type="master",
        )
        assert message.role == "assistant"
        assert message.agent_type == "master"

    def test_message_with_parent(self):
        """Test message with parent for conversation forking."""
        message = Message(
            id="msg-id",
            session_id="session-id",
            role="user",
            content="Follow-up question",
            parent_message_id="parent-msg-id",
        )
        assert message.parent_message_id == "parent-msg-id"

    def test_message_with_extra_data(self):
        """Test message with extra metadata."""
        message = Message(
            id="msg-id",
            session_id="session-id",
            role="assistant",
            content="Response",
            extra_data={
                "tokens": 100,
                "cost": 0.01,
                "model": "claude-3-5-sonnet",
                "duration_ms": 1500,
            },
        )
        assert message.extra_data["tokens"] == 100
        assert message.extra_data["model"] == "claude-3-5-sonnet"


class TestWorkingMemory:
    """Test the WorkingMemory model."""

    def test_create_working_memory(self):
        """Test creating working memory."""
        memory = WorkingMemory(
            id="mem-id",
            session_id="session-id",
            memory_tree={"root": {"agent": "master", "children": []}},
            timeline=[{"id": "step-1", "agent": "planner"}],
            index_map={"step-1": {"status": "completed"}},
        )
        assert memory.session_id == "session-id"
        assert memory.memory_tree["root"]["agent"] == "master"
        assert len(memory.timeline) == 1

    def test_working_memory_repr(self):
        """Test working memory string representation."""
        memory = WorkingMemory(
            id="mem-id",
            session_id="session-id",
        )
        repr_str = repr(memory)
        assert "WorkingMemory" in repr_str
        assert "session-id" in repr_str


class TestAgentStep:
    """Test the AgentStep model."""

    def test_create_agent_step(self):
        """Test creating an agent step."""
        step = AgentStep(
            id="step-id",
            session_id="session-id",
            step_number=1,
            agent_type="planner",
            description="Planning the approach",
            status="pending",
        )
        assert step.step_number == 1
        assert step.agent_type == "planner"
        assert step.status == "pending"

    def test_agent_step_status_values(self):
        """Test various agent step statuses."""
        for status in ["pending", "running", "completed", "failed"]:
            step = AgentStep(
                id="step-id",
                session_id="session-id",
                step_number=1,
                status=status,
            )
            assert step.status == status

    def test_agent_step_with_logs(self):
        """Test agent step with execution logs."""
        step = AgentStep(
            id="step-id",
            session_id="session-id",
            step_number=1,
            logs="Step 1: Started\nStep 2: Processing\nStep 3: Completed",
        )
        assert "Step 2: Processing" in step.logs


class TestCustomTool:
    """Test the CustomTool model."""

    def test_create_custom_tool(self):
        """Test creating a custom tool."""
        tool = CustomTool(
            id="tool-id",
            name="my_calculator",
            description="A custom calculator tool",
            code="def calculate(x, y): return x + y",
            enabled=True,
        )
        assert tool.name == "my_calculator"
        assert tool.enabled is True


class TestConfiguration:
    """Test the Configuration model."""

    def test_create_configuration(self):
        """Test creating a configuration."""
        config = Configuration(
            id="config-id",
            config_json={"version": "1.0", "setting": "value"},
            version=1,
        )
        assert config.config_json["version"] == "1.0"
        assert config.version == 1


class TestModelRelationships:
    """Test model relationships."""

    def test_session_messages_relationship(self):
        """Test session-messages relationship."""
        session = ChatSession(id="session-id", title="Test")
        message = Message(
            id="msg-id",
            session_id="session-id",
            role="user",
            content="Test",
        )
        session.messages = [message]
        assert len(session.messages) == 1
        assert session.messages[0].id == "msg-id"

    def test_session_working_memory_relationship(self):
        """Test session-working memory relationship."""
        session = ChatSession(id="session-id", title="Test")
        memory = WorkingMemory(
            id="mem-id",
            session_id="session-id",
        )
        session.working_memory = memory
        assert session.working_memory.id == "mem-id"

    def test_session_agent_steps_relationship(self):
        """Test session-agent steps relationship."""
        session = ChatSession(id="session-id", title="Test")
        step = AgentStep(
            id="step-id",
            session_id="session-id",
            step_number=1,
        )
        session.agent_steps = [step]
        assert len(session.agent_steps) == 1
