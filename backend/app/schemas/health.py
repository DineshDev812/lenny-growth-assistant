from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    db: Literal["ok"] = "ok"
    provider: str
    model: str = Field(description="Active model from configuration.")
    provider_status: str = "ok"
    llm_status: Literal["reachable", "unreachable", "not_configured"] = "reachable"


class MetaResponse(BaseModel):
    app_name: str
    version: str = "1.0.0"
    current_model: str
    model_provider: str
    fallback_provider: str | None = None
    grounding_strict: bool = True
    llm_status: Literal["reachable", "unreachable", "not_configured"] = "reachable"
    provider: str
    model: str
    provider_status: str = "ok"
