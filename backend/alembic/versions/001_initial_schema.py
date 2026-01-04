"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-04

"""

from typing import Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Create chat_sessions table
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column("archived", sa.Boolean, nullable=False, default=False),
        sa.Column("extra_data", sa.JSON, nullable=True),
    )

    # Create messages table
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("agent_type", sa.String(20), nullable=True),
        sa.Column("parent_message_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column("extra_data", sa.JSON, nullable=True),
    )
    op.create_index("idx_session_created", "messages", ["session_id", "created_at"])

    # Create working_memory table
    op.create_table(
        "working_memory",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("memory_tree", sa.JSON, nullable=True),
        sa.Column("timeline", sa.JSON, nullable=True),
        sa.Column("index_map", sa.JSON, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=False, default=sa.func.now()),
    )

    # Create agent_steps table
    op.create_table(
        "agent_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            sa.String(36),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("step_number", sa.Integer, nullable=False),
        sa.Column("agent_type", sa.String(20), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("logs", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("idx_session_message", "agent_steps", ["session_id", "message_id"])

    # Create custom_tools table
    op.create_table(
        "custom_tools",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("code", sa.Text, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, default=True),
        sa.Column("created_at", sa.DateTime, nullable=False, default=sa.func.now()),
    )

    # Create configurations table
    op.create_table(
        "configurations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("config_json", sa.JSON, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, default=1),
        sa.Column("created_at", sa.DateTime, nullable=False, default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("configurations")
    op.drop_table("custom_tools")
    op.drop_index("idx_session_message", table_name="agent_steps")
    op.drop_table("agent_steps")
    op.drop_table("working_memory")
    op.drop_index("idx_session_created", table_name="messages")
    op.drop_table("messages")
    op.drop_table("chat_sessions")
