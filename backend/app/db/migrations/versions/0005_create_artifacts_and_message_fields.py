"""Create artifacts table and add intent/error_class to messages.

Revision ID: 0005_artifacts_and_fields
Revises: 0004_weighted_search
Create Date: 2026-10-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_artifacts_and_fields"
down_revision: Union[str, None] = "0004_weighted_search"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add intent and error_class to messages table
    op.add_column("messages", sa.Column("intent", sa.Text(), nullable=True))
    op.add_column("messages", sa.Column("error_class", sa.Text(), nullable=True))

    # 2. Create artifacts table
    op.create_table(
        "artifacts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("format", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_artifacts_session_id", "artifacts", ["session_id"])
    op.create_index("ix_artifacts_client_id", "artifacts", ["client_id"])
    op.create_index("ix_artifacts_message_id", "artifacts", ["message_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_artifacts_message_id", table_name="artifacts")
    op.drop_index("ix_artifacts_client_id", table_name="artifacts")
    op.drop_index("ix_artifacts_session_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_column("messages", "error_class")
    op.drop_column("messages", "intent")
