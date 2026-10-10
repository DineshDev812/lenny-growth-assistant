from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ArtifactSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    format: str
    title: str


class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    message_id: UUID
    format: str
    title: str
    content: str
    created_at: datetime
