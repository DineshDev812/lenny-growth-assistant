from __future__ import annotations

import time
from typing import Literal

from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import DatabaseUnavailableError
from app.llm import factory as llm_factory
from app.repositories.health import ping
from app.schemas.health import HealthResponse, MetaResponse

_probe_cache: tuple[float, str, Literal["reachable", "unreachable", "not_configured"]] | None = None
CACHE_TTL_SECONDS = 10.0


async def probe_llm_health() -> tuple[str, Literal["reachable", "unreachable", "not_configured"]]:
    """Probe LLM provider health with a 10s memory cache to prevent hammering."""
    global _probe_cache
    now = time.monotonic()

    # Bypass cache if a mock test provider is set
    if llm_factory._test_provider is None and _probe_cache is not None:
        cached_ts, cached_pstatus, cached_llm_status = _probe_cache
        if now - cached_ts < CACHE_TTL_SECONDS:
            return cached_pstatus, cached_llm_status

    settings = get_settings()
    provider = llm_factory.get_llm_provider(settings)
    try:
        provider_status = await provider.health()
    except Exception:
        provider_status = "unavailable"

    if provider_status == "ok":
        llm_status: Literal["reachable", "unreachable", "not_configured"] = "reachable"
    elif provider_status == "unconfigured":
        llm_status = "not_configured"
    else:
        llm_status = "unreachable"

    _probe_cache = (now, provider_status, llm_status)
    return provider_status, llm_status


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
        provider_status, llm_status = await probe_llm_health()

        return HealthResponse(
            status="ok",
            db="ok",
            provider=settings.model_provider,
            model=settings.active_model,
            provider_status=provider_status,
            llm_status=llm_status,
        )

    async def get_meta(self) -> MetaResponse:
        settings = get_settings()
        provider_status, llm_status = await probe_llm_health()

        episodes_count = 0
        chunks_count = 0
        try:
            from sqlalchemy import func, select
            from app.db.models import Chunk, Episode
            from app.db.session import SessionLocal

            if self._db is not None:
                ep_res = await self._db.scalar(select(func.count(Episode.id)))
                ch_res = await self._db.scalar(select(func.count(Chunk.id)))
                episodes_count = int(ep_res or 0)
                chunks_count = int(ch_res or 0)
            else:
                async with SessionLocal() as db:
                    ep_res = await db.scalar(select(func.count(Episode.id)))
                    ch_res = await db.scalar(select(func.count(Chunk.id)))
                    episodes_count = int(ep_res or 0)
                    chunks_count = int(ch_res or 0)
        except Exception:
            pass

        return MetaResponse(
            app_name=settings.app_name,
            version="1.0.0",
            current_model=settings.active_model,
            model_provider=settings.model_provider,
            fallback_provider=settings.model_fallback if settings.model_fallback != "none" else None,
            grounding_strict=settings.grounding_strict,
            llm_status=llm_status,
            provider=settings.model_provider,
            model=settings.active_model,
            provider_status=provider_status,
            episodes_loaded=episodes_count,
            chunks_loaded=chunks_count,
        )
