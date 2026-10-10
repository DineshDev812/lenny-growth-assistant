from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models import Session
from app.repositories.sessions import SessionRepository


class SessionService:
    def __init__(self, db: AsyncSession) -> None:
        self._sessions = SessionRepository(db)

    async def create(
        self,
        client_id: UUID,
        title: str | None,
        user_metadata: dict[str, Any],
    ) -> Session:
        return await self._sessions.create(
            client_id=client_id,
            title=title.strip() if title and title.strip() else "New chat",
            user_metadata=user_metadata,
        )

    async def list_for_client(self, client_id: UUID) -> list[Session]:
        return await self._sessions.list_for_client(client_id)

    async def get_owned(self, session_id: UUID, client_id: UUID) -> Session:
        session = await self._sessions.get_owned(session_id, client_id)
        if session is None:
            raise NotFoundError("Session not found.")
        return session
