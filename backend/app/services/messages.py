from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.db.models import Message
from app.repositories.messages import MessageRepository
from app.repositories.sessions import SessionRepository

PLACEHOLDER_ASSISTANT_CONTENT = (
    "[PLACEHOLDER] Chat is not implemented in this phase. "
    "Your message was saved; a grounded assistant reply will be added later."
)

_TITLE_MAX = 60


class MessageService:
    def __init__(self, db: AsyncSession) -> None:
        self._sessions = SessionRepository(db)
        self._messages = MessageRepository(db)

    async def add_user_message(
        self,
        *,
        session_id: UUID,
        client_id: UUID,
        content: str,
    ) -> tuple[Message, Message]:
        session = await self._sessions.get_owned(session_id, client_id)
        if session is None:
            raise NotFoundError("Session not found.")

        is_first = len(session.messages) == 0
        user_message = await self._messages.create(
            session_id=session.id,
            role="user",
            content=content,
            sources=[],
        )
        settings = get_settings()
        assistant_message = await self._messages.create(
            session_id=session.id,
            role="assistant",
            content=PLACEHOLDER_ASSISTANT_CONTENT,
            sources=[],
            provider=settings.model_provider,
            model=settings.active_model,
        )
        new_title = content[:_TITLE_MAX] if is_first and session.title == "New chat" else None
        await self._sessions.touch(session, title=new_title)
        return user_message, assistant_message
