from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health(db: Annotated[AsyncSession, Depends(get_db)]) -> HealthResponse:
    return await HealthService(db).get_health()
