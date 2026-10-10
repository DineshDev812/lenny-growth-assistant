from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    db: Literal["ok"] = "ok"
    provider: str
    model: str = Field(description="Active model from configuration (not probed in this phase).")
