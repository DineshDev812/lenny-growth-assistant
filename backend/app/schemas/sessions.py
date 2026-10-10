from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    user_metadata: dict[str, Any] = Field(default_factory=dict)


class SessionUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    user_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
