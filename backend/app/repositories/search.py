from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import Text, cast, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Episode

_ENGLISH = literal_column("'english'::regconfig")
_NORMALIZE_LENGTH_SQUASH = literal_column("32")  # rank / (rank + 1): scores in [0, 1)


@dataclass(frozen=True)
class SearchRow:
    chunk_id: UUID
    episode_id: UUID
    episode_slug: str
    episode_title: str
    guest: str
    publish_date: date | None
    youtube_url: str | None
    chunk_index: int
    speaker: str | None
    start_seconds: int | None
    text: str
    score: float


class ChunkSearchRepository:
    """Full-text search over chunks.tsv. All user input is passed as bind parameters."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def search_websearch(self, query: str, *, min_score: float, limit: int) -> list[SearchRow]:
        tsquery = func.websearch_to_tsquery(_ENGLISH, cast(query, Text))
        return await self._run(tsquery, min_score=min_score, limit=limit)

    async def search_any_term(
        self, terms: list[str], *, min_score: float, limit: int
    ) -> list[SearchRow]:
        """OR-style search. Terms must already be sanitised to letters and digits."""
        if not terms:
            return []
        tsquery = func.to_tsquery(_ENGLISH, cast(" | ".join(terms), Text))
        return await self._run(tsquery, min_score=min_score, limit=limit)

    async def _run(self, tsquery, *, min_score: float, limit: int) -> list[SearchRow]:  # type: ignore[no-untyped-def]
        rank = func.ts_rank_cd(Chunk.tsv, tsquery, _NORMALIZE_LENGTH_SQUASH)
        statement = (
            select(
                Chunk.id,
                Chunk.episode_id,
                Episode.slug,
                Episode.title,
                Episode.guest,
                Episode.publish_date,
                Episode.youtube_url,
                Chunk.chunk_index,
                Chunk.speaker,
                Chunk.start_seconds,
                Chunk.text,
                rank.label("score"),
            )
            .join(Episode, Episode.id == Chunk.episode_id)
            .where(Chunk.tsv.op("@@", is_comparison=True)(tsquery))
            .where(rank >= min_score)
            .order_by(rank.desc(), Episode.slug, Chunk.chunk_index)
            .limit(limit)
        )
        result = await self._db.execute(statement)
        return [
            SearchRow(
                chunk_id=row[0],
                episode_id=row[1],
                episode_slug=row[2],
                episode_title=row[3],
                guest=row[4],
                publish_date=row[5],
                youtube_url=row[6],
                chunk_index=row[7],
                speaker=row[8],
                start_seconds=row[9],
                text=row[10],
                score=float(row[11]),
            )
            for row in result.all()
        ]
