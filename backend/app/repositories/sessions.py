from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Session


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        client_id: UUID,
        title: str,
        user_metadata: dict[str, Any],
    ) -> Session:
        session = Session(client_id=client_id, title=title, user_metadata=user_metadata)
        self._db.add(session)
        await self._db.flush()
        await self._db.refresh(session)
        return session

    async def list_for_client(self, client_id: UUID) -> list[Session]:
        result = await self._db.execute(
            select(Session)
            .where(Session.client_id == client_id)
            .order_by(Session.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_owned(self, session_id: UUID, client_id: UUID) -> Session | None:
        result = await self._db.execute(
            select(Session)
            .options(selectinload(Session.messages))
            .where(Session.id == session_id, Session.client_id == client_id)
        )
        return result.scalar_one_or_none()

    async def touch(
        self,
        session: Session,
        *,
        title: str | None = None,
    ) -> Session:
        if title is not None:
            session.title = title
        session.updated_at = datetime.now(timezone.utc)
        await self._db.flush()
        await self._db.refresh(session)
        return session
