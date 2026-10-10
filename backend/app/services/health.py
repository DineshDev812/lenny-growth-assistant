from __future__ import annotations

from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import DatabaseUnavailableError
from app.llm.factory import get_llm_provider
from app.repositories.health import ping
from app.schemas.health import HealthResponse, MetaResponse


class HealthService:
    def __init__(self, db: AsyncSession | None = None) -> None:
        self._db = db

    async def get_health(self) -> HealthResponse:
        if self._db is not None:
            try:
                await ping(self._db)
            except (OperationalError, InterfaceError, OSError) as exc:
                raise DatabaseUnavailableError() from exc

        settings = get_settings()
        provider = get_llm_provider(settings)
        try:
            provider_status = await provider.health()
        except Exception:
            provider_status = "unavailable"

        return HealthResponse(
            status="ok",
            db="ok",
            provider=settings.model_provider,
            model=settings.active_model,
            provider_status=provider_status,
        )

    async def get_meta(self) -> MetaResponse:
        settings = get_settings()
        provider = get_llm_provider(settings)
        try:
            provider_status = await provider.health()
        except Exception:
            provider_status = "unavailable"

        return MetaResponse(
            app_name=settings.app_name,
            provider=settings.model_provider,
            model=settings.active_model,
            fallback_provider=None,
            provider_status=provider_status,
        )
