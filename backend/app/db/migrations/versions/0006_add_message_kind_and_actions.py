"""Add kind and actions to messages.

Revision ID: 0006_kind_and_actions
Revises: 0005_artifacts_and_fields
Create Date: 2026-10-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_kind_and_actions"
down_revision: Union[str, None] = "0005_artifacts_and_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("kind", sa.Text(), nullable=True, server_default=sa.text("'answer'")))
    op.add_column("messages", sa.Column("actions", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'[]'::jsonb")))


def downgrade() -> None:
    op.drop_column("messages", "actions")
    op.drop_column("messages", "kind")
