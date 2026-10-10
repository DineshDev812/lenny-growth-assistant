"""Create episodes and chunks tables with full-text search.

Revision ID: 0002_episodes_chunks
Revises: 0001_sessions_messages
Create Date: 2026-10-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_episodes_chunks"
down_revision: Union[str, None] = "0001_sessions_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "episodes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("guest", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("youtube_url", sa.Text(), nullable=True),
        sa.Column("video_id", sa.Text(), nullable=True),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("slug", name="uq_episodes_slug"),
    )
    op.create_table(
        "chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("episode_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("speaker", sa.Text(), nullable=True),
        sa.Column("start_seconds", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english'::regconfig, text)", persisted=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["episode_id"], ["episodes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("episode_id", "chunk_index", name="uq_chunks_episode_index"),
    )
    op.create_index("ix_chunks_tsv", "chunks", ["tsv"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_chunks_tsv", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("episodes")
