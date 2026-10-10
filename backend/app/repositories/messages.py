from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message


class MessageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        *,
        session_id: UUID,
        role: str,
        content: str,
        sources: list[Any] | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> Message:
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            sources=sources if sources is not None else [],
            provider=provider,
            model=model,
        )
        self._db.add(message)
        await self._db.flush()
        await self._db.refresh(message)
        return message

    async def list_for_session(self, session_id: UUID) -> list[Message]:
        result = await self._db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc(), Message.seq.asc())
        )
        return list(result.scalars().all())
