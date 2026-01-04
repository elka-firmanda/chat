"""
Add performance indexes for database queries.

Revision ID: 003
Revises: 002
Create Date: 2024-01-04

"""

from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_index("idx_chat_sessions_created_at", "chat_sessions", ["created_at"])
    op.create_index("idx_chat_sessions_archived", "chat_sessions", ["archived"])
    op.create_index("idx_chat_sessions_updated_at", "chat_sessions", ["updated_at"])

    op.create_index("idx_messages_session_id", "messages", ["session_id"])
    op.create_index("idx_messages_created_at", "messages", ["created_at"])

    op.create_index("idx_working_memory_session_id", "working_memory", ["session_id"])

    op.create_index("idx_agent_steps_session_id", "agent_steps", ["session_id"])
    op.create_index("idx_agent_steps_created_at", "agent_steps", ["created_at"])

    op.create_index("idx_custom_tools_enabled", "custom_tools", ["enabled"])
    op.create_index("idx_custom_tools_created_at", "custom_tools", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_custom_tools_created_at", table_name="custom_tools")
    op.drop_index("idx_custom_tools_enabled", table_name="custom_tools")

    op.drop_index("idx_agent_steps_created_at", table_name="agent_steps")
    op.drop_index("idx_agent_steps_session_id", table_name="agent_steps")

    op.drop_index("idx_working_memory_session_id", table_name="working_memory")

    op.drop_index("idx_messages_created_at", table_name="messages")
    op.drop_index("idx_messages_session_id", table_name="messages")

    op.drop_index("idx_chat_sessions_updated_at", table_name="chat_sessions")
    op.drop_index("idx_chat_sessions_archived", table_name="chat_sessions")
    op.drop_index("idx_chat_sessions_created_at", table_name="chat_sessions")
