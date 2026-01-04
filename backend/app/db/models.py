"""
SQLAlchemy database models for the agentic chatbot.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship
import uuid


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class ChatSession(Base):
    """
    Represents a chat session/conversation.
    """

    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    archived = Column(Boolean, default=False, nullable=False)
    extra_data = Column(JSON, nullable=True)

    # Relationships
    messages = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan"
    )
    working_memory = relationship(
        "WorkingMemory",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )
    agent_steps = relationship(
        "AgentStep", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ChatSession(id={self.id}, title={self.title}, created_at={self.created_at})>"


class Message(Base):
    """
    Represents a single message in a chat session.
    Can be from user, assistant, or system.
    """

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    agent_type = Column(
        String(20), nullable=True
    )  # 'master', 'planner', 'researcher', 'tools', 'database'
    parent_message_id = Column(String(36), nullable=True)  # For conversation forking
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    extra_data = Column(JSON, nullable=True)  # tokens, cost, model, duration

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    agent_steps = relationship(
        "AgentStep", back_populates="message", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("idx_session_created", "session_id", "created_at"),)

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, agent_type={self.agent_type}, created_at={self.created_at})>"


class WorkingMemory(Base):
    """
    Stores the hybrid working memory for agent orchestration.
    Contains tree structure, timeline, and index map.
    """

    __tablename__ = "working_memory"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    memory_tree = Column(JSON, nullable=True)  # Hierarchical structure
    timeline = Column(JSON, nullable=True)  # Flat execution log for UI
    index_map = Column(JSON, nullable=True)  # Quick lookup by ID
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    session = relationship("ChatSession", back_populates="working_memory")

    def __repr__(self):
        return f"<WorkingMemory(id={self.id}, session_id={self.session_id}, updated_at={self.updated_at})>"


class AgentStep(Base):
    """
    Represents a single step in the agent execution plan.
    Used for UI progress tracking.
    """

    __tablename__ = "agent_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    message_id = Column(
        String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=True
    )
    step_number = Column(Integer, nullable=False)
    agent_type = Column(String(20), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(
        String(20), default="pending", nullable=False
    )  # 'pending', 'running', 'completed', 'failed'
    result = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)  # Expandable logs
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("ChatSession", back_populates="agent_steps")
    message = relationship("Message", back_populates="agent_steps")

    # Indexes
    __table_args__ = (Index("idx_session_message", "session_id", "message_id"),)

    def __repr__(self):
        return f"<AgentStep(id={self.id}, step_number={self.step_number}, agent_type={self.agent_type}, status={self.status})>"


class CustomTool(Base):
    """
    Stores user-defined custom tools for the tools agent.
    """

    __tablename__ = "custom_tools"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    code = Column(Text, nullable=False)  # Python code
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    def __repr__(self):
        return f"<CustomTool(id={self.id}, name={self.name}, enabled={self.enabled})>"


class Configuration(Base):
    """
    Stores persisted configuration in database (backup of config.json).
    """

    __tablename__ = "configurations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    config_json = Column(JSON, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    def __repr__(self):
        return f"<Configuration(id={self.id}, version={self.version}, created_at={self.created_at})>"
