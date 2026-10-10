from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IngestErrorItem(BaseModel):
    slug: str
    message: str


class IngestStatusResponse(BaseModel):
    state: Literal["idle", "running", "completed", "failed"]
    trigger: str | None = Field(default=None, description="startup or manual")
    started_at: datetime | None = None
    finished_at: datetime | None = None
    transcripts_dir: str
    files_found: int = 0
    episodes_ingested: int = 0
    episodes_skipped: int = 0
    episodes_failed: int = 0
    episodes_deleted: int = 0
    chunks_created: int = 0
    total_episodes: int | None = Field(default=None, description="Episodes currently in the database.")
    total_chunks: int | None = Field(default=None, description="Chunks currently in the database.")
    errors: list[IngestErrorItem] = Field(default_factory=list)
    message: str | None = None
