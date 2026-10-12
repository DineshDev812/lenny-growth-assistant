from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.artifacts import ArtifactRead, ArtifactSummary


class Source(BaseModel):
    id: str  # e.g. "S1", "S2"
    chunk_id: UUID
    episode_id: UUID
    slug: str
    title: str
    guest: str
    publish_date: str | None = None
    youtube_url: str | None = None
    youtube_deep_link: str | None = None
    start_ts: str | None = None
    start_seconds: int | None = None
    snippet: str


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    intent: Literal["qa", "essay", "artifact", "general"] | None = None
    artifact_format: Literal["markdown", "html"] | None = None

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("content must not be empty")
        return stripped


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    seq: int | None = None
    role: str
    content: str
    sources: list[Source] | list[dict[str, Any]] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None
    intent: str | None = None
    error_class: str | None = None
    kind: str | None = "answer"
    actions: list[dict[str, Any]] | None = None
    artifact: ArtifactSummary | None = None
    created_at: datetime


class SessionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    user_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead]


class SendMessageResponse(BaseModel):
    user_message: MessageRead
    assistant_message: MessageRead
    artifact: ArtifactRead | None = None
