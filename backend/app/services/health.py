from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import DatabaseUnavailableError
from app.repositories.health import ping
from app.schemas.health import HealthResponse


class HealthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_health(self) -> HealthResponse:
        try:
            await ping(self._db)
        except (OperationalError, InterfaceError, OSError) as exc:
            raise DatabaseUnavailableError() from exc
        settings = get_settings()
        return HealthResponse(
            status="ok",
            db="ok",
            provider=settings.model_provider,
            model=settings.active_model,
        )
