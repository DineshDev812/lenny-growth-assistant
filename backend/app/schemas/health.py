from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    db: Literal["ok"] = "ok"
    provider: str
    model: str = Field(description="Active model from configuration.")
    provider_status: str = "ok"


class MetaResponse(BaseModel):
    app_name: str
    provider: str
    model: str
    fallback_provider: str | None = None
    provider_status: str = "ok"
