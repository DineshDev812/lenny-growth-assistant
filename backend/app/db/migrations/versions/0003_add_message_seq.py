"""Add monotonic seq column to messages table.

Revision ID: 0003_message_seq
Revises: 0002_episodes_chunks
Create Date: 2026-10-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_message_seq"
down_revision: Union[str, None] = "0002_episodes_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "seq",
            sa.BigInteger(),
            sa.Identity(start=1),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_messages_session_created_seq",
        "messages",
        ["session_id", "created_at", "seq"],
    )


def downgrade() -> None:
    op.drop_index("ix_messages_session_created_seq", table_name="messages")
    op.drop_column("messages", "seq")
