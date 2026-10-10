"""Add keywords to episodes and weighted search vector (guest/title/keywords + body) to chunks.

Revision ID: 0004_weighted_search
Revises: 0003_message_seq
Create Date: 2026-10-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_weighted_search"
down_revision: Union[str, None] = "0003_message_seq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add keywords JSONB column to episodes table
    op.add_column(
        "episodes",
        sa.Column(
            "keywords",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # 2. Drop existing chunks.tsv computed column and index
    op.drop_index("ix_chunks_tsv", table_name="chunks")
    op.drop_column("chunks", "tsv")

    # 3. Add header text column to chunks table
    op.add_column(
        "chunks",
        sa.Column("header", sa.Text(), nullable=False, server_default=""),
    )

    # 4. Backfill header for existing chunks from parent episode title and guest
    op.execute(
        "UPDATE chunks c SET header = trim(e.title || ' ' || e.guest) FROM episodes e WHERE e.id = c.episode_id"
    )

    # 5. Add new weighted tsv computed column (header weight A, text weight B)
    op.add_column(
        "chunks",
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed(
                "setweight(to_tsvector('english'::regconfig, header), 'A') || "
                "setweight(to_tsvector('english'::regconfig, text), 'B')",
                persisted=True,
            ),
            nullable=False,
        ),
    )

    # 6. Re-create GIN index on chunks.tsv
    op.create_index("ix_chunks_tsv", "chunks", ["tsv"], postgresql_using="gin")


def downgrade() -> None:
    # 1. Drop weighted tsv computed column and index
    op.drop_index("ix_chunks_tsv", table_name="chunks")
    op.drop_column("chunks", "tsv")

    # 2. Drop header column
    op.drop_column("chunks", "header")

    # 3. Restore unweighted tsv computed column and index
    op.add_column(
        "chunks",
        sa.Column(
            "tsv",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english'::regconfig, text)", persisted=True),
            nullable=False,
        ),
    )
    op.create_index("ix_chunks_tsv", "chunks", ["tsv"], postgresql_using="gin")

    # 4. Drop keywords column from episodes
    op.drop_column("episodes", "keywords")
