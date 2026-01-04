"""Add FTS5 full-text search support

Revision ID: 002
Revises: 001
Create Date: 2024-01-04

"""

from typing import Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    """Create FTS5 virtual table for message content search."""
    connection = op.get_bind()

    # Check if FTS5 is available (SQLite version check)
    try:
        result = connection.execute(
            sa.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='messages_fts'"
            )
        )
        existing = result.fetchone()

        if existing:
            # Table already exists, just return
            return
    except Exception:
        # If query fails, continue with creation
        pass

    # Create FTS5 virtual table for messages
    # This enables fast full-text search with ranking and highlighting
    op.execute(
        sa.text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
            content,
            content='messages',
            content_rowid='id',
            tokenize='porter unicode61'
        )
    """)
    )

    # Create triggers to keep FTS5 table in sync with messages table
    # Trigger for INSERT
    op.execute(
        sa.text("""
        CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
            INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
        END
    """)
    )

    # Trigger for UPDATE
    op.execute(
        sa.text("""
        CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
            INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
        END
    """)
    )

    # Trigger for DELETE
    op.execute(
        sa.text("""
        CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
            INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
        END
    """)
    )

    # Populate FTS5 table with existing messages
    op.execute(
        sa.text("""
        INSERT INTO messages_fts(rowid, content) 
        SELECT id, content FROM messages
    """)
    )


def downgrade() -> None:
    """Remove FTS5 virtual table and triggers."""
    # Drop triggers first (in reverse order of creation)
    op.execute(sa.text("DROP TRIGGER IF EXISTS messages_ad"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS messages_au"))
    op.execute(sa.text("DROP TRIGGER IF EXISTS messages_ai"))

    # Drop the FTS5 virtual table
    op.execute(sa.text("DROP TABLE IF EXISTS messages_fts"))
