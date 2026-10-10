from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    chunk_id: UUID
    episode_id: UUID
    episode_slug: str
    episode_title: str
    guest: str
    publish_date: date | None = None
    youtube_url: str | None = None
    youtube_deep_link: str | None = Field(
        default=None, description="YouTube URL with &t=SECONDS pointing at the chunk start."
    )
    chunk_index: int
    speaker: str | None = None
    start_seconds: int | None = None
    start_timestamp: str | None = Field(default=None, description="HH:MM:SS")
    text: str
    score: float = Field(description="ts_rank_cd normalised to [0, 1); higher is better.")


class SearchResponse(BaseModel):
    query: str
    k: int
    count: int
    results: list[RetrievedChunk]
