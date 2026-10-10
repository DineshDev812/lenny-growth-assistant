from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk, Episode


class EpisodeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def hashes_by_slug(self) -> dict[str, str]:
        result = await self._db.execute(select(Episode.slug, Episode.content_hash))
        return {slug: content_hash for slug, content_hash in result.all()}

    async def replace_episode(
        self,
        *,
        slug: str,
        guest: str,
        title: str,
        youtube_url: str | None,
        video_id: str | None,
        publish_date: date | None,
        description: str | None,
        source_path: str,
        content_hash: str,
        chunks: list[dict[str, Any]],
    ) -> int:
        """Insert or update one episode and replace all of its chunks. Returns chunk count."""
        values = {
            "guest": guest,
            "title": title,
            "youtube_url": youtube_url,
            "video_id": video_id,
            "publish_date": publish_date,
            "description": description,
            "source_path": source_path,
            "content_hash": content_hash,
            "ingested_at": func.now(),
        }
        existing_id = (
            await self._db.execute(select(Episode.id).where(Episode.slug == slug))
        ).scalar_one_or_none()
        if existing_id is None:
            episode = Episode(slug=slug, **{k: v for k, v in values.items() if k != "ingested_at"})
            self._db.add(episode)
            await self._db.flush()
            episode_id = episode.id
        else:
            episode_id = existing_id
            await self._db.execute(update(Episode).where(Episode.id == episode_id).values(**values))
            await self._db.execute(delete(Chunk).where(Chunk.episode_id == episode_id))
        if chunks:
            rows = [{"episode_id": episode_id, **chunk} for chunk in chunks]
            await self._db.execute(insert(Chunk), rows)
        await self._db.flush()
        return len(chunks)

    async def delete_by_slugs(self, slugs: list[str]) -> int:
        if not slugs:
            return 0
        result = await self._db.execute(delete(Episode).where(Episode.slug.in_(slugs)))
        return result.rowcount or 0

    async def count_episodes(self) -> int:
        return int((await self._db.execute(select(func.count()).select_from(Episode))).scalar_one())

    async def count_chunks(self) -> int:
        return int((await self._db.execute(select(func.count()).select_from(Chunk))).scalar_one())
