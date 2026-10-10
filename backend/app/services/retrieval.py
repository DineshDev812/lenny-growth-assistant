"""Chunk retrieval: Postgres full-text search with an OR-style fallback."""

from __future__ import annotations

import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.repositories.search import ChunkSearchRepository, SearchRow
from app.schemas.retrieval import RetrievedChunk
from app.services.transcript_parser import format_timestamp

logger = logging.getLogger(__name__)

MAX_QUERY_CHARS = 500
MAX_K = 50
MAX_OR_TERMS = 16
_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def build_deep_link(youtube_url: str | None, start_seconds: int | None) -> str | None:
    if not youtube_url:
        return None
    if start_seconds is None:
        return youtube_url
    separator = "&" if "?" in youtube_url else "?"
    return f"{youtube_url}{separator}t={start_seconds}"


def extract_terms(query: str) -> list[str]:
    """Lowercase letter/digit tokens, deduplicated, safe to join with ' | ' for to_tsquery."""
    seen: dict[str, None] = {}
    for token in _WORD_RE.findall(query.lower()):
        if len(token) >= 2:
            seen.setdefault(token, None)
    return list(seen)[:MAX_OR_TERMS]


def _to_chunk(row: SearchRow) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=row.chunk_id,
        episode_id=row.episode_id,
        episode_slug=row.episode_slug,
        episode_title=row.episode_title,
        guest=row.guest,
        publish_date=row.publish_date,
        youtube_url=row.youtube_url,
        youtube_deep_link=build_deep_link(row.youtube_url, row.start_seconds),
        chunk_index=row.chunk_index,
        speaker=row.speaker,
        start_seconds=row.start_seconds,
        start_timestamp=format_timestamp(row.start_seconds),
        text=row.text,
        score=round(row.score, 4),
    )


class RetrievalService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        min_score: float | None = None,
        fallback_min_score: float | None = None,
    ) -> None:
        settings = get_settings()
        self._repo = ChunkSearchRepository(db)
        self._min_score = settings.retrieval_min_score if min_score is None else min_score
        # OR-style matches are looser, so they must clear a higher bar (e.g. not one stray word).
        fallback = settings.retrieval_fallback_min_score if fallback_min_score is None else fallback_min_score
        self._fallback_min_score = max(fallback, self._min_score)

    async def retrieve(self, query: str, k: int = 6) -> list[RetrievedChunk]:
        """Top-k chunks for a query. Empty/nonsense/weak queries return [], never an error."""
        cleaned = " ".join((query or "").split())[:MAX_QUERY_CHARS]
        terms = extract_terms(cleaned)
        if not terms or k < 1:
            return []
        limit = min(k, MAX_K)

        rows = await self._repo.search_websearch(cleaned, min_score=self._min_score, limit=limit)
        mode = "strict"
        if not rows:
            rows = await self._repo.search_any_term(
                terms, min_score=self._fallback_min_score, limit=limit
            )
            mode = "or_fallback"
        logger.info(
            "Retrieval %s returned %d chunks" % (mode, len(rows)),
            extra={"event": "retrieval", "retrieval_hits": len(rows)},
        )
        return [_to_chunk(row) for row in rows]
